import json
import os

FIELDS = {
    "name": "",
    "path": "",
    "monitor": "",
    "width": 1920,
    "height": 1080,
    "refresh": 60,
    "decoder": "gpu",
    "audio": "default",
    "last_video": "",
    "media": [],
}

EXT = ".vlcproj.json"


class Project:
    def __init__(self, **kwargs):
        self.data = dict(FIELDS)
        self.data.update({k: v for k, v in kwargs.items() if k in FIELDS})

    @property
    def name(self):
        return self.data["name"]

    @property
    def file_path(self):
        return os.path.join(self.data["path"], self.data["name"] + EXT)

    def save(self):
        os.makedirs(self.data["path"], exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, file_path):
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        missing = {"name", "path"} - set(data)
        if missing:
            raise ValueError(f"Champs manquants dans le projet : {', '.join(sorted(missing))}")
        project = cls(**data)
        project.data["path"] = os.path.dirname(os.path.abspath(file_path))
        project.data["name"] = os.path.basename(file_path)[: -len(EXT)]
        return project

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        if key in FIELDS:
            self.data[key] = value
