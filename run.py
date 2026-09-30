from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
VENV_DIR = PROJECT_DIR / ".venv"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def dependency_available(python_exe: Path) -> bool:
    try:
        result = subprocess.run(
            [str(python_exe), "-c", "import PySide6, send2trash"],
            cwd=PROJECT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except OSError:
        return False


def bootstrap() -> Path:
    py = venv_python()

    if not py.exists():
        print("First run: creating a private Python environment for Jellyfin Media Organizer...")
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)

    if not dependency_available(py):
        print("First run: installing application dependencies (PySide6 and send2trash). This only needs to happen once...")
        subprocess.check_call(
            [str(py), "-m", "pip", "install", "--upgrade", "pip"],
            cwd=PROJECT_DIR,
        )
        subprocess.check_call(
            [str(py), "-m", "pip", "install", "-e", "."],
            cwd=PROJECT_DIR,
        )

    return py


def main() -> int:
    try:
        py = bootstrap()
    except Exception as exc:
        print("\nCould not prepare the application environment.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        print("\nYou can also install manually with:", file=sys.stderr)
        print("  python -m pip install PySide6 send2trash", file=sys.stderr)
        return 1

    # Run the GUI using the private environment. This keeps dependencies out of the
    # user's global Python installation and makes subsequent launches fast.
    return subprocess.call(
        [str(py), "-m", "jellyfin_organizer.app"],
        cwd=PROJECT_DIR,
    )


if __name__ == "__main__":
    raise SystemExit(main())
