#!/usr/bin/env python3
"""Entry point for the ExamDNA Skill.

Locates the ``examdna`` package and runs its CLI:

1. a vendored copy next to this file (``scripts/examdna/``) — present in the
   distributed Skill zip;
2. otherwise the repository root (development checkout), found by walking up
   from this file until a directory containing ``examdna/__init__.py`` is found.

Only the Python standard library is required (Python 3.9+).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _locate() -> str:
    if os.path.isfile(os.path.join(HERE, "examdna", "__init__.py")):
        return HERE
    cur = HERE
    for _ in range(8):
        cur = os.path.dirname(cur)
        if os.path.isfile(os.path.join(cur, "examdna", "__init__.py")) and os.path.isfile(os.path.join(cur, "pyproject.toml")):
            return cur
    sys.stderr.write("examdna: could not find the examdna package next to this script or in a parent checkout.\n")
    sys.exit(1)


if sys.version_info < (3, 9):
    sys.stderr.write("examdna: Python 3.9 or newer is required.\n")
    sys.exit(1)

sys.path.insert(0, _locate())

from examdna.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
