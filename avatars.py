"""Hero characters: built-in SVG illustrations (offline), or your own photos.

To use real photos, put girl1..girl4 (.png/.jpg/.jpeg/.webp) in the assets/ folder.
"""
import base64
from pathlib import Path

ASSETS = Path(__file__).parent / "assets"
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

CHARACTERS = [
    dict(name="Zoya", slogan="Is this link sus? 👀 We'll tell you why.",
         skin="#f2c4a0", hair="#2b1a12", style="long", top="#ff4ecd", acc="sunglasses",
         bg=("#ff4ecd", "#7b2ff7")),
    dict(name="Maya", slogan="Trust, but verify. ✅",
         skin="#c68863", hair="#120c0a", style="bun", top="#00e5ff", acc="headphones",
         bg=("#00e5ff", "#1f6bff")),
    dict(name="Riya", slogan="No cap, just facts. 🧢",
         skin="#8d5a3b", hair="#5b2a86", style="bob", top="#ffd60a", acc="hoops",
         bg=("#ffd60a", "#ff7b00")),
    dict(name="Ana", slogan="Don't click. Check first. 🔍",
         skin="#ffe0c7", hair="#ff7eb6", style="long", top="#39ff14", acc="star",
         bg=("#39ff14", "#00b894")),
]


def _hair_back(style, c):
    if style == "long":
        return f'<path d="M48 112 Q42 34 100 32 Q158 34 152 112 L160 205 L40 205 Z" fill="{c}"/>'
    if style == "bun":
        return (f'<circle cx="100" cy="30" r="24" fill="{c}"/>'
                f'<path d="M58 110 Q56 50 100 50 Q144 50 142 110 Z" fill="{c}"/>')
    # bob
    return f'<path d="M50 140 Q40 40 100 38 Q160 40 150 140 Q100 150 50 140 Z" fill="{c}"/>'


def _accessory(kind):
    if kind == "sunglasses":
        return ('<g fill="#111" stroke="#111" stroke-width="2">'
                '<rect x="70" y="98" width="26" height="18" rx="8"/>'
                '<rect x="104" y="98" width="26" height="18" rx="8"/>'
                '<path d="M96 105 L104 105" fill="none"/></g>'
                '<path d="M74 102 L82 102" stroke="#fff" stroke-width="2" opacity=".6"/>'
                '<path d="M108 102 L116 102" stroke="#fff" stroke-width="2" opacity=".6"/>')
    if kind == "headphones":
        return ('<path d="M56 108 Q56 40 100 40 Q144 40 144 108" fill="none" stroke="#111" stroke-width="8"/>'
                '<rect x="48" y="98" width="16" height="30" rx="7" fill="#ff4ecd"/>'
                '<rect x="136" y="98" width="16" height="30" rx="7" fill="#ff4ecd"/>')
    if kind == "hoops":
        return ('<circle cx="62" cy="126" r="8" fill="none" stroke="#ffd60a" stroke-width="3"/>'
                '<circle cx="138" cy="126" r="8" fill="none" stroke="#ffd60a" stroke-width="3"/>')
    # star sticker on cheek
    return '<path d="M128 118 l3 6 6 1 -4.5 4 1 6 -5.5 -3 -5.5 3 1 -6 -4.5 -4 6 -1 z" fill="#ffd60a"/>'


def _svg(c):
    eyes = "" if c["acc"] == "sunglasses" else (
        '<ellipse cx="86" cy="108" rx="4.5" ry="5.5" fill="#1b1b1b"/>'
        '<ellipse cx="114" cy="108" rx="4.5" ry="5.5" fill="#1b1b1b"/>'
        '<circle cx="87.5" cy="106" r="1.5" fill="#fff"/><circle cx="115.5" cy="106" r="1.5" fill="#fff"/>'
        '<path d="M80 100 Q86 96 92 100 M108 100 Q114 96 120 100" stroke="#1b1b1b" stroke-width="2" fill="none"/>')
    a, b = c["bg"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 210">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs>
<rect width="200" height="210" fill="url(#g)"/>
<circle cx="30" cy="30" r="6" fill="#fff" opacity=".35"/><circle cx="172" cy="46" r="4" fill="#fff" opacity=".35"/>
{_hair_back(c["style"], c["hair"])}
<path d="M28 210 Q30 166 100 160 Q170 166 172 210 Z" fill="{c["top"]}" stroke="#111" stroke-width="2"/>
<rect x="89" y="138" width="22" height="26" rx="8" fill="{c["skin"]}"/>
<ellipse cx="100" cy="106" rx="38" ry="44" fill="{c["skin"]}"/>
<path d="M60 98 Q62 54 100 54 Q140 54 141 98 Q124 74 104 80 Q84 72 60 98 Z" fill="{c["hair"]}"/>
{eyes}
<circle cx="78" cy="123" r="6" fill="#ff6b9a" opacity=".45"/><circle cx="122" cy="123" r="6" fill="#ff6b9a" opacity=".45"/>
<path d="M89 127 Q100 138 111 127" stroke="#7a2e2e" stroke-width="3" fill="none" stroke-linecap="round"/>
{_accessory(c["acc"])}
</svg>'''


def image_uri(i: int) -> str:
    """Photo from assets/girl{i+1}.* if present, else the built-in illustration."""
    for ext, mime in MIME.items():
        p = ASSETS / f"girl{i + 1}{ext}"
        if p.exists():
            return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
    return "data:image/svg+xml;base64," + base64.b64encode(_svg(CHARACTERS[i]).encode()).decode()
