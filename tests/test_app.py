import json
import os
import struct
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mires
from project import Project, EXT
from settings import Settings, config_path


def test_settings_roundtrip():
    path_backup = os.environ.get("XDG_CONFIG_HOME")
    os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp()
    try:
        s = Settings()
        assert s["volume"] == 70 and s["prevent_sleep"] is True
        s["volume"] = 42
        s["last_video"] = "/tmp/v.mp4"
        s.save()
        s2 = Settings()
        assert s2["volume"] == 42 and s2["last_video"] == "/tmp/v.mp4"
        s2.reset()
        assert Settings()["volume"] == 70
    finally:
        if path_backup:
            os.environ["XDG_CONFIG_HOME"] = path_backup


def test_settings_rejects_bad_types():
    os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp()
    os.makedirs(config_path(), exist_ok=True)
    cfg = os.path.join(config_path(), "settings.json")
    with open(cfg, "w") as f:
        json.dump({"volume": "loud", "loop": "yes", "unknown_key": 1}, f)
    s = Settings()
    assert s["volume"] == 70 and s["loop"] is False


def test_project_save_load():
    folder = tempfile.mkdtemp()
    p = Project(name="demo", path=folder, monitor="HDMI-1", width=1920,
                height=1080, refresh=50, decoder="cpu", audio="alsa:hw:0")
    p["media"] = [{"path": "/a.mp4", "in_point": 500, "out_point": 9000,
                   "ignore": True, "volume_points": [[0, 80], [4000, 30]]}]
    p.save()
    assert os.path.isfile(p.file_path)
    assert p.file_path.endswith("demo" + EXT)
    loaded = Project.load(p.file_path)
    assert loaded.name == "demo"
    assert loaded["refresh"] == 50 and loaded["decoder"] == "cpu"
    assert loaded["media"][0]["out_point"] == 9000
    assert loaded["media"][0]["volume_points"][-1] == [4000, 30]


def test_project_load_rejects_incomplete():
    folder = tempfile.mkdtemp()
    bad = os.path.join(folder, "bad" + EXT)
    with open(bad, "w") as f:
        json.dump({"width": 1920}, f)
    try:
        Project.load(bad)
        raise AssertionError("ValueError attendu")
    except ValueError:
        pass


def test_fmt_time():
    from mediamodel import fmt_time
    assert fmt_time(-1) == "--:--"
    assert fmt_time(0) == "00:00"
    assert fmt_time(65_000) == "01:05"
    assert fmt_time(3_725_000) == "1:02:05"


def test_envelope_value():
    from mediamodel import envelope_value
    assert envelope_value([], 100) is None
    assert envelope_value([[5000, 40]], 0) == 40
    assert envelope_value([[5000, 40]], 9999) == 40
    assert envelope_value([[0, 100], [10_000, 0]], 5_000) == 50
    assert envelope_value([[0, 0], [1_000, 100], [2_000, 0]], 500) == 50
    assert envelope_value([[0, 0], [1_000, 100], [2_000, 0]], 1_500) == 50


def test_new_media_entry():
    from mediamodel import new_media_entry
    e = new_media_entry("/x/y.mp4")
    assert e == {"path": "/x/y.mp4", "in_point": 0, "out_point": 0,
                 "ignore": False, "volume_points": [[0, 100]]}


def test_vlc_audio_options():
    import hardware
    assert hardware.vlc_audio_options("default") == []
    assert hardware.vlc_audio_options("") == []
    assert hardware.vlc_audio_options("wasapi") == ["--aout=wasapi"]
    assert hardware.vlc_audio_options("directsound") == ["--aout=directsound"]
    assert hardware.vlc_audio_options("pulse") == ["--aout=pulse"]
    assert hardware.vlc_audio_options("alsa:hw:0,0") == \
        ["--aout=alsa", "--alsa-audio-device=hw:0,0"]
    assert hardware.vlc_audio_options("pulse:sortie.hdmi") == ["--aout=pulse"]
    assert hardware.vlc_audio_options("inconnu") == []


def test_static_mires():
    folder = tempfile.mkdtemp()
    for kind in mires.STATIC_MIRE_TYPES:
        path = mires.generate_static(kind, "1280x720", folder)
        assert os.path.isfile(path) and os.path.getsize(path) > 500, kind
        assert "1280x720" in os.path.basename(path)
    for kind in mires.STATIC_MIRE_TYPES:
        path = mires.generate_static(kind, "640x360", folder)
        assert os.path.isfile(path)


def _walk_avi(path):
    chunks = []
    with open(path, "rb") as f:
        data = f.read()
    assert data[:4] == b"RIFF" and data[8:12] == b"AVI "
    assert struct.unpack("<I", data[4:8])[0] == len(data) - 8
    assert data.find(b"strf") == 164
    assert data.find(b"movi") == 220
    pos = 224
    while pos < len(data):
        fourcc = data[pos:pos + 4]
        if fourcc == b"idx1":
            idx_size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
            assert idx_size % 16 == 0
            break
        ln = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        chunks.append((fourcc, ln))
        pos += 8 + ln + (ln % 2)
    return chunks


def test_dynamic_mires_avi_structure():
    folder = tempfile.mkdtemp()
    cases = [
        ("Barre défilante", "1920x1080", 50, 2, 1),
        ("Damier clignotant", "1280x720", 25, 2, 10),
        ("Cercle rotatif", "1280x720", 60, 1, 2),
    ]
    for kind, size, fps, duration, rate in cases:
        path = mires.generate_dynamic(kind, size, fps, duration, rate, folder)
        expected_frames = fps * duration
        chunks = _walk_avi(path)
        assert len(chunks) == expected_frames, (kind, len(chunks))
        assert all(c[0] == b"00dc" for c in chunks)
        with open(path, "rb") as f:
            f.seek(232)
            assert f.read(2) == b"\xff\xd8", "frame JPEG invalide"
            f.seek(48)
            assert struct.unpack("<I", f.read(4))[0] == expected_frames
        assert f"{fps}fps" in os.path.basename(path)


def test_mire_sizes_supported():
    folder = tempfile.mkdtemp()
    for size in mires.SIZES:
        path = mires.generate_static("Grille", size, folder)
        assert os.path.isfile(path)


def test_import_main_with_stubs():
    vlc = type(sys)("vlc")

    class _Enum:
        MediaPlayerEndReached = "end"
        local = 1

    class _State:
        Playing, Paused, Stopped = "p", "pa", "s"

    class _TrackType:
        video = "video"

    vlc.Instance = lambda *a: None
    vlc.EventType = _Enum
    vlc.State = _State
    vlc.TrackType = _TrackType
    vlc.MediaParseFlag = _Enum

    tk_stub = type(sys)("tkinter")

    class _W:
        def __init_subclass__(cls, **kw):
            pass

        def __init__(self, *a, **kw):
            pass

    class Tk(_W):
        pass

    class Frame(_W):
        pass

    class Canvas(_W):
        pass

    class Menu(_W):
        pass

    class Toplevel(_W):
        pass

    class Scale(_W):
        pass

    class Label(_W):
        pass

    class Button(_W):
        pass

    class Listbox(_W):
        pass

    for name, cls in [("Tk", Tk), ("Frame", Frame), ("Canvas", Canvas),
                      ("Menu", Menu), ("Toplevel", Toplevel), ("Scale", Scale),
                      ("Label", Label), ("Button", Button), ("Listbox", Listbox)]:
        setattr(tk_stub, name, cls)
    for const in ["END", "BOTH", "X", "LEFT", "RIGHT", "TOP", "HORIZONTAL", "VERTICAL"]:
        setattr(tk_stub, const, const)
    for var in ["StringVar", "IntVar", "BooleanVar"]:
        setattr(tk_stub, var, lambda *a, **k: None)

    saved = {k: sys.modules.get(k) for k in ("vlc", "tkinter",
                                             "tkinter.messagebox",
                                             "tkinter.filedialog",
                                             "tkinter.ttk")}
    sys.modules["vlc"] = vlc
    sys.modules["tkinter"] = tk_stub
    sys.modules["tkinter.messagebox"] = type(sys)("tkinter.messagebox")
    sys.modules["tkinter.filedialog"] = type(sys)("tkinter.filedialog")
    sys.modules["tkinter.ttk"] = type(sys)("tkinter.ttk")
    try:
        import importlib.util
        main_file = os.path.join(os.path.dirname(__file__), "..", "main.py")
        spec = importlib.util.spec_from_file_location("main_stubbed", main_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "VideoPlayer")
        assert hasattr(module, "MediaManagerDialog")
        assert hasattr(module, "MiresDialog")
        assert hasattr(module, "MismatchDialog")
        assert module.NewProjectDialog.REFRESH_RATES[0] == "25"
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"OK    {name}")
            except Exception as err:
                failures += 1
                print(f"ÉCHEC {name}: {err}")
    print(f"\n{'Tous les tests passent' if not failures else f'{failures} échec(s)'}")
    sys.exit(1 if failures else 0)
