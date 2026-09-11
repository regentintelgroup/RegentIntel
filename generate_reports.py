#!/usr/bin/env python3
"""
Regent Intelligence Group -- Automated Intelligence Production Pipeline
Generates daily SITREP-EF (Epic Fury) and SIGACT-HF (Homeland Focus) reports
Publishes to regentintel.org via GitHub + Netlify

Usage:
    python3 generate_reports.py           # Generate both reports
    python3 generate_reports.py --ef      # Epic Fury only
    python3 generate_reports.py --hf      # Homeland Focus only
    python3 generate_reports.py --dry-run # Generate but do not publish
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime, timezone
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Installing anthropic SDK...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic", "--quiet"])
    import anthropic


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

REPO_DIR = os.environ.get("REPO_DIR", os.path.expanduser("~/RegentIntel"))
REPORTS_DIR = os.path.join(REPO_DIR, "reports")
REPORTS_JSON = os.path.join(REPO_DIR, "reports.json")
MODEL = "claude-opus-4-0"  # Maximum analytical quality
DTG = datetime.now(timezone.utc).strftime("%d%H%MZ %b %Y").upper()
DATE_DISPLAY = datetime.now(timezone.utc).strftime("%B %d, %Y")
DATE_FILE = datetime.now(timezone.utc).strftime("%Y%m%d")
DATE_ISO = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# PROMPT TEMPLATES
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a Senior All-Source Intelligence Analyst operating at the GS-18 equivalent level, producing finished intelligence for Regent Intelligence Group (RIG).

STANDING RULES:
- No em dashes anywhere. Use commas, semicolons, colons, or separate sentences.
- American English exclusively. US spelling: -ize not -ise, defense not defence, center not centre.
- Date format: Month DD, YYYY (September 11, 2026). Never DD Month YYYY.
- Time format: Zulu (UTC) for DTGs, EST/EDT for domestic references.
- Minimize chatter. Every sentence carries analytical weight.
- BLUF is mandatory and appears first after the header block.
- Confidence levels stated for every major assessment: LOW / MODERATE / HIGH.
- Information gaps explicitly noted.
- Every factual claim must be sourced. Use web search to find real, current, verifiable information. Do not fabricate or assume.
- Analytical standards: ICD 203 (analytic standards), ICD 206 (sourcing).
- Voice: "we/the firm" -- never "I."
- Classification: UNCLASSIFIED // FOR PUBLIC RELEASE

BRANDING:
- Organization: Regent Intelligence Group
- Report attribution: Regent Intelligence Group, All-Source Analysis Division

SOURCE REQUIREMENTS:
- Search for real, current events and verified reporting
- Cite sources by outlet name and date
- Distinguish confirmed facts from unconfirmed claims
- Assess source reliability where relevant
- If information is thin on a topic, say so. Do not pad with filler."""

EF_PROMPT = """Produce SITREP-EF-{report_number} for today, {date_display}.
DTG: {dtg}

This is the Epic Fury theater series covering the Iran/U.S. strategic competition and broader Middle East/global security environment.

Search for the latest real developments in:
1. Iran nuclear program status and IAEA reporting
2. Iran proxy activity (Hezbollah, Houthis, Iraqi militias, Hamas)
3. U.S. force posture and deployments in CENTCOM AOR
4. Strait of Hormuz / maritime security
5. Iran cyber operations and influence campaigns
6. Israel-Iran dynamic
7. Gulf state security posture (UAE, Saudi, Bahrain)
8. Any active hostilities, strikes, or escalation indicators

Structure:
- HEADER BLOCK (Report number, DTG, period covered, classification)
- BLUF (3-5 sentences, key takeaways)
- CURRENT SITUATION (by threat stream, sourced)
- KEY DEVELOPMENTS (last 24-48 hours, sourced)
- INDICATORS AND WARNINGS (what to watch)
- ASSESSMENT (analytical judgment with confidence levels)
- INFORMATION GAPS (what we do not know)
- SOURCES (list all sources referenced)

Write the full report now. Every claim sourced via search."""

HF_PROMPT = """Produce SIGACT-HF-{report_number} for today, {date_display}.
DTG: {dtg}

This is the Homeland Focus series covering CONUS domestic security threats.

Search for the latest real developments in:
1. Domestic violent extremism (DVE) -- all ideologies
2. ISIS/AQ-inspired threats or disrupted plots on U.S. soil
3. Iranian state-sponsored activity targeting the U.S. homeland
4. Transnational criminal organization (TCO) nexus with terrorism
5. Critical infrastructure threats (cyber-physical convergence)
6. Aviation and transportation security
7. Active FBI/DHS threat advisories or NTAS bulletins
8. Mass casualty events or disrupted attacks (last 48 hours)

Structure:
- HEADER BLOCK (Report number, DTG, period covered, classification)
- BLUF (3-5 sentences, key takeaways)
- THREAT STREAMS (by category, sourced)
- KEY INCIDENTS (last 24-48 hours, sourced)
- WATCH LIST (active investigations, trial updates, known threats)
- ASSESSMENT (analytical judgment with confidence levels)
- INFORMATION GAPS (what we do not know)
- SOURCES (list all sources referenced)

Write the full report now. Every claim sourced via search."""


# ---------------------------------------------------------------------------
# REPORT HTML TEMPLATE
# ---------------------------------------------------------------------------

REPORT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | Regent Intelligence Group</title>
    <meta name="description" content="{bluf_short}">
    <meta property="og:title" content="{title} | Regent Intelligence Group">
    <meta property="og:description" content="{bluf_short}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="https://regentintel.org/reports/{filename}">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            background: #0a0e14;
            color: #c8cdd3;
            line-height: 1.7;
        }}
        .report-header {{
            background: #0D1B2A;
            border-bottom: 2px solid #146E87;
            padding: 40px 20px;
            text-align: center;
        }}
        .report-header .org {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 12px;
            letter-spacing: 2px;
            color: #146E87;
            text-transform: uppercase;
            margin-bottom: 16px;
        }}
        .report-header h1 {{
            font-size: 24px;
            color: #e8ecf0;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        .report-header .meta {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 13px;
            color: #7a8a9a;
        }}
        .report-header .classification {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 11px;
            letter-spacing: 1.5px;
            color: #4a9a6a;
            margin-top: 12px;
        }}
        .report-body {{
            max-width: 760px;
            margin: 0 auto;
            padding: 40px 20px 80px;
        }}
        .report-body h2 {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 14px;
            letter-spacing: 1.5px;
            color: #146E87;
            text-transform: uppercase;
            margin-top: 36px;
            margin-bottom: 12px;
            padding-bottom: 6px;
            border-bottom: 1px solid #1a2a3a;
        }}
        .report-body h3 {{
            font-size: 16px;
            color: #e0e4e8;
            margin-top: 24px;
            margin-bottom: 8px;
        }}
        .report-body p {{
            margin-bottom: 14px;
            font-size: 15px;
        }}
        .bluf {{
            background: #0D1B2A;
            border-left: 3px solid #146E87;
            padding: 20px 24px;
            margin: 24px 0;
            font-size: 15px;
            line-height: 1.8;
        }}
        .bluf-label {{
            font-family: Arial, Helvetica, sans-serif;
            font-size: 11px;
            letter-spacing: 1.5px;
            color: #146E87;
            margin-bottom: 8px;
        }}
        .report-footer {{
            max-width: 760px;
            margin: 0 auto;
            padding: 30px 20px;
            border-top: 1px solid #1a2a3a;
            text-align: center;
        }}
        .report-footer a {{
            color: #146E87;
            text-decoration: none;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 13px;
        }}
        .report-footer a:hover {{
            text-decoration: underline;
        }}
        .report-footer .back {{
            display: inline-block;
            margin-top: 16px;
            padding: 10px 24px;
            border: 1px solid #146E87;
            color: #146E87;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 13px;
            text-decoration: none;
        }}
        .report-footer .back:hover {{
            background: #146E87;
            color: #0D1B2A;
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <div class="org">Regent Intelligence Group</div>
        <h1>{title}</h1>
        <div class="meta">{date_display} | {dtg}</div>
        <div class="classification">UNCLASSIFIED // FOR PUBLIC RELEASE</div>
    </div>
    <div class="report-body">
        {content_html}
    </div>
    <div class="report-footer">
        <a href="https://regentintel.org/advisory" class="back">Return to Intelligence Feed</a>
        <br><br>
        <a href="https://regentintel.org">regentintel.org</a>
    </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# CORE FUNCTIONS
# ---------------------------------------------------------------------------

def get_next_report_number(series: str) -> str:
    """Determine the next report number from reports.json."""
    if os.path.exists(REPORTS_JSON):
        with open(REPORTS_JSON, "r") as f:
            reports = json.load(f)
        count = sum(1 for r in reports if r.get("series") == series)
    else:
        count = 0
    return str(count + 1).zfill(3)


def generate_report(series: str, dry_run: bool = False) -> dict:
    """Generate a single report via Claude API with web search."""
    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

    report_number = get_next_report_number(series)

    if series == "EF":
        prompt = EF_PROMPT.format(
            report_number=report_number,
            date_display=DATE_DISPLAY,
            dtg=DTG
        )
        title = f"SITREP-EF-{report_number}"
        full_title = f"SITREP-EF-{report_number}: Epic Fury Theater Assessment"
    else:
        prompt = HF_PROMPT.format(
            report_number=report_number,
            date_display=DATE_DISPLAY,
            dtg=DTG
        )
        title = f"SIGACT-HF-{report_number}"
        full_title = f"SIGACT-HF-{report_number}: Homeland Focus Assessment"

    filename = f"{title}-{DATE_FILE}.html"

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating {title}...")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Calling Claude API with web search...")

    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )

    # Extract text content from response (may include tool use blocks)
    report_text = ""
    for block in response.content:
        if block.type == "text":
            report_text += block.text

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Report generated. {len(report_text)} characters.")

    # Convert markdown-style content to HTML
    content_html = convert_to_html(report_text)

    # Extract BLUF for the index
    bluf_short = extract_bluf(report_text)

    # Build full HTML report
    report_html = REPORT_HTML_TEMPLATE.format(
        title=full_title,
        bluf_short=bluf_short[:200],
        filename=filename,
        date_display=DATE_DISPLAY,
        dtg=DTG,
        content_html=content_html
    )

    if not dry_run:
        # Save report file
        os.makedirs(REPORTS_DIR, exist_ok=True)
        report_path = os.path.join(REPORTS_DIR, filename)
        with open(report_path, "w") as f:
            f.write(report_html)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Saved to {report_path}")

        # Update reports.json
        update_index(title, full_title, series, bluf_short, filename)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Updated reports.json")
    else:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] DRY RUN -- not saving.")
        print("--- PREVIEW ---")
        print(report_text[:1000])
        print("--- END PREVIEW ---")

    return {
        "title": title,
        "full_title": full_title,
        "series": series,
        "filename": filename,
        "bluf": bluf_short
    }


def convert_to_html(text: str) -> str:
    """Convert report text to HTML. Handles markdown-style headers and paragraphs."""
    lines = text.strip().split("\n")
    html_parts = []
    in_bluf = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_bluf:
                html_parts.append("</div>")
                in_bluf = False
            continue

        # Detect BLUF section
        if stripped.upper().startswith("BLUF") or stripped.upper().startswith("BOTTOM LINE"):
            if ":" in stripped:
                label, content = stripped.split(":", 1)
                html_parts.append(f'<div class="bluf"><div class="bluf-label">{label.strip()}</div>')
                html_parts.append(f"<p>{content.strip()}</p>")
            else:
                html_parts.append(f'<div class="bluf"><div class="bluf-label">{stripped}</div>')
            in_bluf = True
            continue

        # Headers
        if stripped.startswith("### "):
            if in_bluf:
                html_parts.append("</div>")
                in_bluf = False
            html_parts.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("## "):
            if in_bluf:
                html_parts.append("</div>")
                in_bluf = False
            html_parts.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("# "):
            if in_bluf:
                html_parts.append("</div>")
                in_bluf = False
            html_parts.append(f"<h2>{stripped[2:]}</h2>")
        elif stripped.startswith("**") and stripped.endswith("**"):
            if in_bluf:
                html_parts.append("</div>")
                in_bluf = False
            html_parts.append(f"<h3>{stripped[2:-2]}</h3>")
        else:
            # Regular paragraph
            # Convert inline bold
            import re
            processed = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
            html_parts.append(f"<p>{processed}</p>")

    if in_bluf:
        html_parts.append("</div>")

    return "\n".join(html_parts)


def extract_bluf(text: str) -> str:
    """Pull the BLUF paragraph from the report text."""
    lines = text.split("\n")
    capture = False
    bluf_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("BLUF") or stripped.upper().startswith("BOTTOM LINE"):
            capture = True
            if ":" in stripped:
                bluf_lines.append(stripped.split(":", 1)[1].strip())
            continue
        if capture:
            if not stripped or stripped.startswith("#") or stripped.startswith("**"):
                break
            bluf_lines.append(stripped)

    return " ".join(bluf_lines).strip() if bluf_lines else "Assessment available in full report."


def update_index(title: str, full_title: str, series: str, bluf: str, filename: str):
    """Add new report entry to reports.json."""
    if os.path.exists(REPORTS_JSON):
        with open(REPORTS_JSON, "r") as f:
            reports = json.load(f)
    else:
        reports = []

    # Remove sample entry if present
    reports = [r for r in reports if "SAMPLE" not in r.get("id", "")]

    new_entry = {
        "id": title,
        "title": full_title,
        "series": series,
        "date": DATE_ISO,
        "bluf": bluf[:300],
        "filename": filename,
        "classification": "UNCLASSIFIED"
    }

    # Insert at beginning (newest first)
    reports.insert(0, new_entry)

    with open(REPORTS_JSON, "w") as f:
        json.dump(reports, f, indent=2)


def git_push():
    """Commit and push new reports to GitHub."""
    os.chdir(REPO_DIR)

    subprocess.run(["git", "add", "reports/", "reports.json"], check=True)

    commit_msg = f"Intelligence update {DATE_DISPLAY}"
    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Pushed to GitHub. Netlify will deploy.")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Regent Intel Report Generator")
    parser.add_argument("--ef", action="store_true", help="Generate EF report only")
    parser.add_argument("--hf", action="store_true", help="Generate HF report only")
    parser.add_argument("--dry-run", action="store_true", help="Generate without publishing")
    parser.add_argument("--no-push", action="store_true", help="Generate and save but do not push to GitHub")
    args = parser.parse_args()

    # Validate environment
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        print("Run: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    if not os.path.isdir(REPO_DIR) and not args.dry_run:
        print(f"ERROR: Repository directory not found at {REPO_DIR}")
        print(f"Run: git clone https://github.com/regentintelgroup/RegentIntel.git {REPO_DIR}")
        sys.exit(1)

    # Determine which reports to generate
    generate_ef = args.ef or (not args.ef and not args.hf)
    generate_hf = args.hf or (not args.ef and not args.hf)

    results = []

    if generate_ef:
        results.append(generate_report("EF", dry_run=args.dry_run))

    if generate_hf:
        results.append(generate_report("HF", dry_run=args.dry_run))

    # Push to GitHub
    if not args.dry_run and not args.no_push:
        git_push()

    print("\n=== PRODUCTION COMPLETE ===")
    for r in results:
        print(f"  {r['title']}: https://regentintel.org/reports/{r['filename']}")
    print("===========================\n")


if __name__ == "__main__":
    main()
