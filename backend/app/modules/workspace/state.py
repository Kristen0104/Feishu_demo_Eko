"""Workspace state and locking placeholders."""

from __future__ import annotations

# TODO(PRD-2.3): implement creator-only edit permissions, workspace locking, and cross-device state mirroring.


class WorkspaceLock:
    def acquire(self) -> None:
        raise NotImplementedError

    def release(self) -> None:
        raise NotImplementedError

