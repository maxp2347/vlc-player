def fmt_time(ms):
    if ms < 0:
        return "--:--"
    s = int(ms / 1000)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def new_media_entry(path):
    return {"path": path, "in_point": 0, "out_point": 0, "ignore": False,
            "volume_points": [[0, 100]]}


def envelope_value(points, t):
    if not points:
        return None
    pts = sorted(points)
    if t <= pts[0][0]:
        return pts[0][1]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        if t <= t1:
            ratio = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return v0 + (v1 - v0) * ratio
    return pts[-1][1]
