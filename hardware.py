import ctypes
import re
import shutil
import subprocess
import sys


def list_monitors():
    if sys.platform.startswith("win"):
        return _monitors_windows()
    if sys.platform == "darwin":
        return _monitors_macos()
    return _monitors_linux()


def get_current_mode(monitor_id):
    if sys.platform.startswith("win"):
        return _current_mode_windows(monitor_id)
    if sys.platform == "darwin":
        return None
    return _current_mode_linux(monitor_id)


def set_display_mode(monitor_id, width, height, refresh):
    if not monitor_id:
        return False, "Aucun moniteur sélectionné."
    if sys.platform.startswith("win"):
        return _set_mode_windows(monitor_id, width, height, refresh)
    if sys.platform == "darwin":
        return _set_mode_macos(width, height, refresh)
    return _set_mode_linux(monitor_id, width, height, refresh)


def list_audio_outputs():
    outputs = [("default", "Défaut système")]
    if sys.platform.startswith("win"):
        outputs += [("wasapi", "WASAPI"), ("directsound", "DirectSound")]
    elif sys.platform == "darwin":
        pass
    else:
        if shutil.which("pactl"):
            try:
                out = subprocess.run(
                    ["pactl", "list", "short", "sinks"],
                    capture_output=True, text=True, timeout=5,
                ).stdout
                for line in out.splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        outputs.append((f"pulse:{parts[1]}", f"PulseAudio : {parts[1]}"))
            except (OSError, subprocess.TimeoutExpired):
                pass
        if shutil.which("aplay"):
            try:
                out = subprocess.run(
                    ["aplay", "-L"], capture_output=True, text=True, timeout=5
                ).stdout
                for block in out.split("\n\n"):
                    lines = block.strip().splitlines()
                    if len(lines) >= 2 and lines[0].strip() and not lines[0].startswith(" "):
                        device = lines[0].strip().rstrip(":")
                        desc = lines[1].strip()
                        if device in ("default", "null", "pulse"):
                            continue
                        outputs.append((f"alsa:{device}", f"ALSA : {desc}"))
            except (OSError, subprocess.TimeoutExpired):
                pass
        if not shutil.which("pactl") and not shutil.which("aplay"):
            outputs += [("pulse", "PulseAudio"), ("alsa", "ALSA")]
    return outputs


def vlc_audio_options(audio_choice):
    if not audio_choice or audio_choice == "default":
        return []
    if audio_choice.startswith("alsa:"):
        return ["--aout=alsa", f"--alsa-audio-device={audio_choice[5:]}"]
    if audio_choice.startswith("pulse:"):
        return ["--aout=pulse"]
    if audio_choice in ("pulse", "alsa", "wasapi", "directsound"):
        return [f"--aout={audio_choice}"]
    return []


def _monitors_windows():
    try:
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        monitors = []

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long),
            ]

        class MONITORINFOEXW(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_ulong),
                ("szDevice", ctypes.c_wchar * 32),
            ]

        proc = ctypes.WINFUNCTYPE(
            wintypes.HMONITOR, wintypes.HDC,
            ctypes.POINTER(RECT), wintypes.LPARAM,
        )

        def callback(hmon, hdc, rect, lparam):
            info = MONITORINFOEXW()
            info.cbSize = ctypes.sizeof(MONITORINFOEXW)
            if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
                r = info.rcMonitor
                monitors.append({
                    "id": info.szDevice,
                    "name": info.szDevice,
                    "x": r.left, "y": r.top,
                    "w": r.right - r.left, "h": r.bottom - r.top,
                    "primary": bool(info.dwFlags & 1),
                })
            return True

        user32.EnumDisplayMonitors(None, None, proc(callback), 0)
        return monitors
    except (OSError, AttributeError):
        return []


def _current_mode_windows(device_name):
    try:
        class DEVMODEW(ctypes.Structure):
            _fields_ = [
                ("dmDeviceName", ctypes.c_wchar * 32),
                ("dmSpecVersion", ctypes.c_ushort),
                ("dmDriverVersion", ctypes.c_ushort),
                ("dmSize", ctypes.c_ushort),
                ("dmDriverExtra", ctypes.c_ushort),
                ("dmFields", ctypes.c_ulong),
                ("dmPositionX", ctypes.c_long),
                ("dmPositionY", ctypes.c_long),
                ("dmDisplayOrientation", ctypes.c_ulong),
                ("dmDisplayFixedOutput", ctypes.c_ulong),
                ("dmColor", ctypes.c_short),
                ("dmDuplex", ctypes.c_short),
                ("dmYResolution", ctypes.c_short),
                ("dmTTOption", ctypes.c_short),
                ("dmCollate", ctypes.c_short),
                ("dmFormName", ctypes.c_wchar * 32),
                ("dmLogPixels", ctypes.c_ushort),
                ("dmBitsPerPel", ctypes.c_ulong),
                ("dmPelsWidth", ctypes.c_ulong),
                ("dmPelsHeight", ctypes.c_ulong),
                ("dmDisplayFlags", ctypes.c_ulong),
                ("dmDisplayFrequency", ctypes.c_ulong),
            ]

        dm = DEVMODEW()
        dm.dmSize = ctypes.sizeof(DEVMODEW)
        if ctypes.windll.user32.EnumDisplaySettingsW(device_name, -1, ctypes.byref(dm)):
            return (dm.dmPelsWidth, dm.dmPelsHeight, dm.dmDisplayFrequency)
    except (OSError, AttributeError):
        pass
    return None


def _set_mode_windows(device_name, width, height, refresh):
    current = _current_mode_windows(device_name)
    if not current:
        return False, f"Écran {device_name} introuvable."

    class DEVMODEW(ctypes.Structure):
        _fields_ = [
            ("dmDeviceName", ctypes.c_wchar * 32),
            ("dmSpecVersion", ctypes.c_ushort),
            ("dmDriverVersion", ctypes.c_ushort),
            ("dmSize", ctypes.c_ushort),
            ("dmDriverExtra", ctypes.c_ushort),
            ("dmFields", ctypes.c_ulong),
            ("dmPositionX", ctypes.c_long),
            ("dmPositionY", ctypes.c_long),
            ("dmDisplayOrientation", ctypes.c_ulong),
            ("dmDisplayFixedOutput", ctypes.c_ulong),
            ("dmColor", ctypes.c_short),
            ("dmDuplex", ctypes.c_short),
            ("dmYResolution", ctypes.c_short),
            ("dmTTOption", ctypes.c_short),
            ("dmCollate", ctypes.c_short),
            ("dmFormName", ctypes.c_wchar * 32),
            ("dmLogPixels", ctypes.c_ushort),
            ("dmBitsPerPel", ctypes.c_ulong),
            ("dmPelsWidth", ctypes.c_ulong),
            ("dmPelsHeight", ctypes.c_ulong),
            ("dmDisplayFlags", ctypes.c_ulong),
            ("dmDisplayFrequency", ctypes.c_ulong),
        ]

    dm = DEVMODEW()
    dm.dmSize = ctypes.sizeof(DEVMODEW)
    if not ctypes.windll.user32.EnumDisplaySettingsW(device_name, -1, ctypes.byref(dm)):
        return False, "Réglages actuels illisibles."
    dm.dmFields = 0x00080000 | 0x00100000 | 0x00400000
    dm.dmPelsWidth = width
    dm.dmPelsHeight = height
    if refresh:
        dm.dmDisplayFrequency = refresh
    result = ctypes.windll.user32.ChangeDisplaySettingsExW(
        device_name, ctypes.byref(dm), None, 0x00000002, None
    )
    if result == 0:
        return True, "Résolution appliquée."
    return False, f"Changement refusé par le pilote (code {result})."


def _monitors_linux():
    if not shutil.which("xrandr"):
        return []
    try:
        out = subprocess.run(
            ["xrandr", "--query"], capture_output=True, text=True, timeout=5
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    monitors = []
    for line in out.splitlines():
        m = re.match(r"^(\S+) connected (?:primary )?(\d+)x(\d+)\+(\d+)\+(\d+)", line)
        if m:
            name, w, h, x, y = m.groups()
            monitors.append({
                "id": name, "name": name,
                "x": int(x), "y": int(y), "w": int(w), "h": int(h),
                "primary": "primary" in line,
            })
    return monitors


_XR = {}


def _xrandr_state():
    if "modes" in _XR:
        return _XR
    modes = {}
    current = {}
    output = None
    try:
        out = subprocess.run(
            ["xrandr", "--query"], capture_output=True, text=True, timeout=5
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        out = ""
    for line in out.splitlines():
        m = re.match(r"^(\S+) (connected|disconnected)", line)
        if m:
            output = m.group(1)
            modes[output] = []
            cur = re.search(r"(\d+)x(\d+)\+(\d+)\+(\d+)", line)
            if cur and m.group(2) == "connected":
                current[output] = (int(cur.group(1)), int(cur.group(2)), None)
            continue
        m = re.match(r"^\s+(\d+)x(\d+)\s+([\d.]+)[*\s+]", line)
        if m and output:
            w, h, rate = int(m.group(1)), int(m.group(2)), float(m.group(3))
            modes[output].append((w, h, rate))
            if "*" in line and output in current:
                current[output] = (w, h, rate)
    _XR["modes"] = modes
    _XR["current"] = current
    return _XR


def _current_mode_linux(output):
    return _xrandr_state()["current"].get(output)


def _set_mode_linux(output, width, height, refresh):
    if not shutil.which("xrandr"):
        return False, "xrandr indisponible ( Wayland non supporté)."
    modes = _xrandr_state()["modes"].get(output, [])
    candidates = [m for m in modes if m[0] == width and m[1] == height]
    if not candidates:
        return False, f"Mode {width}x{height} non disponible sur {output}."
    if refresh:
        exact = [m for m in candidates if abs(m[2] - float(refresh)) < 0.5]
        if not exact:
            rates = ", ".join(str(m[2]) for m in candidates)
            return False, f"{width}x{height} disponible mais pas à {refresh} Hz (fréquences : {rates})."
    cmd = ["xrandr", "--output", output, "--mode", f"{width}x{height}"]
    if refresh:
        cmd += ["--rate", str(refresh)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if proc.returncode == 0:
        _XR.pop("modes", None)
        return True, "Résolution appliquée."
    return False, f"xrandr a échoué : {proc.stderr.strip()}"


def _monitors_macos():
    if not shutil.which("displayplacer"):
        return [{
            "id": "main", "name": "Écran principal (installez displayplacer pour plus de détails)",
            "x": 0, "y": 0, "w": 0, "h": 0, "primary": True,
        }]
    try:
        out = subprocess.run(
            ["displayplacer", "list"], capture_output=True, text=True, timeout=5
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    monitors = []
    screen_id = None
    for line in out.splitlines():
        m = re.search(r"id:(\S+)", line)
        if m:
            screen_id = m.group(1)
        m = re.search(r"origin:\((\d+),\s*(\d+)\).*?resolution:\((\d+)x(\d+)\)", line)
        if m and screen_id:
            x, y, w, h = map(int, m.groups())
            monitors.append({
                "id": screen_id, "name": f"Écran {len(monitors) + 1} ({screen_id[:8]}…)",
                "x": x, "y": y, "w": w, "h": h, "primary": len(monitors) == 0,
            })
    return monitors


def _set_mode_macos(width, height, refresh):
    if not shutil.which("displayplacer"):
        return False, "Changement de résolution sur macOS nécessite 'displayplacer' (brew install displayplacer)."
    proc = subprocess.run(
        ["displayplacer", f"res:{width}x{height}" + (f" hz:{refresh}" if refresh else "")],
        capture_output=True, text=True, timeout=10,
    )
    if proc.returncode == 0:
        return True, "Résolution appliquée."
    return False, f"displayplacer a échoué : {proc.stderr.strip()}"
