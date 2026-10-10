"""Compatibility entry point: ``uvicorn app:app`` uses the packaged application."""

from civic_stack.app import app

__all__ = ["app"]
