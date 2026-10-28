# 🔗 Fake Link Detector — Team 4, Syntax Soldiers

A lightweight, **fully offline**, **rule-based** URL risk checker. Paste one or more links and get a
**Low / Medium / High** rating plus the **exact rules that fired and why**.

> **Preliminary heuristic assessment.** A High rating is not proof of danger, and Low is not a guarantee of safety.

- No machine learning, no paid APIs, **no network calls**: the URL is only parsed as a string, never opened, fetched or DNS-resolved.
- Python standard library only for the core (`urllib`-free custom parser, `ipaddress`, `re`, `dataclasses`).

## How to run

```bash
pip install -r requirements.txt
streamlit run app.py          # web UI
python cli.py "http://www.paypal.com@evil.com"   # command line
python -m pytest -q           # tests
```

## Files

| File | Purpose |
|---|---|
| `detector.py` | Core engine: `analyze(url)` and `analyze_many(text)`. Pure functions, never raises. |
| `config.py` | All keywords, brands, TLDs, thresholds and points (single place to tune). |
| `app.py` | Streamlit UI: badge, risk meter, "Why this rating", batch summary. |
| `cli.py` | Command-line checker for demo/debugging. |
| `tests/test_detector.py` | Acceptance tests, edge cases, false-positive guard, no-network test. |

## Requirements coverage

| Item | Where |
|---|---|
| M1 Accept a URL | Text box in `app.py`, `cli.py` |
| M2 HTTPS check | `NO_HTTPS` rule |
| M3 Long URLs | `LONG_URL` (>75), `VERY_LONG_URL` (>100) |
| M4 Suspicious characters/patterns | `AT_SYMBOL`, hyphens, keywords, punycode, port, encoded chars, … |
| M5 Rating + reasons | Every result lists its findings with points |
| M6 Empty / malformed | Friendly error, never crashes (see tests) |
| B1 IP links | `IP_HOST` (dotted, decimal, hex, octal, IPv6) |
| B2 Brand only in subdomain | `BRAND_IN_SUBDOMAIN` |
| B3 Warning-signs list | "Why this rating" list with severity icons |
| B4 Colour-coded meter | Green/amber/red badge and meter (score/10) |
| B5 Several links at once | One URL per line + Low/Medium/High/Invalid summary |

## Rules and scoring

| ID | Condition | Points |
|---|---|---|
| `NO_HTTPS` | scheme is `http` | +2 |
| `NO_SCHEME` | no scheme given (http assumed) | note |
| `LONG_URL` | length > 75 | +1 |
| `VERY_LONG_URL` | length > 100 (replaces LONG_URL) | +2 |
| `AT_SYMBOL` | `@` in the authority (userinfo trick) | +3 |
| `MANY_HYPHENS` / `SOME_HYPHENS` | ≥3 / exactly 2 hyphens in hostname | +2 / +1 |
| `SUSPICIOUS_WORDS` | 1 / 2+ keywords (login, verify, secure, …) | +1 / +2 |
| `IP_HOST` | host is an IPv4 (any form) or IPv6 address | +3 |
| `BRAND_IN_SUBDOMAIN` | brand in subdomain but not registered domain | +3 |
| `PUNYCODE` | a label starts with `xn--` (incl. Unicode hosts after IDNA) | +2 |
| `ODD_PORT` | explicit port other than 80/443 | +1 |
| `MANY_SUBDOMAINS` | ≥4 dots in host | +1 |
| `RISKY_TLD` | .zip .xyz .top .tk .click .gq .ml .cf .work .support | +1 |
| `URL_SHORTENER` | bit.ly, tinyurl.com, t.co, … (destination hidden) | +1 |
| `ENCODED_CHARS` | ≥3 `%XX` in host/path | +1 |
| `MANY_DIGITS_HOST` | ≥5 digits in hostname | +1 |

**Rating:** 0–2 **Low**, 3–5 **Medium**, 6+ **High**.

Demo checks: `https://www.example.com/about` → **Low (0)**;
`http://secure-login-verify-account.example-bank.com/signin/confirm?session=…&redirect=update-billing-info-now` → **High (8)**.

## Limitations (honest)

- Heuristics cannot see page content, domain age or reputation; there is no live threat-intel data.
- Attackers can craft URLs that avoid every rule; some legitimate sites have long URLs or hyphens.
- Registered-domain logic is a deliberate no-dependency simplification (last 2 labels, or 3 for
  `co.uk`, `com.au`, `co.in`, `org.uk`, `co.jp`, `com.br`) rather than the full Public Suffix List.
- Keyword lists are English-only; thresholds are hand-tuned, not statistically validated.

That is why every rating is advisory and always shows its reasoning.

## UI and extra features

- Gen Z neon theme with 4 hero characters and slogans ("Is this link sus? We'll tell you why", "Trust, but verify", ...).
  The characters are built-in SVG illustrations (work offline). To use real photos, drop `girl1.jpg` … `girl4.jpg` into `assets/`.
- Verdict line per rating: "Looks clean ✨" / "Kinda sus 🤨" / "Major red flag 🚩".
- Real destination host and a **defanged, safe-to-share** version of the link (`hxxp://evil[.]com`).
- **Download report (CSV)** for batch checks.
- `.streamlit/config.toml` sets the dark theme and turns off Streamlit usage statistics (fully offline).

## New features (v3)

- **Quick safety tips** always shown under the input box.
- **History** (sidebar): every checked link with its rating, searchable, tap to re-check, clear button.
  Saved locally in `history.json` on this device (never uploaded).
- **Share report**: copy-ready "rating + reasons" text with a defanged link (copy icon), plus .txt/.csv download.
- **QR-code link check**: upload a QR image or scan with the camera; decoded on-device with `zxing-cpp`, then checked.
  The decoded link is shown as plain text and never opened. Demo image: `assets/sample_qr_risky.png`.
- **Edge AI second opinion** (sidebar toggle, OFF by default): `edge_ai.py` + `model.json` (97 KB).
  Logistic regression on hashed character 3-grams + 7 numeric features, pure Python, ~0.02 ms per link.
  Trained offline with `train_edge_model.py` on 64,000 URLs from a free public dataset
  (faizann24/Using-machine-learning-to-detect-malicious-URLs, balanced good/bad);
  held-out test on 16,000 URLs: **precision 0.955, recall 0.921, accuracy 0.939**.
  It is advisory only, never changes the rule score or rating, and shows "Models disagree; treat with caution"
  when it conflicts with the rules. It is a small model with limits (dataset bias, no page content).
  Delete `model.json` and the app runs on rules only.
