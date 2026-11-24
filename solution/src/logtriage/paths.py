"""The log root and the screening of every path under it."""

from __future__ import annotations

import os
import stat

from fastmcp.exceptions import ToolError

from . import errors


class LogRoot:
    """The log root, resolved once at startup. Only what lies below it is screened, so the root may sit
    under symlinks; a symlink met below it is refused wherever it appears."""

    def __init__(self, given: str) -> None:
        self.alias = os.path.abspath(given)
        self.real = os.path.realpath(given)

    def resolve(self, path: str) -> str:
        """The absolute location of `path` under the root, or a ToolError with E1 or E2.

        `path` is relative to the root, or absolute inside it. It is refused (E1) when it holds a NUL byte,
        leaves the root, or passes through a symlink, the file itself or a folder on the way. A path that passes
        and is not there is E2. The same check runs again before a stored path is opened a second time."""
        if "\0" in path:
            raise ToolError(errors.path_outside(path))
        parts = self._parts_below_root(path)
        if parts is None:
            raise ToolError(errors.path_outside(path))
        current = self.real
        for part in parts:
            current = os.path.join(current, part)
            try:
                mode = os.lstat(current).st_mode
            except OSError:
                raise ToolError(errors.path_missing(path)) from None
            if stat.S_ISLNK(mode):
                raise ToolError(errors.path_outside(path))
        return current

    def _parts_below_root(self, path: str) -> list[str] | None:
        if os.path.isabs(path):
            target = os.path.normpath(path)
            for base in (self.real, self.alias):
                if os.path.commonpath([base, target]) == base:
                    relative = os.path.relpath(target, base)
                    return [] if relative == "." else relative.split(os.sep)
            return None
        relative = os.path.normpath(path or ".")
        if relative == ".." or relative.startswith(".." + os.sep):
            return None
        return [] if relative == "." else relative.split(os.sep)

    def relative(self, location: str) -> str:
        """Output form: relative to the root, `/`-separated, `.` for the root itself."""
        return os.path.relpath(location, self.real).replace(os.sep, "/")
