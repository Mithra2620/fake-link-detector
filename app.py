"""Streamlit UI. Run: streamlit run app.py"""
import csv
import html
import io
import json
from datetime import datetime
from pathlib import Path

import streamlit as st

import config as C
from avatars import CHARACTERS, image_uri
from detector import analyze_many
import edge_ai
import qr

SAFE_EXAMPLE = "https://www.example.com/about"
RISKY_EXAMPLE = ("http://secure-login-verify-account.example-bank.com/signin/confirm"
                 "?session=8f3a9c2b1d7e4a6f&redirect=update-billing-info-now")
BATCH_EXAMPLE = "\n".join([
    SAFE_EXAMPLE, RISKY_EXAMPLE, "http://www.paypal.com@evil.com",
    "http://192.168.1.1/login", "https://paypal.account-check.xyz/", "not a url",
])

COLORS = {"Low": "#39ff14", "Medium": "#ffb703", "High": "#ff3864", None: "#9a8fb5"}
ICONS = {"Low": "🟢", "Medium": "🟠", "High": "🔴", None: "⚪"}
SEV_ICON = {"danger": "🔴", "warn": "🟠", "info": "ℹ️"}
VERDICT = {
    "Low": ("Looks clean ✨", "No red flags spotted. Still, stay alert."),
    "Medium": ("Kinda sus 🤨", "A few warning signs. Double-check before you click."),
    "High": ("Major red flag 🚩", "Do NOT click unless you are 100% sure who sent it."),
    None: ("That's not a link, bestie 💀", ""),
}
TICKER = ["Is this link sus? 👀", "Trust, but verify ✅", "No cap, just facts 🧢",
          "Don't click. Check first 🔍", "Runs offline 📴", "Links are never opened 🔒",
          "Every rating explained 🧠"]

st.set_page_config(page_title="Fake Link Detector", page_icon="🔗", layout="wide", initial_sidebar_state="collapsed")

CSS = """
<style>
.stApp {
  background:
    radial-gradient(circle at 10% 10%, rgba(255,78,205,.25), transparent 40%),
    radial-gradient(circle at 90% 20%, rgba(0,229,255,.20), transparent 40%),
    radial-gradient(circle at 50% 100%, rgba(123,47,247,.30), transparent 50%),
    #0b0420;
}
.block-container { max-width: 1100px; padding-top: 1.5rem; }
header[data-testid="stHeader"] { background: transparent; }

.ticker { overflow: hidden; white-space: nowrap; border-radius: 999px; padding: 8px 0;
  background: linear-gradient(90deg, #ff4ecd, #7b2ff7, #00e5ff); margin-bottom: 18px; }
.ticker span { display: inline-block; padding-left: 100%; animation: scroll 28s linear infinite;
  font-weight: 800; color: #0b0420; letter-spacing: .5px; }
.ticker b { margin: 0 28px; }
@keyframes scroll { to { transform: translateX(-100%); } }

.hero h1 { font-size: clamp(2.2rem, 6vw, 4.2rem); line-height: 1.02; margin: 0; font-weight: 900; }
.hero h1 .grad {
  background: linear-gradient(90deg, #ff4ecd, #ffd60a, #00e5ff); -webkit-background-clip: text;
  background-clip: text; color: transparent; }
.hero p.sub { font-size: 1.25rem; color: #d9cffb; margin: 8px 0 20px; }
.hero p.sub b { color: #fff; }

.squad { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 6px 0 22px; }
@media (max-width: 760px) { .squad { grid-template-columns: repeat(2, 1fr); } }
.girl { display: flex; flex-direction: column; gap: 10px; animation: float 4s ease-in-out infinite; }
.girl:nth-child(2) { animation-delay: .6s; } .girl:nth-child(3) { animation-delay: 1.2s; }
.girl:nth-child(4) { animation-delay: 1.8s; }
.girl img { width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block; border-radius: 24px;
  border: 3px solid rgba(255,255,255,.22); box-shadow: 0 10px 30px rgba(0,0,0,.45); }
.bubble { position: relative; padding: 10px 12px; border-radius: 16px; background: #fff;
  color: #0b0420; font-weight: 800; font-size: 1rem; line-height: 1.25; text-align: center; }
.bubble::before { content: ""; position: absolute; top: -9px; left: 50%; transform: translateX(-50%);
  border: 10px solid transparent; border-top: 0; border-bottom-color: #fff; }
.bubble small { display: block; color: #c2187a; font-weight: 800; font-size: .7rem;
  text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px; }
@keyframes float { 50% { transform: translateY(-8px) rotate(-.6deg); } }

.banner { border-radius: 16px; padding: 12px 16px; margin-bottom: 14px; color: #e9e3ff;
  background: rgba(0,229,255,.10); border: 1px solid rgba(0,229,255,.45); }

.stTextArea textarea { background: rgba(26,11,61,.85) !important; border-radius: 16px !important;
  border: 2px solid #7b2ff7 !important; font-family: ui-monospace, monospace; }
.stButton > button { border-radius: 999px; font-weight: 800; border: 2px solid #7b2ff7; }
.stButton > button[kind="primary"] { background: linear-gradient(90deg, #ff4ecd, #7b2ff7);
  border: none; font-size: 1.1rem; box-shadow: 0 0 24px rgba(255,78,205,.55); }

.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 18px 0; }
.stat { border-radius: 18px; padding: 14px; text-align: center; background: rgba(255,255,255,.06);
  border: 1px solid rgba(255,255,255,.14); }
.stat .n { font-size: 2.2rem; font-weight: 900; } .stat .l { color: #cfc4f5; font-weight: 700; }

.card { border-radius: 22px; padding: 18px 20px; margin: 14px 0; background: rgba(26,11,61,.72);
  backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,.14); border-left: 8px solid var(--c);
  box-shadow: 0 0 30px color-mix(in srgb, var(--c) 25%, transparent); }
.url { font-family: ui-monospace, monospace; word-break: break-all; padding: 10px 12px;
  border-radius: 12px; background: rgba(0,0,0,.35); color: #e9e3ff; font-size: .9rem; }
.row { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin: 12px 0 6px; }
.badge { padding: 6px 16px; border-radius: 999px; font-weight: 900; color: #0b0420;
  background: var(--c); font-size: 1.05rem; }
.verdict { font-size: 1.35rem; font-weight: 900; color: #fff; }
.vsub { color: #cfc4f5; }
.meter { position: relative; height: 16px; border-radius: 999px; margin: 10px 0 4px;
  background: linear-gradient(90deg, #39ff14 0%, #ffb703 45%, #ff3864 80%); }
.meter .mask { position: absolute; top: 0; right: 0; bottom: 0; border-radius: 0 999px 999px 0;
  background: rgba(11,4,32,.8); }
.meter .dot { position: absolute; top: -5px; width: 26px; height: 26px; border-radius: 50%;
  background: #fff; border: 4px solid var(--c); transform: translateX(-50%);
  box-shadow: 0 0 14px var(--c); }
.meta { color: #b9aee0; font-size: .85rem; }
.meta code { color: #fff; background: rgba(255,255,255,.08); padding: 1px 6px; border-radius: 6px; }
.why { margin: 12px 0 0; padding: 0; list-style: none; }
.why li { padding: 8px 10px; border-radius: 12px; margin: 6px 0; background: rgba(255,255,255,.05); }
.why .pts { font-weight: 900; color: var(--c); margin: 0 6px; }
.why code { color: #ff9ae6; background: rgba(255,78,205,.12); padding: 1px 6px; border-radius: 6px; }
.err { color: #ffb3c4; font-weight: 700; margin-top: 8px; }
.tips { display: flex; flex-wrap: wrap; gap: 8px; margin: 2px 0 14px; }
.tip { padding: 6px 12px; border-radius: 999px; font-weight: 800; font-size: .85rem; color: #fff;
  background: rgba(255,255,255,.07); border: 1px solid rgba(255,78,205,.55); }
.tips-h { font-weight: 900; color: #ff9ae6; font-size: .8rem; letter-spacing: 1px; margin-top: 4px; }
.ai { margin-top: 12px; padding: 10px 12px; border-radius: 14px; background: rgba(0,229,255,.08);
  border: 1px dashed rgba(0,229,255,.6); color: #dff9ff; }
.ai .note { color: #ffd166; font-weight: 800; }
.disc { color: #9a8fb5; font-size: .8rem; margin-top: 12px; }
</style>
"""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def defang(r) -> str:
    """Safe-to-share form, e.g. hxxp://evil[.]com/path"""
    s = r.input.strip()
    s = s.replace("https://", "hxxps://", 1).replace("http://", "hxxp://", 1)
    if r.normalized_host:
        s = s.replace(r.normalized_host, r.normalized_host.replace(".", "[.]"), 1)
    return s


def hero():
    squad = "".join(
        f'<div class="girl"><img src="{image_uri(i)}" alt="{esc(c["name"])}"/>'
        f'<div class="bubble"><small>{esc(c["name"])} says</small>{esc(c["slogan"])}</div></div>'
        for i, c in enumerate(CHARACTERS))
    ticker = "".join(f"<b>{esc(t)}</b>" for t in TICKER * 2)
    st.html(CSS + f"""
<div class="ticker"><span>{ticker}</span></div>
<div class="hero">
  <h1><span class="grad">Is this link sus?</span> 👀</h1>
  <p class="sub">Paste it. <b>We'll tell you why.</b> Rule-based, explainable, 100% offline.</p>
</div>
<div class="squad">{squad}</div>
<div class="banner">🔒 <b>Preliminary heuristic assessment.</b> Runs offline; links are never opened, fetched or resolved.</div>
""")


def card(r, ai: bool = False) -> str:
    c = COLORS[r.level]
    title, sub = VERDICT[r.level]
    shown = r.input.strip()
    shown = (shown[:300] + "…") if len(shown) > 300 else (shown or "(empty)")
    out = [f'<div class="card" style="--c:{c}"><div class="url">{esc(shown)}</div>',
           f'<div class="row"><span class="badge">{ICONS[r.level]} {esc(r.level or "Invalid")}</span>'
           f'<span class="verdict">{esc(title)}</span>']
    if r.valid:
        pct = min(r.score * 10, 100)
        out.append(f'<span class="vsub">Score <b>{r.score}</b> · {esc(sub)}</span></div>')
        out.append(f'<div class="meter"><div class="mask" style="left:{pct}%"></div>'
                   f'<div class="dot" style="left:{max(pct, 2)}%"></div></div>')
        out.append(f'<div class="meta">Real destination: <code>{esc(r.normalized_host)}</code>'
                   f' &nbsp;·&nbsp; Safe to share: <code>{esc(defang(r)[:160])}</code></div>')
        out.append('<div style="margin-top:12px;font-weight:900">🧠 Why this rating</div><ul class="why">')
        for f in r.findings:
            out.append(f'<li>{SEV_ICON[f.severity]}<span class="pts">+{f.points}</span>'
                       f'<code>{esc(f.rule_id)}</code> {esc(f.message)}</li>')
        out.append("</ul>")
        p = edge_ai.predict(r.input) if ai else None
        if p is not None:
            tag = "suspicious-looking" if p >= 0.7 else ("unsure" if p >= 0.4 else "normal-looking")
            note = ""
            if (p >= 0.7 and r.level == "Low") or (p < 0.3 and r.level == "High"):
                note = '<br><span class="note">⚖️ Models disagree; treat with caution.</span>'
            out.append(f'<div class="ai">🤖 <b>Edge AI second opinion:</b> {p:.2f} ({tag}) '
                       f'<span style="opacity:.7">· advisory only, does not change the rating</span>{note}</div>')
    else:
        out.append(f'</div><div class="err">⛔ {esc(r.error)}</div>')
    out.append(f'<div class="disc">⚠️ {esc(C.DISCLAIMER)}</div></div>')
    return "".join(out)


def report_csv(results) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["url", "rating", "score", "real_host", "reasons", "disclaimer"])
    for r in results:
        reasons = r.error if not r.valid else "; ".join(
            f"{f.rule_id} (+{f.points}): {f.message}" for f in r.findings)
        w.writerow([r.input.strip(), r.level or "Invalid", r.score, r.normalized_host or "", reasons, C.DISCLAIMER])
    return buf.getvalue()


TIPS = ["🔒 HTTPS ≠ safe", "👀 Check the real domain", "🚫 Never share OTP or passwords",
        "⏰ “Urgent!” = red flag", "🎁 Free prize? It's bait", "📞 Verify with the sender"]
HISTORY_FILE = Path(__file__).parent / "history.json"


def load_history() -> list:
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def add_history(results, source: str):
    hist = st.session_state.history
    now = datetime.now().strftime("%d %b, %H:%M")
    for r in results:
        hist.insert(0, {"time": now, "url": r.input.strip()[:300], "level": r.level or "Invalid",
                        "score": r.score, "source": source})
    del hist[200:]
    try:
        HISTORY_FILE.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass  # history is a convenience; never break the check


def share_text(results) -> str:
    lines = []
    for r in results:
        if not r.valid:
            lines.append(f"⚪ Invalid input: {r.error}")
            continue
        title, _ = VERDICT[r.level]
        lines.append(f"🔗 Link: {defang(r)[:200]}")
        lines.append(f"{ICONS[r.level]} Rating: {r.level} (score {r.score}) · {title}")
        reasons = [f for f in r.findings if f.points > 0]
        if reasons:
            lines.append("Why:")
            lines += [f"  • +{f.points} {f.message}" for f in reasons]
        else:
            lines.append("Why: no warning signs triggered.")
        lines.append("")
    lines.append(f"⚠️ {C.DISCLAIMER}")
    lines.append("Checked offline with Fake Link Detector (Team 4, Syntax Soldiers). Link was never opened.")
    return "\n".join(lines)


def run_check(text: str, source: str):
    results = analyze_many(text)
    if results:
        add_history(results, source)
    st.session_state.last = results


def set_urls(text: str):
    st.session_state.urls = text


def do_check():
    if not st.session_state.urls.strip():
        st.session_state.last = None
        st.session_state.warn = True
    else:
        run_check(st.session_state.urls, "paste")


def recheck(url: str):
    st.session_state.urls = url
    run_check(url, "history")


def clear_history():
    st.session_state.history = []
    try:
        HISTORY_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def render_history():
    hist = st.session_state.history
    st.header(f"🕘 History ({len(hist)})")
    if not hist:
        st.caption("No links checked yet.")
        return
    q = st.text_input("Search history", placeholder="🔎 filter…", label_visibility="collapsed")
    shown = [h for h in hist if q.lower() in h["url"].lower()] if q else hist
    for i, h in enumerate(shown[:25]):
        icon = ICONS.get(h["level"] if h["level"] != "Invalid" else None, "⚪")
        label = h["url"] if len(h["url"]) <= 28 else h["url"][:26] + "…"
        st.button(f"{icon} {label}", key=f"h{i}", on_click=recheck, args=(h["url"],),
                  help=f'{h["time"]} · {h["level"]} · score {h["score"]} · via {h["source"]}',
                  use_container_width=True)
    st.caption("Tap an item to re-check it. Saved in history.json on this device.")
    st.button("🗑️ Clear history", on_click=clear_history, use_container_width=True)


def show_results(results, ai: bool):
    counts = {k: sum(1 for r in results if r.level == k) for k in ("Low", "Medium", "High", None)}
    stats = "".join(
        f'<div class="stat"><div class="n" style="color:{COLORS[k]}">{counts[k]}</div>'
        f'<div class="l">{ICONS[k]} {k or "Invalid"}</div></div>' for k in counts)
    st.html(f'<div class="stats">{stats}</div>' + "".join(card(r, ai) for r in results))
    st.markdown("### 📤 Share report")
    st.caption("Tap the copy icon ⧉ (top-right of the box) and paste it in WhatsApp / Instagram to warn your friends.")
    report = share_text(results)
    st.code(report, language=None, wrap_lines=True)
    d1, d2 = st.columns(2)
    d1.download_button("⬇️ Download report (.txt)", report, file_name="link_report.txt",
                       mime="text/plain", use_container_width=True)
    d2.download_button("⬇️ Download report (.csv)", report_csv(results), file_name="link_report.csv",
                       mime="text/csv", use_container_width=True)


# ---------------- page ----------------
for k, v in (("urls", ""), ("last", None), ("qr_seen", None)):
    st.session_state.setdefault(k, v)
if "history" not in st.session_state:
    st.session_state.history = load_history()

hero()

with st.sidebar:
    st.header("📊 Rating scale")
    st.markdown(f"🟢 **Low**: score 0–{C.MEDIUM_MIN - 1}\n\n🟠 **Medium**: {C.MEDIUM_MIN}–{C.HIGH_MIN - 1}\n\n🔴 **High**: {C.HIGH_MIN}+")
    with st.expander("All rules and points"):
        st.table({"Rule": list(C.POINTS), "Points": list(C.POINTS.values())})

    st.divider()
    st.header("🤖 Edge AI")
    ai_ok = edge_ai.available()
    use_ai = st.toggle("Edge AI second opinion (experimental)", value=False, disabled=not ai_ok)
    if ai_ok:
        m = edge_ai.meta()
        st.caption(f"Tiny on-device model, advisory only; never changes the rule rating. "
                   f"Held-out precision {m.get('precision', '?')}, recall {m.get('recall', '?')}.")
    else:
        st.caption("model.json not found: running on rules only.")

    st.divider()
    hist_box = st.container()
    st.divider()
    st.caption("Rules: no machine learning · no paid APIs · no network calls.")

tab_paste, tab_upload, tab_scan = st.tabs(["⌨️ Paste link", "🖼️ Upload QR", "📷 Scan QR"])

with tab_paste:
    c1, c2, c3 = st.columns(3)
    c1.button("✅ Safe example", on_click=set_urls, args=(SAFE_EXAMPLE,), use_container_width=True)
    c2.button("🚩 Risky example", on_click=set_urls, args=(RISKY_EXAMPLE,), use_container_width=True)
    c3.button("📋 Batch example", on_click=set_urls, args=(BATCH_EXAMPLE,), use_container_width=True)
    st.text_area("Drop your link(s) here, one per line 👇", key="urls", height=130,
                 placeholder="https://www.example.com/about")
    st.html('<div class="tips-h">⚡ QUICK SAFETY TIPS</div><div class="tips">'
            + "".join(f'<span class="tip">{esc(t)}</span>' for t in TIPS) + "</div>")
    st.button("🔍 Check if it's sus", type="primary", on_click=do_check, use_container_width=True)
    if st.session_state.pop("warn", False):
        st.warning("Paste at least one link first, bestie 🙏 (or tap an example button).")


def handle_qr(file, source: str):
    if file is None:
        return
    data = file.getvalue()
    sig = (source, len(data), hash(data[:4096]))
    if st.session_state.qr_seen == sig:
        return  # already decoded this image
    st.session_state.qr_seen = sig
    texts, err = qr.decode(data)
    if err:
        st.session_state.last = None
        st.error(f"📷 {err}")
        return
    st.success(f"✅ Decoded {len(texts)} QR code(s). Checking the link(s) below; nothing was opened.")
    st.code("\n".join(t[:300] for t in texts), language=None, wrap_lines=True)
    run_check("\n".join(t.strip() for t in texts), source)


with tab_upload:
    st.caption("Upload a screenshot or photo of a QR code. It is decoded on your device; the link is never opened.")
    handle_qr(st.file_uploader("Upload QR image", type=["png", "jpg", "jpeg", "webp", "bmp"],
                               label_visibility="collapsed"), "QR upload")

with tab_scan:
    st.caption("Point your camera at a QR code and take a photo. Allow camera access if the browser asks.")
    if st.toggle("Turn on camera", value=False):
        handle_qr(st.camera_input("Scan QR", label_visibility="collapsed"), "QR scan")

if st.session_state.last:
    show_results(st.session_state.last, use_ai)

with hist_box:
    render_history()
