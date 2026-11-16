import ctypes
import shutil
import subprocess
import sys


class KeepAwake:
    def __init__(self):
        self.active = False
        self.method = None
        self._proc = None
        self._assertion_id = None
        self._gsettings_restore = None

    def start(self):
        if self.active:
            return
        if sys.platform.startswith("win"):
            self._start_windows()
        elif sys.platform == "darwin":
            self._start_macos()
        else:
            self._start_linux()
        if self.active:
            print(f"Anti-veille activé ({self.method})")

    def stop(self):
        if not self.active:
            return
        if sys.platform.startswith("win"):
            ES_CONTINUOUS = 0x80000000
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        elif sys.platform == "darwin":
            iokit = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
            iokit.IOPMAssertionRelease(ctypes.c_uint32(self._assertion_id))
            self._assertion_id = None
        else:
            if self._proc:
                self._proc.terminate()
                self._proc = None
            if self._gsettings_restore is not None:
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.session", "idle-delay",
                     str(self._gsettings_restore)],
                    capture_output=True,
                )
                self._gsettings_restore = None
        self.active = False
        self.method = None

    def _start_windows(self):
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        result = ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
        self.active = bool(result)
        self.method = "SetThreadExecutionState"

    def _start_macos(self):
        try:
            cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
            iokit = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
            cf.CFStringCreateWithCString.restype = ctypes.c_void_p
            cf.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
            iokit.IOPMAssertionCreateWithName.restype = ctypes.c_int
            iokit.IOPMAssertionCreateWithName.argtypes = [
                ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint32),
            ]
            kCFStringEncodingUTF8 = 0x08000100
            assert_type = cf.CFStringCreateWithCString(None, b"PreventUserIdleDisplaySleep", kCFStringEncodingUTF8)
            reason = cf.CFStringCreateWithCString(None, b"VLCPlayer playback", kCFStringEncodingUTF8)
            assertion_id = ctypes.c_uint32(0)
            status = iokit.IOPMAssertionCreateWithName(assert_type, 255, reason, ctypes.byref(assertion_id))
            if status == 0:
                self._assertion_id = assertion_id.value
                self.active = True
                self.method = "IOPMAssertion"
        except (OSError, AttributeError):
            pass

    def _start_linux(self):
        if shutil.which("systemd-inhibit"):
            try:
                self._proc = subprocess.Popen(
                    ["systemd-inhibit", "--what=sleep:idle", "--who=VLCPlayer",
                     "--mode=block", "sleep", "infinity"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                self.active = True
                self.method = "systemd-inhibit"
                return
            except OSError:
                pass
        if shutil.which("gsettings"):
            try:
                current = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.session", "idle-delay"],
                    capture_output=True, text=True,
                )
                old = current.stdout.strip()
                if old and old != "uint32 0" and old != "0":
                    self._gsettings_restore = old.replace("uint32", "").strip()
                subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.session", "idle-delay", "0"],
                    capture_output=True,
                )
                self.active = True
                self.method = "gsettings (GNOME)"
            except OSError:
                pass
