"""Run all documentation examples to validate they work.

Usage:
    uv run python tests/examples/run_all_examples.py
"""

from __future__ import annotations

import importlib.util
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import boto3
import pydynox
from pydynox import DynamoDBClient
from testcontainers.localstack import LocalStackContainer

try:
    from tests.examples.fixtures import create_tables, populate_data
except ModuleNotFoundError:
    from fixtures import create_tables, populate_data

# Test credentials for LocalStack
TEST_REGION = "us-east-1"
TEST_ACCESS_KEY = "testing"
TEST_SECRET_KEY = "testing"

# Directories to skip entirely
SKIP_DIRS = {"agentic"}

# Files to skip (incomplete snippets, extra deps, LocalStack limitations, pytest-only)
SKIP_FILES = {
    "filter_condition.py",
    "query_gsi.py",
    "query_multi_attr.py",
    "range_key_condition.py",
    "fastapi_example.py",
    "create_table_multi_attr.py",
    "sdk_debug.py",
    # Testing examples - these use pytest fixtures, not standalone scripts
    "testing_query.py",
    "testing_scan.py",
    "testing_ttl.py",
    "query_scan.py",
    # Client projection examples - need specific table setup
    "client_projection.py",
    "nested_projection.py",
    # Type checking examples - TYPE_CHECKING blocks, not runnable
    "basic_types.py",
    "crud_types.py",
    "handle_none.py",
}


@dataclass
class ExampleResult:
    """Result of running an example."""

    path: str
    status: str  # pass, fail, skip
    duration_ms: float
    error: str | None = None

    @property
    def icon(self) -> str:
        return {"pass": "✅", "fail": "❌", "skip": "⏭️"}.get(self.status, "?")


def find_examples_dir() -> Path:
    """Find docs/examples directory from current file location."""
    current = Path(__file__).parent
    while current != current.parent:
        candidate = current / "pydynox" / "docs" / "examples"
        if candidate.exists():
            return candidate
        current = current.parent
    raise RuntimeError("Could not find docs/examples directory")


def discover_examples(examples_dir: Path) -> list[Path]:
    """Discover all runnable example files."""
    return sorted(
        p
        for p in examples_dir.rglob("*.py")
        if p.name not in SKIP_FILES and not any(d in p.parts for d in SKIP_DIRS)
    )


@contextmanager
def localstack_env(endpoint_url: str) -> Iterator[DynamoDBClient]:
    """Set up environment and yield a configured client."""
    os.environ.update(
        {
            "AWS_ENDPOINT_URL": endpoint_url,
            "AWS_ACCESS_KEY_ID": TEST_ACCESS_KEY,
            "AWS_SECRET_ACCESS_KEY": TEST_SECRET_KEY,
            "AWS_DEFAULT_REGION": TEST_REGION,
        }
    )

    client = DynamoDBClient(
        region=TEST_REGION,
        endpoint_url=endpoint_url,
        access_key=TEST_ACCESS_KEY,
        secret_key=TEST_SECRET_KEY,
    )
    pydynox.set_default_client(client)
    yield client


def setup_aws_services(endpoint_url: str) -> None:
    """Create KMS key and S3 bucket."""
    boto_kwargs = {
        "endpoint_url": endpoint_url,
        "region_name": TEST_REGION,
        "aws_access_key_id": TEST_ACCESS_KEY,
        "aws_secret_access_key": TEST_SECRET_KEY,
    }

    # KMS
    kms = boto3.client("kms", **boto_kwargs)
    key = kms.create_key(Description="Test key")
    kms.create_alias(AliasName="alias/my-app-key", TargetKeyId=key["KeyMetadata"]["KeyId"])

    # S3
    s3 = boto3.client("s3", **boto_kwargs)
    s3.create_bucket(Bucket="my-bucket")


def run_example(path: Path, examples_dir: Path, endpoint_url: str) -> ExampleResult:
    """Execute a single example file."""
    rel_path = str(path.relative_to(examples_dir))
    start = time.time()

    try:
        with localstack_env(endpoint_url):
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if spec is None or spec.loader is None:
                return ExampleResult(rel_path, "skip", 0, "Could not load module")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        return ExampleResult(rel_path, "pass", (time.time() - start) * 1000)

    except Exception as e:
        return ExampleResult(rel_path, "fail", (time.time() - start) * 1000, str(e))


def print_summary(results: list[ExampleResult]) -> int:
    """Print summary and return exit code."""
    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")
    skipped = sum(1 for r in results if r.status == "skip")
    total_ms = sum(r.duration_ms for r in results)

    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"Total time: {total_ms:.1f}ms")

    if failed:
        print("\n❌ Some examples failed!")
        return 1
    print("\n✅ All examples passed!")
    return 0


def main() -> None:
    """Run all examples."""
    print("🚀 Running all documentation examples...\n")

    # Start LocalStack
    print("🐳 Starting LocalStack...")
    container = LocalStackContainer(image="localstack/localstack:latest")
    container.with_services("dynamodb", "s3", "kms")
    container.start()
    time.sleep(2)

    endpoint_url = container.get_url()
    print(f"✅ LocalStack ready at {endpoint_url}\n")

    try:
        # Setup
        print("🔧 Setting up AWS services...")
        setup_aws_services(endpoint_url)

        with localstack_env(endpoint_url) as client:
            print("📦 Creating tables and data...")
            create_tables(client)
            populate_data(client)
            print("✅ Setup complete\n")

        # Discover and run examples
        examples_dir = find_examples_dir()
        examples = discover_examples(examples_dir)
        print(f"📝 Found {len(examples)} examples\n")

        results = []
        for path in examples:
            result = run_example(path, examples_dir, endpoint_url)
            results.append(result)
            print(f"{result.icon} {result.path} ({result.duration_ms:.1f}ms)")
            if result.error:
                print(f"   Error: {result.error}")

        exit_code = print_summary(results)

    finally:
        print("\n🛑 Stopping LocalStack...")
        container.stop()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
