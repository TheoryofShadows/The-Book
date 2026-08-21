"""Put tools/ on the import path.

The build scripts are scripts, not a package: they are meant to be run as
`python3 tools/parse_book.py`, and importing them is something only the tests
do. This keeps that knowledge in one file instead of six.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS = os.path.join(ROOT, "tools")

if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
