"""python -m app.archdesk check [--free] : the Architecture Desk live check (archdesk/check.py)."""
import sys

from .check import main

if __name__ == "__main__":
    if sys.argv[1:2] == ["check"]:
        sys.exit(main(sys.argv[2:]))
    print("usage: python -m app.archdesk check [--free]")
