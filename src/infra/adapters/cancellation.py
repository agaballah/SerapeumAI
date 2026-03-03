# -*- coding: utf-8 -*-

class CancellationError(Exception):
    """Raised when an operation is cancelled."""
    pass

class CancellationToken:
    """Token to signal and check for cancellation."""
    def __init__(self):
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def check(self):
        if self._cancelled:
            raise CancellationError("Operation was cancelled.")
