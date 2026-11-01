#!/usr/bin/env python3
"""
Regent Intel -- reports index builder

Builds reports.json from the reports/ folder. Netlify runs this on every deploy
(see netlify.toml), so the only publishing step is: put the report HTML in reports/.

Works with every report format used so far:
  - web-series files that carry an <h1> title
  - print-layout files that carry only a <title> and a "Produced:" line
  - hyphen or underscore filenames (SIGACT-HF-023.html, SIGACT_HF_055_102526.html)

Never fails on a single bad file. Fails the deploy only if it finds no reports at all,
so a broken index can never replace a working one.
"""
import os
import re
import json
import sys
from datetime import datetime

REPORTS_DIR = sys.argv[1] if len(sys.argv) > 1 else "reports"
OUT_PATH = sys.argv[2] if len(sys.argv) > 2 else "reports.json"

MONTHS = ("January|February|March|April|May|June|July|August|"
          "September|October|November|December")
LONG_DATE = r"(?:%s) \d{1,2}, \d{4}" % MONTHS


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()


def long_date_to_iso(s):
    try:
        return datetime.strptime(s, "%B %d, %Y").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def find_title(html, filename):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    if m and strip_tags(m.group(1)):
        return strip_tags(m.group(1))
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    if m and strip_tags(m.group(1)):
        return strip_tags(m.group(1)).split("|")[0].strip()
    return filename.rsplit(".", 1)[0]


def find_report_id(title, filename):
    m = re.search(r"(SITREP[-_ ]?EF[-_ ]?\d+|SIGACT[-_ ]?HF[-_ ]?\d+)", title + " " + filename, re.I)
    if not m:
        return filename.rsplit(".", 1)[0]
    raw = m.group(1).upper()
    series = "SITREP-EF" if "EF" in raw else "SIGACT-HF"
    num = re.search(r"(\d+)$", raw).group(1)
    return "%s-%s" % (series, num)


def find_date(html, filename):
    # 1. "Produced: October 25, 2026"
    m = re.search(r"Produced:\s*(%s)" % LONG_DATE, html)
    if m:
        d = long_date_to_iso(m.group(1))
        if d:
            return d
    # 2. the date on the report header line next to a DTG, e.g. "October 5, 2026 | 051830Z OCT 2026"
    m = re.search(r"(%s)\s*(?:<[^>]+>\s*)*\|\s*\d{6}Z" % LONG_DATE, html)
    if m:
        d = long_date_to_iso(m.group(1))
        if d:
            return d
    # 3. MMDDYY in the filename, e.g. _102526
    m = re.search(r"[-_](\d{2})(\d{2})(\d{2})(?:\D|$)", filename)
    if m:
        mm, dd, yy = m.groups()
        try:
            return datetime(2000 + int(yy), int(mm), int(dd)).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # 4. YYYYMMDD in the filename, e.g. -20261025
    m = re.search(r"[-_](20\d{2})(\d{2})(\d{2})(?:\D|$)", filename)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # 5. first long date anywhere in the file
    m = re.search(LONG_DATE, html)
    if m:
        return long_date_to_iso(m.group(0))
    return ""


def find_bluf(html):
    m = re.search(r"(?:BOTTOM LINE UP FRONT|BLUF)\s*(?:</[^>]+>\s*)*(?:<p[^>]*>)?(.*?)(?:</p>|</div>|</section>)",
                  html, re.S | re.I)
    if m:
        text = strip_tags(m.group(1))
        if text:
            return text[:300]
    return "Assessment available in full report."


def build_entry(filename):
    path = os.path.join(REPORTS_DIR, filename)
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        html = fh.read()
    title = find_title(html, filename)
    report_id = find_report_id(title, filename)
    if report_id.startswith("SITREP-EF") or "Epic Fury" in title:
        series = "EF"
    elif report_id.startswith("SIGACT-HF") or "Homeland Focus" in title:
        series = "HF"
    else:
        series = "OTHER"
    num_match = re.search(r"(\d+)$", report_id)
    return {
        "id": report_id,
        "title": title,
        "series": series,
        "date": find_date(html, filename),
        "bluf": find_bluf(html),
        "filename": filename,
        "classification": "UNCLASSIFIED",
        "_num": int(num_match.group(1)) if num_match else 0,
    }


def main():
    if not os.path.isdir(REPORTS_DIR):
        print("ERROR: reports folder not found: %s" % REPORTS_DIR)
        return 1

    entries = []
    skipped = []
    for name in sorted(os.listdir(REPORTS_DIR)):
        if name.startswith(".") or not name.lower().endswith(".html"):
            continue
        try:
            entries.append(build_entry(name))
        except Exception as exc:  # one bad file must never break the index
            skipped.append("%s (%s)" % (name, exc))

    if not entries:
        print("ERROR: no report HTML files found in %s; refusing to write an empty index." % REPORTS_DIR)
        return 1

    # newest first: by date, then report number
    entries.sort(key=lambda e: (e["date"], e["_num"]), reverse=True)
    for e in entries:
        del e["_num"]

    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2)

    latest = {}
    for e in entries:
        latest.setdefault(e["series"], e)
    print("Wrote %d entries to %s" % (len(entries), OUT_PATH))
    for series in ("EF", "HF"):
        if series in latest:
            print("  latest %s: %s (%s) -> %s" % (series, latest[series]["id"], latest[series]["date"], latest[series]["filename"]))
    for s in skipped:
        print("  skipped: %s" % s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
