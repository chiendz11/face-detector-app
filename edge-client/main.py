from __future__ import annotations

from pathlib import Path
import sys


ROOT_SRC = Path(__file__).resolve().parent / "src"
if str(ROOT_SRC) not in sys.path:
    sys.path.insert(0, str(ROOT_SRC))

from edge_client.app import main

if __name__ == "__main__":
    main()
