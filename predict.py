from pathlib import Path
import os
import runpy
import sys


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent
    shepherd_dir = repo_root / "shepherd"
    os.chdir(shepherd_dir)
    sys.path.insert(0, str(shepherd_dir))
    runpy.run_path("predict.py", run_name="__main__")
