"""Lifecycle hooks for Model operations.

Decorators to run code before/after save, delete, update operations.

Example:
    >>> from pydynox.hooks import before_save, after_save
    >>>
    >>> class User(Model):
    ...     @before_save
    ...     def validate_email(self):
    ...         if not self.email.endswith("@company.com"):
    ...             raise ValueError("Invalid email")
    ...
    ...     @after_save
    ...     def log_save(self):
    ...         print(f"User {self.pk} saved")
"""

from __future__ import annotations

from enum import Enum
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class HookType(Enum):
    """Types of lifecycle hooks."""

    BEFORE_SAVE = "before_save"
    AFTER_SAVE = "after_save"
    BEFORE_DELETE = "before_delete"
    AFTER_DELETE = "after_delete"
    BEFORE_UPDATE = "before_update"
    AFTER_UPDATE = "after_update"
    AFTER_LOAD = "after_load"


def before_save(func: F) -> F:
    """Run before save(). Use for validation or transformation."""
    setattr(func, "_hook_type", HookType.BEFORE_SAVE)
    return func


def after_save(func: F) -> F:
    """Run after save(). Use for logging or side effects."""
    setattr(func, "_hook_type", HookType.AFTER_SAVE)
    return func


def before_delete(func: F) -> F:
    """Run before delete(). Use for validation."""
    setattr(func, "_hook_type", HookType.BEFORE_DELETE)
    return func


def after_delete(func: F) -> F:
    """Run after delete(). Use for cleanup."""
    setattr(func, "_hook_type", HookType.AFTER_DELETE)
    return func


def before_update(func: F) -> F:
    """Run before update(). Use for validation."""
    setattr(func, "_hook_type", HookType.BEFORE_UPDATE)
    return func


def after_update(func: F) -> F:
    """Run after update(). Use for logging or side effects."""
    setattr(func, "_hook_type", HookType.AFTER_UPDATE)
    return func


def after_load(func: F) -> F:
    """Run after get() or query(). Use for transformation."""
    setattr(func, "_hook_type", HookType.AFTER_LOAD)
    return func
