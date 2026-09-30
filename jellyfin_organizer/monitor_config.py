from __future__ import annotations

import json
import os
import plistlib
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


APP_SLUG = "jellyfin-media-organizer"
APP_DIR_NAME = "Jellyfin Media Organizer"
WINDOWS_RUN_VALUE = "JellyfinMediaOrganizerMonitor"
MAC_LAUNCH_AGENT = "org.jellyfinmediaorganizer.monitor.plist"


def config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        path = base / "JellyfinMediaOrganizer"
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        path = base / APP_SLUG
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return config_dir() / "monitor-settings.json"


def heartbeat_path() -> Path:
    return config_dir() / "monitor-heartbeat.json"


def monitor_log_path() -> Path:
    return config_dir() / "monitor.log"


@dataclass(slots=True)
class MonitorSettings:
    enabled: bool = False
    folders: list[str] = field(default_factory=list)
    output_root: str = ""
    leftover_policy: str = "leave"
    start_at_login: bool = False
    poll_seconds: int = 5
    stable_seconds: int = 20


def load_monitor_settings() -> MonitorSettings:
    path = settings_path()
    if not path.exists():
        return MonitorSettings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return MonitorSettings()

    defaults = asdict(MonitorSettings())
    defaults.update({key: value for key, value in data.items() if key in defaults})
    try:
        return MonitorSettings(**defaults)
    except TypeError:
        return MonitorSettings()


def save_monitor_settings(settings: MonitorSettings) -> None:
    path = settings_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    tmp.replace(path)


def monitor_is_running(max_age_seconds: int = 30) -> bool:
    path = heartbeat_path()
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        updated = float(data.get("updated", 0))
    except Exception:
        return False
    return (time.time() - updated) <= max_age_seconds


def monitor_command() -> list[str]:
    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).resolve().parent
        names = ["JellyfinMediaMonitor.exe"] if sys.platform == "win32" else ["JellyfinMediaMonitor"]
        candidates: list[Path] = []
        for name in names:
            candidates.extend(
                [
                    app_dir / "monitor" / name,
                    app_dir / name,
                    app_dir.parent / "Resources" / "monitor" / name,
                ]
            )
        for candidate in candidates:
            if candidate.exists():
                return [str(candidate)]
        raise FileNotFoundError(
            "The background monitor executable was not found in this installation."
        )

    return [sys.executable, "-m", "jellyfin_organizer.monitor_service"]


def launch_monitor() -> None:
    if monitor_is_running():
        return
    command = monitor_command()
    kwargs: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = (
            getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        )
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(command, **kwargs)


def _quoted_command(command: list[str]) -> str:
    if sys.platform == "win32":
        return subprocess.list2cmdline(command)
    return " ".join(shlex.quote(part) for part in command)


def configure_autostart(enabled: bool) -> tuple[bool, str]:
    """Enable/disable monitor-at-login for the current user."""
    try:
        command = monitor_command()
    except FileNotFoundError as exc:
        return False, str(exc)

    try:
        if sys.platform == "win32":
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                if enabled:
                    winreg.SetValueEx(
                        key,
                        WINDOWS_RUN_VALUE,
                        0,
                        winreg.REG_SZ,
                        _quoted_command(command),
                    )
                else:
                    try:
                        winreg.DeleteValue(key, WINDOWS_RUN_VALUE)
                    except FileNotFoundError:
                        pass
            return True, ""

        if sys.platform == "darwin":
            launch_agents = Path.home() / "Library" / "LaunchAgents"
            launch_agents.mkdir(parents=True, exist_ok=True)
            path = launch_agents / MAC_LAUNCH_AGENT
            if enabled:
                payload = {
                    "Label": "org.jellyfinmediaorganizer.monitor",
                    "ProgramArguments": command,
                    "RunAtLoad": True,
                    "KeepAlive": False,
                    "StandardOutPath": str(monitor_log_path()),
                    "StandardErrorPath": str(monitor_log_path()),
                }
                path.write_bytes(plistlib.dumps(payload))
            else:
                path.unlink(missing_ok=True)
            return True, ""

        autostart = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart"
        autostart.mkdir(parents=True, exist_ok=True)
        path = autostart / "jellyfin-media-organizer-monitor.desktop"
        if enabled:
            path.write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Jellyfin Media Organizer Monitor\n"
                f"Exec={_quoted_command(command)}\n"
                "NoDisplay=true\n"
                "X-GNOME-Autostart-enabled=true\n",
                encoding="utf-8",
            )
        else:
            path.unlink(missing_ok=True)
        return True, ""
    except Exception as exc:
        return False, str(exc)
