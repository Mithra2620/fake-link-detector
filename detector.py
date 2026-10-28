"""Core rule engine. Pure functions: no I/O, no network, no UI.

The URL is only parsed as a string. It is never opened, fetched or resolved.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field

import config as C


@dataclass
class Finding:
    rule_id: str
    message: str
    points: int
    severity: str  # "info" | "warn" | "danger"


@dataclass
class Result:
    input: str
    valid: bool
    error: str | None
    score: int
    level: str | None
    findings: list[Finding] = field(default_factory=list)
    normalized_host: str | None = None
    disclaimer: str = C.DISCLAIMER


_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):(?!\d)")
_ENCODED_RE = re.compile(r"%[0-9a-fA-F]{2}")
_LABEL_RE = re.compile(r"^[a-z0-9_](?:[a-z0-9_\-]*[a-z0-9_])?$")
_NUMERIC_PART_RE = re.compile(r"^(0x[0-9a-f]*|\d+)$")


class _Invalid(Exception):
    pass


def _invalid(raw: str, msg: str) -> Result:
    return Result(input=raw, valid=False, error=msg, score=0, level=None)


def _severity(points: int) -> str:
    if points >= 3:
        return "danger"
    if points >= 1:
        return "warn"
    return "info"


def _level(score: int) -> str:
    if score >= C.HIGH_MIN:
        return "High"
    if score >= C.MEDIUM_MIN:
        return "Medium"
    return "Low"


def _parse_ipv4_loose(host: str) -> ipaddress.IPv4Address | None:
    """inet_aton-style parsing: dotted, decimal (2130706433), hex (0x7f), octal (0177)."""
    parts = host.split(".")
    if not 1 <= len(parts) <= 4 or not all(_NUMERIC_PART_RE.match(p) for p in parts):
        return None
    nums = []
    for p in parts:
        if p.startswith("0x"):
            if len(p) == 2:
                return None
            nums.append(int(p, 16))
        elif len(p) > 1 and p.startswith("0"):
            if not all(c in "01234567" for c in p):
                return None
            nums.append(int(p, 8))
        else:
            nums.append(int(p))
    # Last part fills the remaining bytes
    head, last = nums[:-1], nums[-1]
    if any(n > 255 for n in head) or last >= 256 ** (4 - len(head)):
        return None
    value = 0
    for n in head:
        value = value * 256 + n
    value = value * 256 ** (4 - len(head)) + last
    return ipaddress.IPv4Address(value)


def registered_domain(host: str) -> str:
    labels = host.split(".")
    n = 3 if ".".join(labels[-2:]) in C.TWO_PART_SUFFIXES else 2
    return ".".join(labels[-n:])


def _parse(raw: str):
    """Return dict of parsed parts, or raise _Invalid with a friendly message."""
    s = raw.strip().strip(",;").strip().strip("\"'<>").strip()
    if not s:
        raise _Invalid("Empty input: please paste a URL.")
    if any(c.isspace() for c in s):
        raise _Invalid("Not a valid URL: it contains spaces.")

    no_scheme = False
    if "://" in s:
        scheme, rest = s.split("://", 1)
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*$", scheme):
            raise _Invalid("Malformed URL: invalid scheme.")
    else:
        m = _SCHEME_RE.match(s)
        if m:
            raise _Invalid(f"Unsupported scheme '{m.group(1).lower()}:' (only http and https are checked).")
        scheme, rest, no_scheme = "http", s, True
    scheme = scheme.lower()
    if scheme not in ("http", "https"):
        raise _Invalid(f"Unsupported scheme '{scheme}://' (only http and https are checked).")

    # Authority ends at the first / ? or #
    m = re.search(r"[/?#\\]", rest)
    authority, tail = (rest[: m.start()], rest[m.start():]) if m else (rest, "")
    userinfo, at, hostport = authority.rpartition("@")
    has_at = bool(at)

    port = None
    if hostport.startswith("["):
        end = hostport.find("]")
        if end == -1:
            raise _Invalid("Malformed URL: unclosed '[' in IPv6 address.")
        host, after = hostport[1:end], hostport[end + 1:]
        if after:
            if not after.startswith(":"):
                raise _Invalid("Malformed URL: unexpected text after IPv6 address.")
            port = after[1:]
        try:
            ip = ipaddress.IPv6Address(host)
        except ValueError:
            raise _Invalid("Malformed URL: invalid IPv6 address.")
        host_kind, host = "ip", str(ip)
    else:
        if hostport.count(":") > 1:
            raise _Invalid("Malformed URL: too many ':' in host.")
        host, _, port = hostport.partition(":")
        port = port if _ else None
        host = host.lower().rstrip(".")
        if not host:
            raise _Invalid("Malformed URL: no hostname found.")
        ip4 = _parse_ipv4_loose(host)
        if ip4 is not None:
            host_kind, host = "ip", str(ip4)
        elif all(_NUMERIC_PART_RE.match(p) for p in host.split(".")):
            raise _Invalid("Malformed URL: invalid IP address.")
        else:
            host_kind = "domain"
            try:
                ascii_host = host.encode("idna").decode("ascii")
            except (UnicodeError, ValueError):
                raise _Invalid("Malformed URL: hostname contains invalid characters.")
            host = ascii_host.lower()
            labels = host.split(".")
            if len(labels) < 2:
                raise _Invalid(f"Not a valid domain: '{host}' has no dot (e.g. example.com).")
            if len(host) > 253 or not all(_LABEL_RE.match(l) and len(l) <= 63 for l in labels):
                raise _Invalid("Malformed URL: hostname contains invalid characters.")
            if not (labels[-1].isalpha() or labels[-1].startswith("xn--")):
                raise _Invalid(f"Not a valid domain: '.{labels[-1]}' is not a valid top-level domain.")

    if port is not None:
        if not port.isdigit() or not 0 < int(port) <= 65535:
            raise _Invalid("Malformed URL: invalid port number.")
        port = int(port)

    path, _, query = tail.partition("?")
    query = query.split("#", 1)[0]
    path = path.split("#", 1)[0]
    return dict(
        stripped=s, scheme=scheme, no_scheme=no_scheme, has_at=has_at, userinfo=userinfo,
        host=host, host_kind=host_kind, port=port, path=path, query=query,
    )


def _rules(p: dict) -> list[Finding]:
    P = C.POINTS
    out: list[Finding] = []

    def add(rule_id, message, points):
        out.append(Finding(rule_id, message, points, _severity(points)))

    host, is_ip = p["host"], p["host_kind"] == "ip"
    url = p["stripped"]

    # M2: HTTPS
    if p["no_scheme"]:
        add("NO_SCHEME", "No scheme given (http/https); assuming http://.", P["NO_SCHEME"])
    if p["scheme"] == "http":
        add("NO_HTTPS", "Uses http, not https: the connection is not encrypted.", P["NO_HTTPS"])
    else:
        add("HTTPS_OK", "Uses https (encrypted connection). Note: phishing sites can use https too.", 0)

    # M3: length
    n = len(url)
    if n > C.VERY_LONG_URL_LEN:
        add("VERY_LONG_URL", f"Very long URL ({n} characters > {C.VERY_LONG_URL_LEN}); long links can hide the real destination.", P["VERY_LONG_URL"])
    elif n > C.LONG_URL_LEN:
        add("LONG_URL", f"Long URL ({n} characters > {C.LONG_URL_LEN}).", P["LONG_URL"])

    # M4: suspicious characters / patterns
    if p["has_at"]:
        add("AT_SYMBOL", f"Contains '@' before the host: browsers ignore '{p['userinfo'][:40]}' and go to '{host}'.", P["AT_SYMBOL"])

    if not is_ip:
        hy = host.count("-") - 2 * host.count("xn--")
        if hy >= C.MANY_HYPHENS_MIN:
            add("MANY_HYPHENS", f"Hostname has {hy} hyphens (common in fake look-alike domains).", P["MANY_HYPHENS"])
        elif hy == C.SOME_HYPHENS_COUNT:
            add("SOME_HYPHENS", f"Hostname has {hy} hyphens.", P["SOME_HYPHENS"])

    haystack = (host + p["path"] + "?" + p["query"]).lower()
    words = [w for w in C.SUSPICIOUS_KEYWORDS if w in haystack]
    if len(words) >= 2:
        add("SUSPICIOUS_WORDS", f"Suspicious words found: {', '.join(words)}.", P["SUSPICIOUS_WORDS_MANY"])
    elif words:
        add("SUSPICIOUS_WORDS", f"Suspicious word found: {words[0]}.", P["SUSPICIOUS_WORDS_ONE"])

    # B1: IP host
    if is_ip:
        add("IP_HOST", f"Host is a raw IP address ({host}) instead of a domain name.", P["IP_HOST"])
    else:
        labels = host.split(".")
        reg = registered_domain(host)
        sub_labels = labels[: len(labels) - len(reg.split("."))]

        # B2: brand only in subdomain
        sub_tokens = set(re.split(r"[.\-_]", ".".join(sub_labels))) if sub_labels else set()
        sub_text = ".".join(sub_labels)
        brands = [b for b in C.BRANDS
                  if (b in sub_tokens or (len(b) >= 5 and b in sub_text)) and b not in reg]
        if brands:
            add("BRAND_IN_SUBDOMAIN", f"Brand name '{brands[0]}' appears only in the subdomain; the real site is '{reg}'.", P["BRAND_IN_SUBDOMAIN"])

        if any(l.startswith("xn--") for l in labels):
            add("PUNYCODE", "Hostname uses punycode (xn--): may contain look-alike Unicode letters.", P["PUNYCODE"])
        if host.count(".") >= C.MANY_DOTS_MIN:
            add("MANY_SUBDOMAINS", f"Many subdomain levels ({host.count('.')} dots in host).", P["MANY_SUBDOMAINS"])
        if labels[-1] in C.RISKY_TLDS:
            add("RISKY_TLD", f"Top-level domain '.{labels[-1]}' is frequently abused.", P["RISKY_TLD"])
        if host.removeprefix("www.") in C.URL_SHORTENERS:
            add("URL_SHORTENER", "Link shortener: the real destination is hidden.", P["URL_SHORTENER"])
        digits = sum(c.isdigit() for c in host)
        if digits >= C.DIGITS_HOST_MIN:
            add("MANY_DIGITS_HOST", f"Hostname contains {digits} digits.", P["MANY_DIGITS_HOST"])

    if p["port"] is not None and p["port"] not in C.STANDARD_PORTS:
        add("ODD_PORT", f"Uses non-standard port {p['port']}.", P["ODD_PORT"])

    enc = len(_ENCODED_RE.findall(host + p["path"]))
    if enc >= C.ENCODED_MIN:
        add("ENCODED_CHARS", f"{enc} percent-encoded characters (%XX) can disguise the URL.", P["ENCODED_CHARS"])

    return out


def analyze(raw) -> Result:
    """Analyse one URL. Never raises."""
    raw_str = "" if raw is None else str(raw)
    try:
        p = _parse(raw_str)
        findings = _rules(p)
        score = sum(f.points for f in findings)
        if score == 0:
            findings.append(Finding("NO_WARNINGS", "No warning signs triggered.", 0, "info"))
        findings.sort(key=lambda f: f.points, reverse=True)
        return Result(input=raw_str, valid=True, error=None, score=score,
                      level=_level(score), findings=findings, normalized_host=p["host"])
    except _Invalid as e:
        return _invalid(raw_str, str(e))
    except Exception as e:  # defensive: analyze() must never raise
        return _invalid(raw_str, f"Could not analyse this input ({type(e).__name__}).")


def analyze_many(text) -> list[Result]:
    """One URL per line; blank lines ignored."""
    if not text:
        return []
    return [analyze(line) for line in str(text).splitlines() if line.strip()]
