#!/usr/bin/env python3
"""
Flowchart-MT Editor
===================
A tool for designing, translating, and testing multi-threaded programs
defined as sets of flowcharts (block diagrams).

Usage
-----
    python main.py
"""

import sys

# Ensure Python 3.9+
if sys.version_info < (3, 9):
    print("Python 3.9 or later is required.", file=sys.stderr)
    sys.exit(1)

from gui.app import Application


def main() -> None:
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
