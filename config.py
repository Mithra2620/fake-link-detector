"""All tunable lists and point values live here (single place to tune)."""

DISCLAIMER = (
    "Preliminary heuristic assessment. A High rating is not proof of danger, "
    "and Low is not a guarantee of safety."
)

# Rule points
POINTS = {
    "NO_HTTPS": 2,
    "NO_SCHEME": 0,
    "LONG_URL": 1,
    "VERY_LONG_URL": 2,
    "AT_SYMBOL": 3,
    "MANY_HYPHENS": 2,
    "SOME_HYPHENS": 1,
    "SUSPICIOUS_WORDS_ONE": 1,
    "SUSPICIOUS_WORDS_MANY": 2,
    "IP_HOST": 3,
    "BRAND_IN_SUBDOMAIN": 3,
    "PUNYCODE": 2,
    "ODD_PORT": 1,
    "MANY_SUBDOMAINS": 1,
    "RISKY_TLD": 1,
    "URL_SHORTENER": 1,
    "ENCODED_CHARS": 1,
    "MANY_DIGITS_HOST": 1,
}

# Thresholds
LONG_URL_LEN = 75
VERY_LONG_URL_LEN = 100
MANY_HYPHENS_MIN = 3
SOME_HYPHENS_COUNT = 2
MANY_DOTS_MIN = 4
ENCODED_MIN = 3
DIGITS_HOST_MIN = 5

# Rating: score 0-2 Low, 3-5 Medium, 6+ High
MEDIUM_MIN = 3
HIGH_MIN = 6

SUSPICIOUS_KEYWORDS = [
    "login", "signin", "verify", "secure", "account", "update", "confirm",
    "password", "banking", "wallet", "suspend", "unlock", "billing", "free",
    "bonus", "prize",
]

BRANDS = [
    "paypal", "google", "apple", "microsoft", "amazon", "facebook", "instagram",
    "netflix", "whatsapp", "sbi", "hdfc", "icici", "paytm", "chase", "dropbox",
    "linkedin",
]

RISKY_TLDS = {"zip", "xyz", "top", "tk", "click", "gq", "ml", "cf", "work", "support"}

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "ow.ly", "buff.ly",
    "rebrand.ly", "cutt.ly", "shorturl.at", "tiny.cc", "rb.gy", "t.ly", "s.id",
}

# Two-part public suffixes (deliberate no-dependency simplification of the PSL)
TWO_PART_SUFFIXES = {"co.uk", "com.au", "co.in", "org.uk", "co.jp", "com.br"}

STANDARD_PORTS = {80, 443}
