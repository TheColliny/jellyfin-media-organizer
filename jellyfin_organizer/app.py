from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QObject, QSize, QStandardPaths, QUrl
from PySide6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QDesktopServices,
    QFont,
    QIcon,
    QKeySequence,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .models import LeftoverPolicy, OperationAction, PlanStatus, PlannedOperation
from .operations import apply_plan, latest_completed_log, undo_log
from .monitor_config import (
    MonitorSettings,
    configure_autostart,
    launch_monitor,
    load_monitor_settings,
    monitor_is_running,
    monitor_log_path,
    save_monitor_settings,
)
from .planner import build_plan
from .scanner import scan_roots


APP_NAME = "Jellyfin Media Organizer"
APP_USER_MODEL_ID = "JellyfinMediaOrganizer.Desktop"
BUY_ME_A_COFFEE_URL = "https://buymeacoffee.com/thecolliny"
GITHUB_REPOSITORY = "TheColliny/jellyfin-media-organizer"
GITHUB_LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_REPOSITORY}/releases"


# The palette is intentionally derived from the supplied jellyfish/folder artwork:
# aqua + vivid blue as the primary colors, with coral, green and yellow accents.
APP_STYLESHEET = r"""
QMainWindow, QWidget#rootWidget {
    background: #eef8ff;
    color: #17324d;
}

QToolTip {
    background: #15335f;
    color: white;
    border: 1px solid #2bc7e7;
    padding: 6px;
}

QFrame#heroCard {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 #2fd0e9,
        stop: 0.47 #2b9cf4,
        stop: 1 #3158eb
    );
    border: 1px solid rgba(255, 255, 255, 120);
    border-radius: 22px;
}

QLabel#appTitle {
    color: white;
    font-size: 27px;
    font-weight: 800;
}

QLabel#appSubtitle {
    color: rgba(255, 255, 255, 225);
    font-size: 12px;
}

QLabel#versionBadge {
    color: white;
    background: rgba(11, 48, 135, 95);
    border: 1px solid rgba(255, 255, 255, 95);
    border-radius: 10px;
    padding: 6px 10px;
    font-weight: 700;
}

QPushButton#coffeeButton {
    min-height: 0px;
    padding: 0px;
    background: transparent;
    border: none;
    border-radius: 10px;
}
QPushButton#coffeeButton:hover {
    background: rgba(255, 255, 255, 28);
}
QPushButton#coffeeButton:pressed {
    background: rgba(10, 40, 110, 35);
}

QPushButton#updateLinkButton {
    min-height: 22px;
    padding: 1px 2px;
    color: rgba(255, 255, 255, 235);
    background: transparent;
    border: none;
    text-decoration: underline;
    font-size: 10px;
    font-weight: 650;
}
QPushButton#updateLinkButton:hover {
    color: white;
    background: rgba(255, 255, 255, 24);
}
QPushButton#updateLinkButton:pressed {
    color: #dff8ff;
}
QPushButton#updateLinkButton:disabled {
    color: rgba(255, 255, 255, 170);
    background: transparent;
    border: none;
}

QFrame#card {
    background: white;
    border: 1px solid #cfe9fb;
    border-radius: 18px;
}

QLabel#sectionTitle {
    color: #163a64;
    font-size: 16px;
    font-weight: 750;
}

QLabel#sectionHint {
    color: #63809a;
    font-size: 11px;
}

QLabel#pathLabel, QLabel#summaryLabel {
    background: #f5fbff;
    color: #284a67;
    border: 1px solid #d6edf9;
    border-radius: 10px;
    padding: 9px 11px;
}

QLabel#countBadge {
    color: #1d4f78;
    background: #def6ff;
    border: 1px solid #a9e6f6;
    border-radius: 10px;
    padding: 4px 9px;
    font-weight: 700;
}

QListWidget, QTableWidget {
    background: white;
    color: #17324d;
    border: 1px solid #bfe4f6;
    border-radius: 12px;
    selection-background-color: #d8f5ff;
    selection-color: #15385b;
    outline: none;
}

QListWidget {
    padding: 6px;
    font-size: 12px;
}

QListWidget::item {
    min-height: 28px;
    border-radius: 7px;
    padding-left: 5px;
}

QListWidget::item:hover {
    background: #eefaff;
}

QHeaderView::section {
    background: #e8f7ff;
    color: #245070;
    border: none;
    border-right: 1px solid #cce8f7;
    border-bottom: 1px solid #bfe1f5;
    padding: 8px 7px;
    font-weight: 750;
}

QTableWidget {
    gridline-color: #e2f0f8;
    alternate-background-color: #f8fcff;
}

QTableWidget::item {
    padding: 5px;
}

QPushButton {
    min-height: 34px;
    padding: 2px 13px;
    border-radius: 10px;
    font-weight: 700;
}

QPushButton#primaryButton {
    color: white;
    border: 1px solid #257bd8;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #25c8e8,
        stop: 1 #2d69ef
    );
}
QPushButton#primaryButton:hover {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #20b8dc,
        stop: 1 #225de0
    );
}
QPushButton#primaryButton:pressed {
    background: #2459cf;
}

QPushButton#successButton {
    color: white;
    border: 1px solid #1e9a68;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #41cf7d,
        stop: 1 #20a86a
    );
}
QPushButton#successButton:hover {
    background: #23b46f;
}

QPushButton#accentButton {
    color: white;
    border: 1px solid #e64f67;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #ff7a70,
        stop: 1 #ef4668
    );
}
QPushButton#accentButton:hover {
    background: #ed5265;
}

QPushButton#secondaryButton {
    color: #23567b;
    background: #f9fdff;
    border: 1px solid #b6dff2;
}
QPushButton#secondaryButton:hover {
    background: #e8f7ff;
    border-color: #7ecde9;
}

QPushButton:disabled {
    color: #8ba4b6;
    background: #e8f0f5;
    border: 1px solid #d2e0e8;
}

QProgressBar {
    min-height: 15px;
    max-height: 15px;
    border: 1px solid #b7ddec;
    border-radius: 7px;
    background: #e8f4fa;
    text-align: center;
    color: #24516f;
}

QProgressBar::chunk {
    border-radius: 6px;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #2dd0e7,
        stop: 0.55 #2f93f1,
        stop: 1 #4c63ea
    );
}

QSplitter::handle {
    background: transparent;
    width: 8px;
}


QComboBox, QSpinBox {
    min-height: 32px;
    padding: 2px 8px;
    color: #17324d;
    background: white;
    border: 1px solid #b6dff2;
    border-radius: 8px;
}
QComboBox:hover, QSpinBox:hover {
    border-color: #6fc9e7;
}
QCheckBox {
    color: #284a67;
    spacing: 8px;
}
QDialog {
    background: #eef8ff;
    color: #17324d;
}

QStatusBar {
    background: #e2f3fb;
    color: #3b637d;
    border-top: 1px solid #c7e4f1;
}
"""


def resource_path(*parts: str) -> Path:
    """Return a bundled resource path in source and PyInstaller builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent
    return base.joinpath(*parts)


def application_icon() -> QIcon:
    """Load the program icon used by the title bar, taskbar, and dialogs."""
    candidates = (
        resource_path("jellyfin_organizer", "assets", "JellyfinMediaOrganizer.png"),
        resource_path("jellyfin_organizer", "assets", "JellyfinMediaOrganizer.ico"),
    )
    for candidate in candidates:
        if candidate.exists():
            icon = QIcon(str(candidate))
            if not icon.isNull():
                return icon
    return QIcon()


def application_logo_pixmap() -> QPixmap:
    candidates = (
        resource_path("jellyfin_organizer", "assets", "JellyfinMediaOrganizer-256.png"),
        resource_path("jellyfin_organizer", "assets", "JellyfinMediaOrganizer.png"),
    )
    for candidate in candidates:
        if candidate.exists():
            pixmap = QPixmap(str(candidate))
            if not pixmap.isNull():
                return pixmap
    return QPixmap()


def coffee_pixmap() -> QPixmap:
    candidate = resource_path("jellyfin_organizer", "assets", "BuyMeACoffee.png")
    if candidate.exists():
        pixmap = QPixmap(str(candidate))
        if not pixmap.isNull():
            return pixmap
    return QPixmap()


def _version_tuple(value: str) -> tuple[int, ...]:
    """Compare ordinary release tags such as v0.4.1 without another dependency."""
    numbers = [int(part) for part in re.findall(r"\d+", value or "")][:4]
    numbers.extend([0] * (4 - len(numbers)))
    return tuple(numbers)


def _release_asset_for_platform(release: dict) -> dict | None:
    assets = [asset for asset in release.get("assets", []) if asset.get("browser_download_url")]
    if not assets:
        return None

    if sys.platform == "win32":
        candidates = [
            a for a in assets
            if str(a.get("name", "")).lower().endswith(".exe")
            and "monitor" not in str(a.get("name", "")).lower()
        ]
    elif sys.platform == "darwin":
        candidates = [
            a for a in assets
            if str(a.get("name", "")).lower().endswith((".pkg", ".dmg", ".zip"))
        ]
    else:
        candidates = [
            a for a in assets
            if str(a.get("name", "")).lower().endswith((".deb", ".appimage", ".rpm", ".tar.gz"))
        ]
    if not candidates:
        return None

    def score(asset: dict) -> tuple[int, int]:
        name = str(asset.get("name", "")).lower()
        if sys.platform == "win32":
            installer = "setup" in name or "installer" in name
        elif sys.platform == "darwin":
            installer = name.endswith((".pkg", ".dmg"))
        else:
            installer = name.endswith((".deb", ".appimage", ".rpm"))
        product_match = "jellyfin" in name and "organizer" in name
        return (1 if installer else 0, 1 if product_match else 0)

    return max(candidates, key=score)


def configure_windows_app_id() -> None:
    """Give Windows a stable taskbar/Start-menu identity for the application."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        # Cosmetic integration only; never prevent the application from starting.
        pass


class ScanWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        roots: list[Path],
        output_root: Path,
        leftover_policy: LeftoverPolicy,
    ):
        super().__init__()
        self.roots = roots
        self.output_root = output_root
        self.leftover_policy = leftover_policy

    def run(self) -> None:
        try:
            items = scan_roots(self.roots)
            plan = build_plan(
                items,
                self.output_root,
                leftover_policy=self.leftover_policy,
            )
            self.finished.emit(plan)
        except Exception as exc:
            self.failed.emit(str(exc))


class UpdateCheckWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def run(self) -> None:
        request = urllib.request.Request(
            GITHUB_LATEST_RELEASE_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"JellyfinMediaOrganizer/{__version__}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                self.failed.emit(
                    "No published GitHub release is available yet. "
                    "Once the repository has a published release, update checking will use it automatically."
                )
            elif exc.code == 403:
                self.failed.emit(
                    "GitHub temporarily refused the update request, usually because of a rate limit. "
                    "Please try again later."
                )
            else:
                self.failed.emit(f"GitHub returned HTTP {exc.code} while checking for updates.")
            return
        except Exception as exc:
            self.failed.emit(f"Could not contact GitHub.\n\n{exc}")
            return

        if not isinstance(payload, dict) or not payload.get("tag_name"):
            self.failed.emit("GitHub returned an unexpected release response.")
            return
        self.finished.emit(payload)


class UpdateDownloadWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)
    progress = Signal(int)

    def __init__(self, url: str, destination: Path):
        super().__init__()
        self.url = url
        self.destination = destination

    def run(self) -> None:
        part_path = self.destination.with_name(self.destination.name + ".part")
        request = urllib.request.Request(
            self.url,
            headers={"User-Agent": f"JellyfinMediaOrganizer/{__version__}"},
        )
        try:
            self.destination.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(request, timeout=30) as response:
                total = int(response.headers.get("Content-Length") or 0)
                downloaded = 0
                with part_path.open("wb") as handle:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            self.progress.emit(min(100, int(downloaded * 100 / total)))
            os.replace(part_path, self.destination)
        except Exception as exc:
            try:
                part_path.unlink(missing_ok=True)
            except Exception:
                pass
            self.failed.emit(f"Could not download the update.\n\n{exc}")
            return

        self.progress.emit(100)
        self.finished.emit(str(self.destination))


class DropListWidget(QListWidget):
    folders_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setAlternatingRowColors(False)
        self.setToolTip("Drag one or more folders from Explorer/Finder/file manager and drop them here.")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        paths = []
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_dir():
                paths.append(str(path))
        if paths:
            self.folders_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class MonitorDialog(QDialog):
    """Configure the small background monitor process."""

    def __init__(self, parent: "MainWindow"):
        super().__init__(parent)
        self.parent_window = parent
        self.settings = load_monitor_settings()
        self.monitor_output_root = Path(self.settings.output_root) if self.settings.output_root else None

        self.setWindowTitle("Folder Monitoring")
        self.setWindowIcon(application_icon())
        self.resize(680, 650)
        self.setMinimumSize(570, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("Background Folder Monitoring")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        hint = QLabel(
            "When enabled, a lightweight background process watches these folders recursively. "
            "Newly added or moved-in video files are processed only after they remain unchanged for the stability delay. "
            "Low-confidence matches are skipped rather than guessed."
        )
        hint.setObjectName("sectionHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.enable_check = QCheckBox("Enable automatic background monitoring")
        self.enable_check.setChecked(self.settings.enabled)
        layout.addWidget(self.enable_check)

        status_text = "Running" if monitor_is_running() else "Stopped"
        self.status_label = QLabel(f"Monitor status: {status_text}")
        self.status_label.setObjectName("summaryLabel")
        layout.addWidget(self.status_label)

        folders_title = QLabel("Folders to watch")
        folders_title.setObjectName("sectionTitle")
        layout.addWidget(folders_title)

        self.folder_list = QListWidget()
        self.folder_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for folder in self.settings.folders:
            self.folder_list.addItem(folder)
        layout.addWidget(self.folder_list, 1)

        folder_buttons = QHBoxLayout()
        add_button = QPushButton("＋ Add Watch Folder…")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self.add_folder)
        remove_button = QPushButton("Remove Selected")
        remove_button.setObjectName("secondaryButton")
        remove_button.clicked.connect(self.remove_selected)
        folder_buttons.addWidget(add_button)
        folder_buttons.addWidget(remove_button)
        layout.addLayout(folder_buttons)

        output_title = QLabel("Monitor output root")
        output_title.setObjectName("sectionTitle")
        layout.addWidget(output_title)

        if self.monitor_output_root is None and parent.output_root is not None:
            self.monitor_output_root = parent.output_root
        self.output_label = QLabel()
        self.output_label.setObjectName("pathLabel")
        self.output_label.setWordWrap(True)
        self.output_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._refresh_output_label()
        layout.addWidget(self.output_label)

        output_buttons = QHBoxLayout()
        choose_output = QPushButton("Choose Output Root…")
        choose_output.setObjectName("secondaryButton")
        choose_output.clicked.connect(self.choose_output)
        use_current = QPushButton("Use Organizer Output")
        use_current.setObjectName("secondaryButton")
        use_current.clicked.connect(self.use_organizer_output)
        output_buttons.addWidget(choose_output)
        output_buttons.addWidget(use_current)
        layout.addLayout(output_buttons)

        policy_title = QLabel("Leftover-file behavior while monitoring")
        policy_title.setObjectName("sectionTitle")
        layout.addWidget(policy_title)
        self.leftover_combo = QComboBox()
        self._populate_leftover_combo(self.leftover_combo)
        index = self.leftover_combo.findData(self.settings.leftover_policy)
        self.leftover_combo.setCurrentIndex(max(0, index))
        layout.addWidget(self.leftover_combo)

        stability_row = QHBoxLayout()
        stability_row.addWidget(QLabel("Wait until a new file is unchanged for:"))
        self.stable_spin = QSpinBox()
        self.stable_spin.setRange(5, 600)
        self.stable_spin.setSuffix(" seconds")
        self.stable_spin.setValue(max(5, int(self.settings.stable_seconds)))
        stability_row.addWidget(self.stable_spin)
        stability_row.addStretch(1)
        layout.addLayout(stability_row)

        self.autostart_check = QCheckBox("Start the background monitor automatically when I sign in")
        self.autostart_check.setChecked(self.settings.start_at_login)
        layout.addWidget(self.autostart_check)

        log_hint = QLabel(f"Monitor activity log: {monitor_log_path()}")
        log_hint.setObjectName("sectionHint")
        log_hint.setWordWrap(True)
        log_hint.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(log_hint)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save Monitoring Settings")
        save.setObjectName("successButton")
        save.clicked.connect(self.save_settings)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    @staticmethod
    def _populate_leftover_combo(combo: QComboBox) -> None:
        combo.addItem("Leave leftover files where they are", LeftoverPolicy.LEAVE.value)
        combo.addItem("Move associated leftover files with the organized media", LeftoverPolicy.MOVE.value)
        combo.addItem("Delete associated leftover files to Recycle Bin / Trash", LeftoverPolicy.DELETE.value)

    def _folders(self) -> list[str]:
        return [self.folder_list.item(i).text() for i in range(self.folder_list.count())]

    def _refresh_output_label(self) -> None:
        text = str(self.monitor_output_root) if self.monitor_output_root else "No output folder selected"
        self.output_label.setText(text)
        self.output_label.setToolTip(text)

    def add_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Folder to Monitor")
        if not path:
            return
        existing = set(self._folders())
        if path not in existing:
            self.folder_list.addItem(path)
        if self.monitor_output_root is None:
            self.monitor_output_root = Path(path)
            self._refresh_output_label()

    def remove_selected(self) -> None:
        for item in self.folder_list.selectedItems():
            self.folder_list.takeItem(self.folder_list.row(item))

    def choose_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Monitor Output Root")
        if path:
            self.monitor_output_root = Path(path)
            self._refresh_output_label()

    def use_organizer_output(self) -> None:
        if self.parent_window.output_root is None:
            QMessageBox.information(
                self,
                "No organizer output",
                "Add an input folder or choose an organizer output root first.",
            )
            return
        self.monitor_output_root = self.parent_window.output_root
        self._refresh_output_label()

    def save_settings(self) -> None:
        enabled = self.enable_check.isChecked()
        folders = self._folders()
        if enabled and not folders:
            QMessageBox.warning(self, "No watch folders", "Add at least one folder to monitor.")
            return

        if enabled and self.monitor_output_root is None:
            self.monitor_output_root = Path(folders[0])
            self._refresh_output_label()

        start_at_login = enabled and self.autostart_check.isChecked()
        settings = MonitorSettings(
            enabled=enabled,
            folders=folders,
            output_root=str(self.monitor_output_root) if self.monitor_output_root else "",
            leftover_policy=str(self.leftover_combo.currentData()),
            start_at_login=start_at_login,
            poll_seconds=5,
            stable_seconds=self.stable_spin.value(),
        )
        save_monitor_settings(settings)

        ok, message = configure_autostart(start_at_login)
        if not ok and start_at_login:
            QMessageBox.warning(
                self,
                "Could not configure startup",
                "Monitoring settings were saved, but automatic startup could not be configured.\n\n"
                + message,
            )

        if enabled:
            try:
                launch_monitor()
            except Exception as exc:
                QMessageBox.critical(
                    self,
                    "Could not start monitor",
                    f"The settings were saved, but the background monitor could not start.\n\n{exc}",
                )
                return
            QMessageBox.information(
                self,
                "Monitoring enabled",
                "Background monitoring is enabled. Existing video files are treated as the baseline; "
                "new or changed files will be organized after the stability delay.",
            )
        elif monitor_is_running():
            QMessageBox.information(
                self,
                "Monitoring disabled",
                "Monitoring has been disabled. The background process will exit after its next settings check.",
            )

        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(application_icon())
        self.resize(1420, 860)
        self.setMinimumSize(1040, 680)

        self.plan: list[PlannedOperation] = []
        self.output_root: Path | None = None
        self._output_is_default = True
        self.scan_thread: QThread | None = None
        self.scan_worker: ScanWorker | None = None
        self.update_thread: QThread | None = None
        self.update_worker: UpdateCheckWorker | None = None
        self.download_thread: QThread | None = None
        self.download_worker: UpdateDownloadWorker | None = None

        root = QWidget()
        root.setObjectName("rootWidget")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 16, 18, 12)
        root_layout.setSpacing(14)
        self.setCentralWidget(root)

        root_layout.addWidget(self._build_hero())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_source_card())
        splitter.addWidget(self._build_preview_card())
        splitter.setSizes([390, 1010])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        root_layout.addWidget(splitter, 1)

        self.statusBar().showMessage("Ready — add media folders to begin")

        try:
            settings = load_monitor_settings()
            if settings.enabled and not monitor_is_running():
                launch_monitor()
        except Exception:
            # Monitoring is optional and must never prevent the main GUI opening.
            pass

    def _build_hero(self) -> QFrame:
        hero = QFrame()
        hero.setObjectName("heroCard")
        hero.setMinimumHeight(202)
        hero.setMaximumHeight(218)

        layout = QHBoxLayout(hero)
        layout.setContentsMargins(22, 14, 20, 14)
        layout.setSpacing(18)

        logo = QLabel()
        logo.setFixedSize(126, 126)
        logo.setAlignment(Qt.AlignCenter)
        pixmap = application_logo_pixmap()
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(116, 116, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            shadow = QGraphicsDropShadowEffect(logo)
            shadow.setBlurRadius(20)
            shadow.setOffset(0, 5)
            shadow.setColor(QColor(0, 28, 90, 115))
            logo.setGraphicsEffect(shadow)
        layout.addWidget(logo, 0, Qt.AlignVCenter)

        text_box = QVBoxLayout()
        text_box.setSpacing(5)
        title = QLabel(APP_NAME)
        title.setObjectName("appTitle")
        title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text_box.addStretch(1)
        text_box.addWidget(title)
        subtitle = QLabel(
            "Turn messy movie and TV folders into clean, Jellyfin-friendly libraries — with a preview before anything moves."
        )
        subtitle.setObjectName("appSubtitle")
        subtitle.setWordWrap(True)
        text_box.addWidget(subtitle)
        text_box.addStretch(2)
        layout.addLayout(text_box, 1)

        right_width = 116
        right_box = QVBoxLayout()
        right_box.setContentsMargins(0, 0, 0, 0)
        right_box.setSpacing(5)

        version = QLabel(f"v{__version__}")
        version.setObjectName("versionBadge")
        version.setAlignment(Qt.AlignCenter)
        version.setFixedWidth(right_width)
        version.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        right_box.addWidget(version, 0, Qt.AlignRight)

        self.coffee_button = QPushButton()
        self.coffee_button.setObjectName("coffeeButton")
        self.coffee_button.setFixedSize(right_width, right_width)
        self.coffee_button.setCursor(Qt.PointingHandCursor)
        self.coffee_button.setToolTip("Buy Me a Coffee — opens buymeacoffee.com/thecolliny")
        coffee = coffee_pixmap()
        if not coffee.isNull():
            self.coffee_button.setIcon(QIcon(coffee))
            self.coffee_button.setIconSize(QSize(right_width - 4, right_width - 4))
        else:
            self.coffee_button.setText("Buy Me a Coffee")
        self.coffee_button.clicked.connect(self.open_buy_me_a_coffee)
        right_box.addWidget(self.coffee_button, 0, Qt.AlignRight)

        right_box.addStretch(1)
        self.update_button = QPushButton("Check for updates")
        self.update_button.setObjectName("updateLinkButton")
        self.update_button.setFixedWidth(right_width)
        self.update_button.setCursor(Qt.PointingHandCursor)
        self.update_button.setToolTip(f"Check {GITHUB_RELEASES_URL} for a newer release")
        self.update_button.clicked.connect(self.check_for_updates)
        right_box.addWidget(self.update_button, 0, Qt.AlignRight | Qt.AlignBottom)

        layout.addLayout(right_box)
        return hero

    def open_buy_me_a_coffee(self) -> None:
        QDesktopServices.openUrl(QUrl(BUY_ME_A_COFFEE_URL))

    def _reset_update_button(self) -> None:
        self.update_button.setEnabled(True)
        self.update_button.setText("Check for updates")

    def check_for_updates(self) -> None:
        if self.update_thread is not None and self.update_thread.isRunning():
            return

        self.update_button.setEnabled(False)
        self.update_button.setText("Checking…")
        self.statusBar().showMessage("Checking GitHub for updates…")

        self.update_thread = QThread(self)
        self.update_worker = UpdateCheckWorker()
        self.update_worker.moveToThread(self.update_thread)
        self.update_thread.started.connect(self.update_worker.run)
        self.update_worker.finished.connect(self._update_check_finished)
        self.update_worker.failed.connect(self._update_check_failed)
        self.update_worker.finished.connect(self.update_thread.quit)
        self.update_worker.failed.connect(self.update_thread.quit)
        self.update_worker.finished.connect(self.update_worker.deleteLater)
        self.update_worker.failed.connect(self.update_worker.deleteLater)
        self.update_thread.finished.connect(self._update_thread_finished)
        self.update_thread.start()

    def _update_thread_finished(self) -> None:
        thread = self.update_thread
        self.update_thread = None
        self.update_worker = None
        if thread is not None:
            thread.deleteLater()

    def _update_check_failed(self, message: str) -> None:
        self._reset_update_button()
        self.statusBar().showMessage("Update check could not be completed")
        QMessageBox.information(self, "Update check", message)

    def _update_check_finished(self, release: dict) -> None:
        self._reset_update_button()
        latest_tag = str(release.get("tag_name", "")).strip()
        latest_display = latest_tag.lstrip("vV") or latest_tag

        if _version_tuple(latest_tag) <= _version_tuple(__version__):
            self.statusBar().showMessage(f"Jellyfin Media Organizer v{__version__} is up to date")
            QMessageBox.information(
                self,
                "No update available",
                f"You are running the latest published version (v{__version__}).",
            )
            return

        self.statusBar().showMessage(f"Update {latest_display} is available")
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Update available")
        dialog.setWindowIcon(application_icon())
        dialog.setIcon(QMessageBox.Information)
        dialog.setText(
            f"Jellyfin Media Organizer {latest_display} is available.\n\n"
            f"Installed version: v{__version__}\n"
            f"Latest version: {latest_tag}"
        )
        dialog.setInformativeText("Would you like to download the newest release now?")
        download_button = dialog.addButton("Download", QMessageBox.AcceptRole)
        dialog.addButton("Maybe later", QMessageBox.RejectRole)
        dialog.exec()
        if dialog.clickedButton() is download_button:
            self._download_release(release)

    def _download_release(self, release: dict) -> None:
        asset = _release_asset_for_platform(release)
        if asset is None:
            reply = QMessageBox.information(
                self,
                "No installer asset found",
                "The latest GitHub release does not currently contain a downloadable installer for this platform.\n\n"
                "The release page will be opened instead.",
                QMessageBox.Ok | QMessageBox.Cancel,
                QMessageBox.Ok,
            )
            if reply == QMessageBox.Ok:
                QDesktopServices.openUrl(QUrl(str(release.get("html_url") or GITHUB_RELEASES_URL)))
            return

        name = Path(str(asset.get("name") or "JellyfinMediaOrganizer-update")).name
        url = str(asset["browser_download_url"])
        downloads = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
        destination_dir = Path(downloads) if downloads else Path.home() / "Downloads"
        destination = destination_dir / name

        self.update_button.setEnabled(False)
        self.update_button.setText("Downloading…")
        self.statusBar().showMessage(f"Downloading {name}…")

        self.download_thread = QThread(self)
        self.download_worker = UpdateDownloadWorker(url, destination)
        self.download_worker.moveToThread(self.download_thread)
        self.download_thread.started.connect(self.download_worker.run)
        self.download_worker.progress.connect(self._update_download_progress)
        self.download_worker.finished.connect(self._update_download_finished)
        self.download_worker.failed.connect(self._update_download_failed)
        self.download_worker.finished.connect(self.download_thread.quit)
        self.download_worker.failed.connect(self.download_thread.quit)
        self.download_worker.finished.connect(self.download_worker.deleteLater)
        self.download_worker.failed.connect(self.download_worker.deleteLater)
        self.download_thread.finished.connect(self._download_thread_finished)
        self.download_thread.start()

    def _download_thread_finished(self) -> None:
        thread = self.download_thread
        self.download_thread = None
        self.download_worker = None
        if thread is not None:
            thread.deleteLater()

    def _update_download_progress(self, percent: int) -> None:
        self.update_button.setText(f"Downloading {percent}%")
        self.statusBar().showMessage(f"Downloading update… {percent}%")

    def _update_download_failed(self, message: str) -> None:
        self._reset_update_button()
        self.statusBar().showMessage("Update download failed")
        QMessageBox.warning(self, "Download failed", message)

    def _update_download_finished(self, path_text: str) -> None:
        self._reset_update_button()
        path = Path(path_text)
        self.statusBar().showMessage(f"Update downloaded to {path}")

        dialog = QMessageBox(self)
        dialog.setWindowTitle("Update downloaded")
        dialog.setWindowIcon(application_icon())
        dialog.setIcon(QMessageBox.Information)
        dialog.setText(f"The latest release was downloaded to:\n\n{path}")
        open_button = dialog.addButton("Open installer", QMessageBox.AcceptRole)
        dialog.addButton("Close", QMessageBox.RejectRole)
        dialog.exec()
        if dialog.clickedButton() is open_button:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _build_source_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card.setMinimumWidth(340)
        card.setMaximumWidth(490)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(9)

        header = QHBoxLayout()
        title = QLabel("Media Sources")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.source_count = QLabel("0 folders")
        self.source_count.setObjectName("countBadge")
        header.addWidget(self.source_count)
        layout.addLayout(header)

        hint = QLabel("Drop folders below. Scanning is recursive, so nested season/movie folders are included.")
        hint.setObjectName("sectionHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.folder_list = DropListWidget()
        self.folder_list.setMinimumHeight(165)
        self.folder_list.folders_dropped.connect(self.add_paths)
        layout.addWidget(self.folder_list, 1)

        add_btn = QPushButton("＋  Add Folder…")
        add_btn.setObjectName("primaryButton")
        add_btn.clicked.connect(self.add_folder_dialog)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setObjectName("secondaryButton")
        remove_btn.clicked.connect(self.remove_selected)
        folder_buttons = QHBoxLayout()
        folder_buttons.setSpacing(8)
        folder_buttons.addWidget(add_btn, 1)
        folder_buttons.addWidget(remove_btn, 1)
        layout.addLayout(folder_buttons)

        output_title = QLabel("Organized Library Destination")
        output_title.setObjectName("sectionTitle")
        layout.addWidget(output_title)
        self.output_label = QLabel("Add an input folder to set the default output")
        self.output_label.setObjectName("pathLabel")
        self.output_label.setWordWrap(True)
        self.output_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.output_label)
        output_btn = QPushButton("Choose Different Output Root…")
        output_btn.setObjectName("secondaryButton")
        output_btn.clicked.connect(self.choose_output_root)
        layout.addWidget(output_btn)

        leftover_title = QLabel("Other files left in source folders")
        leftover_title.setObjectName("sectionTitle")
        layout.addWidget(leftover_title)
        self.leftover_combo = QComboBox()
        MonitorDialog._populate_leftover_combo(self.leftover_combo)
        self.leftover_combo.setToolTip(
            "Associated leftovers are only handled automatically when their source folder maps unambiguously to one organized destination."
        )
        layout.addWidget(self.leftover_combo)
        leftover_hint = QLabel(
            "Delete sends files to the operating system Recycle Bin/Trash. Ambiguous leftovers are always marked REVIEW and left untouched."
        )
        leftover_hint.setObjectName("sectionHint")
        leftover_hint.setWordWrap(True)
        layout.addWidget(leftover_hint)

        self.scan_btn = QPushButton("▶  Scan / Build Preview")
        self.scan_btn.setObjectName("primaryButton")
        self.scan_btn.clicked.connect(self.scan)
        layout.addWidget(self.scan_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        self.summary = QLabel("Nothing is changed during scanning. Review the plan before applying it.")
        self.summary.setObjectName("summaryLabel")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.apply_btn = QPushButton("✓  Apply Safe Actions")
        self.apply_btn.setObjectName("successButton")
        self.apply_btn.clicked.connect(self.apply)
        self.apply_btn.setEnabled(False)
        layout.addWidget(self.apply_btn)

        bottom_buttons = QHBoxLayout()
        undo_btn = QPushButton("↶  Undo Last Apply")
        undo_btn.setObjectName("accentButton")
        undo_btn.clicked.connect(self.undo)
        monitor_btn = QPushButton("⚙  Folder Monitoring…")
        monitor_btn.setObjectName("secondaryButton")
        monitor_btn.clicked.connect(self.open_monitor_dialog)
        bottom_buttons.addWidget(undo_btn, 1)
        bottom_buttons.addWidget(monitor_btn, 1)
        layout.addLayout(bottom_buttons)
        return card

    def _build_preview_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(9)

        header_row = QHBoxLayout()
        title = QLabel("Preview Queue")
        title.setObjectName("sectionTitle")
        header_row.addWidget(title)
        header_row.addStretch(1)
        self.remove_queue_btn = QPushButton("Remove Selected from Queue")
        self.remove_queue_btn.setObjectName("secondaryButton")
        self.remove_queue_btn.setEnabled(False)
        self.remove_queue_btn.clicked.connect(self.remove_selected_from_queue)
        header_row.addWidget(self.remove_queue_btn)
        layout.addLayout(header_row)

        hint = QLabel(
            "Ctrl/Command-click or Shift-click to select multiple rows. Press Delete/Backspace to remove selected items from this queue only."
        )
        hint.setObjectName("sectionHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Status", "Action", "Type", "Confidence", "Source", "Destination", "Primary", "Reason"]
        )
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.setTextElideMode(Qt.ElideMiddle)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.itemSelectionChanged.connect(self._preview_selection_changed)

        header = self.table.horizontalHeader()
        for col in (0, 1, 2, 3, 6):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        for col in (4, 5, 7):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        header.setStretchLastSection(True)
        self.table.setColumnWidth(4, 360)
        self.table.setColumnWidth(5, 400)
        self.table.setColumnWidth(7, 300)
        layout.addWidget(self.table, 1)

        detail = QFrame()
        detail.setObjectName("card")
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(10, 8, 10, 8)
        detail_layout.setSpacing(4)
        detail_title = QLabel("Selected row — full paths")
        detail_title.setObjectName("sectionHint")
        detail_layout.addWidget(detail_title)
        self.selected_source_label = QLabel("Source: —")
        self.selected_source_label.setWordWrap(True)
        self.selected_source_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.selected_destination_label = QLabel("Destination: —")
        self.selected_destination_label.setWordWrap(True)
        self.selected_destination_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        detail_layout.addWidget(self.selected_source_label)
        detail_layout.addWidget(self.selected_destination_label)
        layout.addWidget(detail)

        self.delete_shortcut = QShortcut(QKeySequence("Delete"), self.table)
        self.delete_shortcut.activated.connect(self.remove_selected_from_queue)
        self.backspace_shortcut = QShortcut(QKeySequence("Backspace"), self.table)
        self.backspace_shortcut.activated.connect(self.remove_selected_from_queue)
        return card

    @property
    def roots(self) -> list[Path]:
        return [Path(self.folder_list.item(i).text()) for i in range(self.folder_list.count())]

    def _set_output_root(self, path: Path | None, *, user_selected: bool) -> None:
        self.output_root = path
        self._output_is_default = not user_selected
        if path is None:
            text = "Add an input folder to set the default output"
        else:
            text = str(path)
        self.output_label.setText(text)
        self.output_label.setToolTip(text)

    def _update_source_count(self) -> None:
        count = self.folder_list.count()
        noun = "folder" if count == 1 else "folders"
        self.source_count.setText(f"{count} {noun}")

    def add_paths(self, paths: list[str]) -> None:
        existing = {str(p) for p in self.roots}
        added: list[Path] = []
        for raw in paths:
            p = Path(raw)
            if p.is_dir() and str(p) not in existing:
                self.folder_list.addItem(str(p))
                existing.add(str(p))
                added.append(p)
        self._update_source_count()
        if added and (self.output_root is None or self._output_is_default):
            self._set_output_root(self.roots[0], user_selected=False)

    def add_folder_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Media Folder")
        if path:
            self.add_paths([path])

    def remove_selected(self) -> None:
        for item in self.folder_list.selectedItems():
            self.folder_list.takeItem(self.folder_list.row(item))
        self._update_source_count()
        if self._output_is_default:
            self._set_output_root(self.roots[0] if self.roots else None, user_selected=False)

    def choose_output_root(self) -> None:
        start = str(self.output_root) if self.output_root else ""
        path = QFileDialog.getExistingDirectory(self, "Select Output Root", start)
        if path:
            self._set_output_root(Path(path), user_selected=True)

    def open_monitor_dialog(self) -> None:
        MonitorDialog(self).exec()

    def _leftover_policy(self) -> LeftoverPolicy:
        return LeftoverPolicy(str(self.leftover_combo.currentData()))

    def scan(self) -> None:
        if not self.roots:
            QMessageBox.warning(self, "No input folders", "Add at least one input folder.")
            return
        if self.output_root is None:
            self._set_output_root(self.roots[0], user_selected=False)

        self.scan_btn.setEnabled(False)
        self.apply_btn.setEnabled(False)
        self.progress.setRange(0, 0)
        self.summary.setText("Scanning recursively and building a safe preview…")
        self.table.setRowCount(0)
        self.plan = []
        self.statusBar().showMessage("Scanning media folders…")

        self.scan_thread = QThread(self)
        self.scan_worker = ScanWorker(self.roots, self.output_root, self._leftover_policy())
        self.scan_worker.moveToThread(self.scan_thread)
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.failed.connect(self.scan_failed)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.failed.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        self.scan_thread.start()

    def scan_finished(self, plan: list[PlannedOperation]) -> None:
        self.plan = plan
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.scan_btn.setEnabled(True)
        self.render_plan()
        self._update_plan_summary()

    def _update_plan_summary(self) -> None:
        ready = sum(op.status == PlanStatus.READY for op in self.plan)
        review = sum(op.status == PlanStatus.REVIEW for op in self.plan)
        skip = sum(op.status == PlanStatus.SKIP for op in self.plan)
        deletes = sum(op.status == PlanStatus.READY and op.action == OperationAction.DELETE for op in self.plan)
        delete_note = f" • {deletes} to Trash" if deletes else ""
        self.summary.setText(
            f"Queue: {ready} ready • {review} need review • {skip} already OK/skipped{delete_note}. "
            "Only READY rows still in the queue will be applied."
        )
        self.apply_btn.setEnabled(ready > 0)
        self.statusBar().showMessage(
            f"Preview ready — {ready} safe actions, {review} review items, {skip} skipped"
        )

    def scan_failed(self, message: str) -> None:
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.scan_btn.setEnabled(True)
        self.summary.setText("Scan failed. No files were changed.")
        self.statusBar().showMessage("Scan failed")
        QMessageBox.critical(self, "Scan failed", message)

    def _display_source(self, path: Path) -> str:
        matches: list[tuple[int, Path, Path]] = []
        for root in self.roots:
            try:
                relative = path.resolve().relative_to(root.resolve())
                matches.append((len(root.parts), root, relative))
            except (OSError, ValueError):
                continue
        if matches:
            _, root, relative = max(matches, key=lambda item: item[0])
            if str(relative) == ".":
                return root.name
            return str(Path(root.name) / relative)
        return str(path)

    def _display_destination(self, op: PlannedOperation) -> str:
        if op.action == OperationAction.DELETE:
            return "Recycle Bin / Trash"
        if op.destination is None:
            return "—"
        if self.output_root is not None:
            try:
                return str(op.destination.resolve().relative_to(self.output_root.resolve()))
            except (OSError, ValueError):
                pass
        return str(op.destination)

    def render_plan(self) -> None:
        status_theme = {
            PlanStatus.READY: ("#e8fff1", "#147a48"),
            PlanStatus.REVIEW: ("#fff6d8", "#8b6200"),
            PlanStatus.SKIP: ("#eaf5ff", "#275f9a"),
            PlanStatus.ERROR: ("#ffe8e8", "#a82a35"),
            PlanStatus.APPLIED: ("#e8f3ff", "#2a5b98"),
        }

        self.table.setRowCount(len(self.plan))
        for row, op in enumerate(self.plan):
            values = [
                op.status.value,
                op.action.value,
                op.kind.value,
                f"{op.confidence:.0%}",
                self._display_source(op.source),
                self._display_destination(op),
                "Yes" if op.is_primary else "No",
                op.reason,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 4:
                    item.setToolTip(str(op.source))
                elif col == 5:
                    item.setToolTip(
                        str(op.destination) if op.destination is not None else self._display_destination(op)
                    )
                else:
                    item.setToolTip(value)
                if col in (0, 1, 2, 3, 6):
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)

            background, foreground = status_theme.get(op.status, ("#eef4f7", "#355269"))
            status_item = self.table.item(row, 0)
            status_item.setBackground(QColor(background))
            status_item.setForeground(QColor(foreground))
            font = status_item.font()
            font.setBold(True)
            status_item.setFont(font)

        self._preview_selection_changed()

    def _selected_rows(self) -> list[int]:
        return sorted({index.row() for index in self.table.selectedIndexes()})

    def _preview_selection_changed(self) -> None:
        rows = self._selected_rows()
        self.remove_queue_btn.setEnabled(bool(rows))
        if len(rows) == 1 and 0 <= rows[0] < len(self.plan):
            op = self.plan[rows[0]]
            self.selected_source_label.setText(f"Source: {op.source}")
            if op.action == OperationAction.DELETE:
                destination = "Recycle Bin / Trash"
            else:
                destination = str(op.destination) if op.destination is not None else "—"
            self.selected_destination_label.setText(f"Destination: {destination}")
        elif len(rows) > 1:
            self.selected_source_label.setText(f"{len(rows)} rows selected")
            self.selected_destination_label.setText("Use Ctrl/Command-click or Shift-click to adjust the selection.")
        else:
            self.selected_source_label.setText("Source: —")
            self.selected_destination_label.setText("Destination: —")

    def remove_selected_from_queue(self) -> None:
        rows = self._selected_rows()
        if not rows:
            return

        remove_indexes = set(rows)
        selected_primary_groups = {
            self.plan[row].group_id
            for row in rows
            if 0 <= row < len(self.plan) and self.plan[row].is_primary and self.plan[row].group_id
        }
        # Removing a primary also removes its directly attached sidecars so we do
        # not move subtitles/artwork without the media file they belong to.
        for index, op in enumerate(self.plan):
            if op.group_id in selected_primary_groups and op.group_id and not op.is_primary:
                remove_indexes.add(index)

        removed = len(remove_indexes)
        self.plan = [op for index, op in enumerate(self.plan) if index not in remove_indexes]
        self.render_plan()
        self._update_plan_summary()
        self.statusBar().showMessage(f"Removed {removed} queued action(s); no files were changed on disk")

    def apply(self) -> None:
        if self.output_root is None:
            return

        ready = [op for op in self.plan if op.status == PlanStatus.READY]
        if not ready:
            QMessageBox.information(self, "Nothing to apply", "There are no READY actions.")
            return

        delete_count = sum(op.action == OperationAction.DELETE for op in ready)
        message = (
            f"This will apply {len(ready)} queued actions. Existing destinations are never overwritten."
        )
        if delete_count:
            message += (
                f"\n\n{delete_count} leftover file(s) will be sent to the operating system Recycle Bin/Trash. "
                "Jellyfin Media Organizer cannot automatically restore those delete actions; use the OS Trash if needed."
            )
        message += "\n\nContinue?"

        answer = QMessageBox.question(
            self,
            "Apply filesystem changes?",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.statusBar().showMessage("Applying queued actions…")
        try:
            log_dir = self.output_root / ".jellyfin-organizer-logs"
            log_path = apply_plan(self.plan, log_dir, cleanup_roots=self.roots)
        except Exception as exc:
            self.statusBar().showMessage("Apply stopped because of an error")
            QMessageBox.critical(
                self,
                "Apply stopped",
                "An error stopped the operation. The operation log can be used to inspect/undo completed moves.\n\n"
                f"{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Apply complete",
            f"Queued safe actions were applied. Empty source subfolders were removed where possible.\n\nOperation log:\n{log_path}",
        )
        self.scan()

    def undo(self) -> None:
        if self.output_root is None:
            QMessageBox.warning(self, "No output root", "Choose the same output root used for Apply.")
            return

        log_dir = self.output_root / ".jellyfin-organizer-logs"
        log_path = latest_completed_log(log_dir)
        if log_path is None:
            QMessageBox.information(self, "Nothing to undo", "No completed apply log was found.")
            return

        answer = QMessageBox.question(
            self,
            "Undo last apply?",
            f"Undo move operations recorded in:\n{log_path}\n\nFiles sent to Recycle Bin/Trash must be restored there manually.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.statusBar().showMessage("Undoing last completed apply…")
        try:
            undone, errors = undo_log(log_path)
        except Exception as exc:
            self.statusBar().showMessage("Undo failed")
            QMessageBox.critical(self, "Undo failed", str(exc))
            return

        if errors:
            QMessageBox.warning(
                self,
                "Undo partially complete",
                f"Restored {undone} moved files.\n\nNotes/problems:\n" + "\n".join(errors[:20]),
            )
            self.statusBar().showMessage(f"Undo partially complete — restored {undone} moved files")
        else:
            QMessageBox.information(self, "Undo complete", f"Restored {undone} moved files.")
            self.statusBar().showMessage(f"Undo complete — restored {undone} moved files")

        if self.roots:
            self.scan()


def main() -> None:
    configure_windows_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setDesktopFileName("jellyfin-media-organizer")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)

    icon = application_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)

    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
