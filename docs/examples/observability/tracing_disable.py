"""Disable tracing example."""

from pydynox import disable_tracing, enable_tracing

# Enable tracing
enable_tracing()

# ... do some operations with tracing ...

# Disable when no longer needed
disable_tracing()
