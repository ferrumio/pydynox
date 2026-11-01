"""Check that pydynox_core.pyi matches the compiled Rust extension.

The stub is written by hand, so it drifts when Rust bindings change. These tests
compare names, base classes, and call signatures in both directions.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
from pydynox import pydynox_core

STUB_PATH = Path(pydynox_core.__file__).with_name("pydynox_core.pyi")

# Attributes that exist only on instances, so the class does not list them.
INSTANCE_ONLY = {
    "ConditionalCheckFailedException": {"item"},
}


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def _load_stub() -> ast.Module:
    return ast.parse(STUB_PATH.read_text(), filename=str(STUB_PATH))


STUB = _load_stub()
STUB_CLASSES = {node.name: node for node in STUB.body if isinstance(node, ast.ClassDef)}
_FunctionDef = ast.FunctionDef | ast.AsyncFunctionDef

STUB_FUNCTIONS: dict[str, list[_FunctionDef]] = {}
for _node in STUB.body:
    if isinstance(_node, _FunctionDef):
        STUB_FUNCTIONS.setdefault(_node.name, []).append(_node)

RUNTIME_CLASSES = {
    name: obj
    for name, obj in vars(pydynox_core).items()
    if isinstance(obj, type) and not name.startswith("_")
}


def _stub_members(node: ast.ClassDef) -> dict[str, list[_FunctionDef]]:
    """Map each member name in a stub class to its function defs (empty for attributes)."""
    members: dict[str, list[_FunctionDef]] = {}
    for item in node.body:
        if isinstance(item, _FunctionDef):
            members.setdefault(item.name, []).append(item)
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            members.setdefault(item.target.id, [])
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    members.setdefault(target.id, [])
    return members


def _is_staticmethod(node: _FunctionDef) -> bool:
    return any(isinstance(d, ast.Name) and d.id == "staticmethod" for d in node.decorator_list)


def _stub_params(node: _FunctionDef, *, bound: bool) -> list[str]:
    """Describe stub parameters as 'name', 'name=default', '*', '*args' or '**kwargs'."""
    args = node.args
    positional = [*args.posonlyargs, *args.args]
    if bound:
        positional = positional[1:]
    first_default = len(positional) - len(args.defaults)
    params = []
    for index, arg in enumerate(positional):
        if index >= first_default:
            default = ast.literal_eval(args.defaults[index - first_default])
            params.append(f"{arg.arg}={default!r}")
        else:
            params.append(arg.arg)
    if args.vararg:
        params.append(f"*{args.vararg.arg}")
    elif args.kwonlyargs:
        params.append("*")
    for arg, kw_default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        if kw_default is None:
            params.append(arg.arg)
        else:
            params.append(f"{arg.arg}={ast.literal_eval(kw_default)!r}")
    if args.kwarg:
        params.append(f"**{args.kwarg.arg}")
    return params


def _runtime_params(signature: inspect.Signature, *, bound: bool) -> list[str]:
    """Describe runtime parameters in the same format as _stub_params."""
    parameters = list(signature.parameters.values())
    if bound and parameters and parameters[0].name == "self":
        parameters = parameters[1:]
    params = []
    star_added = False
    for param in parameters:
        if param.kind is param.VAR_POSITIONAL:
            params.append(f"*{param.name}")
            star_added = True
            continue
        if param.kind is param.VAR_KEYWORD:
            params.append(f"**{param.name}")
            continue
        if param.kind is param.KEYWORD_ONLY and not star_added:
            params.append("*")
            star_added = True
        if param.default is param.empty:
            params.append(param.name)
        else:
            params.append(f"{param.name}={param.default!r}")
    return params


def _signature_problems(
    label: str, runtime: object, stub_defs: list[_FunctionDef], *, bound: bool
) -> list[str]:
    try:
        signature = inspect.signature(runtime)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return []
    expected = _runtime_params(signature, bound=bound)
    problems = []
    for stub_def in stub_defs:
        actual = _stub_params(stub_def, bound=bound and not _is_staticmethod(stub_def))
        if actual != expected:
            problems.append(
                f"{label}: signature differs\n"
                f"    extension: ({', '.join(expected)})\n"
                f"    stub:      ({', '.join(actual)})"
            )
    return problems


def _name_problems(label: str, runtime: set[str], stub: set[str]) -> list[str]:
    problems = []
    if missing := sorted(runtime - stub):
        problems.append(f"{label}: in extension but missing from stub: {', '.join(missing)}")
    if extra := sorted(stub - runtime):
        problems.append(f"{label}: in stub but missing from extension: {', '.join(extra)}")
    return problems


def test_stub_module_names_match_extension():
    """Every public class and function exists in both the extension and the stub."""
    # GIVEN the public names of the extension module and the stub
    runtime = {name for name in dir(pydynox_core) if not name.startswith("_")}
    stub = {name for name in [*STUB_CLASSES, *STUB_FUNCTIONS] if not name.startswith("_")}

    # THEN both sides list the same names
    problems = _name_problems("pydynox_core", runtime, stub)
    assert not problems, "\n" + "\n".join(problems)


def test_stub_function_signatures_match_extension():
    """Module-level functions take the same parameters in the extension and the stub."""
    # GIVEN every function that both sides define
    problems = []
    for name in sorted(STUB_FUNCTIONS.keys() & set(dir(pydynox_core))):
        # THEN each stub definition matches the compiled signature
        runtime = getattr(pydynox_core, name)
        problems += _signature_problems(name, runtime, STUB_FUNCTIONS[name], bound=False)

    assert not problems, "\n" + "\n".join(problems)


@pytest.mark.parametrize("class_name", sorted(RUNTIME_CLASSES.keys() & STUB_CLASSES.keys()))
def test_stub_class_matches_extension(class_name):
    """Each extension class has the same bases, members, and signatures as its stub."""
    # GIVEN the compiled class and its stub definition
    cls = RUNTIME_CLASSES[class_name]
    stub_class = STUB_CLASSES[class_name]
    stub_members = _stub_members(stub_class)
    problems = []

    # THEN the base classes match
    runtime_bases = [base.__name__ for base in cls.__bases__ if base is not object]
    stub_bases = [ast.unparse(base) for base in stub_class.bases]
    if runtime_bases != stub_bases:
        problems.append(f"{class_name}: bases differ: extension {runtime_bases}, stub {stub_bases}")

    # AND the members match in both directions
    runtime_names = {name for name in vars(cls) if not _is_dunder(name)}
    runtime_names |= INSTANCE_ONLY.get(class_name, set())
    stub_names = {name for name in stub_members if not _is_dunder(name)}
    problems += _name_problems(class_name, runtime_names, stub_names)

    # AND the constructor and methods take the same parameters
    if not issubclass(cls, BaseException):
        init_defs = stub_members.get("__init__", [])
        if cls.__text_signature__ is None and init_defs:
            problems.append(f"{class_name}: stub defines __init__ but the extension has none")
        elif cls.__text_signature__ is not None:
            if not init_defs:
                problems.append(f"{class_name}: extension has a constructor but the stub has none")
            problems += _signature_problems(f"{class_name}.__init__", cls, init_defs, bound=True)

    for name in sorted(runtime_names & stub_names):
        defs = stub_members[name]
        runtime = getattr(cls, name, None)
        if defs and callable(runtime) and getattr(runtime, "__text_signature__", None):
            problems += _signature_problems(f"{class_name}.{name}", runtime, defs, bound=True)

    assert not problems, "\n" + "\n".join(problems)
