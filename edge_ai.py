"""OPTIONAL Edge AI second opinion (advisory only, OFF by default).

Tiny logistic regression over hashed character 3-grams + a few numeric features.
Pure Python inference, runs on-device in well under 1 ms. No server, no API.
It NEVER changes the rule score or rating. If model.json is missing or broken,
predict() returns None and the app silently uses rules only.
"""
from __future__ import annotations

import json
import math
import re
import zlib
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "model.json"
_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_model = None
_loaded = False


def normalize(url: str) -> str:
    u = url.strip().lower()
    u = re.sub(r"^[a-z][a-z0-9+.\-]*://", "", u)  # dataset URLs mostly have no scheme
    return u[4:] if u.startswith("www.") else u


def _entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def features(url: str, dim: int) -> dict[int, float]:
    """Sparse feature vector: hashed char 3-grams + numeric features in the top slots."""
    u = normalize(url)[:300]
    host = re.split(r"[/?#]", u, 1)[0]
    feats: dict[int, float] = {}
    padded = f"^{u}$"
    grams = [padded[i:i + 3] for i in range(len(padded) - 2)]
    if grams:
        w = 1.0 / math.sqrt(len(grams))
        for g in grams:
            h = zlib.crc32(g.encode()) % dim
            feats[h] = feats.get(h, 0.0) + w
    n = max(len(u), 1)
    numeric = [
        min(len(u), 200) / 100,
        sum(c.isdigit() for c in u) / n * 5,
        min(host.count("-"), 6) / 3,
        min(host.count("."), 6) / 3,
        _entropy(u) / 5,
        1.0 if "@" in u else 0.0,
        1.0 if _IP_RE.match(host.split(":")[0]) else 0.0,
        1.0,  # bias
    ]
    for i, v in enumerate(numeric):
        feats[dim + i] = v
    return feats


def _load():
    global _model, _loaded
    if not _loaded:
        _loaded = True
        try:
            m = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
            w = [0.0] * (m["dim"] + m["n_numeric"])
            for k, v in m["weights"].items():
                w[int(k)] = v
            _model = {"dim": m["dim"], "w": w, "meta": m.get("meta", {})}
        except Exception:
            _model = None
    return _model


def available() -> bool:
    return _load() is not None


def meta() -> dict:
    m = _load()
    return m["meta"] if m else {}


def predict(url: str) -> float | None:
    """Probability (0..1) that the URL looks phishing-like, or None if no model."""
    try:
        m = _load()
        if m is None or not url or not url.strip():
            return None
        w = m["w"]
        z = sum(w[i] * v for i, v in features(url, m["dim"]).items() if i < len(w))
        z = max(-30.0, min(30.0, z))
        return 1.0 / (1.0 + math.exp(-z))
    except Exception:
        return None
