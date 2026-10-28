"""CLI: python cli.py "<url>" ["<url>" ...]"""
import sys

from config import DISCLAIMER
from detector import analyze


def main(argv):
    if not argv:
        print('Usage: python cli.py "<url>" [more urls]')
        return 1
    for url in argv:
        r = analyze(url)
        print(f"\n{url}")
        if not r.valid:
            print(f"  INVALID: {r.error}")
            continue
        print(f"  Rating: {r.level}  (score {r.score}, host {r.normalized_host})")
        for f in r.findings:
            print(f"   +{f.points:<2} {f.rule_id:<20} {f.message}")
    print(f"\n{DISCLAIMER}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
