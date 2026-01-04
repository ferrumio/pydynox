"""Memory profiling tests for pydynox.

These tests work with both:
- memray: Memory leak detection
- codspeed: Performance tracking over time

Run with:
    uv run pytest tests/memory --memray      # Memory profiling
    uv run pytest tests/memory --codspeed    # Performance tracking
"""
