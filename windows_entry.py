"""PyInstaller entry point.

Keep this file at the project root instead of building jellyfin_organizer/app.py
as a standalone script.  The application uses package-relative imports, so it
must be imported as part of the jellyfin_organizer package.
"""

from jellyfin_organizer.app import main


if __name__ == "__main__":
    main()
