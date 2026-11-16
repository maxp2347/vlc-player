import json
import os
import sys
import tempfile

DEFAULTS = {
    "volume": 70,
    "loop": False,
    "resume_last": False,
    "fullscreen_on_start": False,
    "prevent_sleep": True,
    "last_video": "",
}


def config_dir():
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    return os.path.join(base, "VLCPlayer")


def config_path():
    return os.path.join(config_dir(), "settings.json")


class Settings:
    def __init__(self):
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(config_path(), encoding="utf-8") as f:
                stored = json.load(f)
            self.data.update(
                {k: stored[k] for k in DEFAULTS if k in stored and type(stored[k]) is type(DEFAULTS[k])}
            )
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            os.makedirs(config_dir(), exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=config_dir(), suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp, config_path())
        except OSError as err:
            print(f"Impossible de sauvegarder les réglages : {err}")

    def reset(self):
        self.data = dict(DEFAULTS)
        self.save()

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
