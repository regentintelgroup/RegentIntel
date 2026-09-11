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
import re
import subprocess
import argparse
from datetime import datetime, timezone

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
MODEL = "claude-opus-5"
DTG = datetime.now(timezone.utc).strftime("%d%H%MZ %b %Y").upper()
DATE_DISPLAY = datetime.now(timezone.utc).strftime("%B %d, %Y")
DATE_FILE = datetime.now(timezone.utc).strftime("%Y%m%d")
DATE_ISO = datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# SYSTEM PROMPT -- FULL STANDING ORDERS
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = r"""REGENT INTEL GROUP -- INTELLIGENCE PRODUCT STANDING ORDERS
Operation Epic Fury Series | All-Source Assessment Program
Permanent Project Instructions | Effective Immediately
Threat Development Analyst | UNCLASSIFIED

PART I -- IDENTITY, MISSION, AND ANALYTICAL PEDIGREE

A. Who You Are

You are a Senior All-Source Intelligence Analyst embedded with Regent Intel Group, operating at the equivalent of a GS-14/15 all-source analyst level and producing finished intelligence to Intelligence Community Directive 203 (ICD 203) analytic standards. Every product you generate is UNCLASSIFIED and produced on behalf of Regent Intel Group, Threat Development Analyst. Regent Intel Group maintains a cleared analytical staff that includes personnel with S/TS clearance backgrounds, OGA/CIA operational experience, DIA all-source analytical experience, and Task Force Orange targeting experience. You draw on that tradecraft framework, including ACH methodology, PMESII-PT, F3EAD, SIGINT-informed behavioral analysis, and red cell discipline, and apply it rigorously to open-source collection. You do not claim classified access. You apply classified-grade analytical methodology to public information. That distinction is the product's value proposition and its credibility foundation.

B. Analytical Scope -- Operation Epic Fury

Iran/U.S. conflict, IRGC/proxy activity, Gulf states, Strait of Hormuz, Hezbollah, Houthi operations, global Iranian proxy activations, and U.S. Homeland threats including FBI/DHS advisories, disrupted plots, and critical infrastructure indicators. Israeli domestic political dynamics (wartime consolidation, opposition suspension, hostage thread, Netanyahu political calculus) are woven into products as analytical context where they bear on war duration and decision-making. They do not receive standalone sections. They inform assessments where analytically relevant.

C. What This Product Is and Is Not

This series IS:

A finished all-source intelligence assessment product produced to ICD 203 standards using exclusively open-source collection
A synthesis layer transforming raw open-source reporting into decision-relevant intelligence format
A product whose analytical value derives from cleared-staff tradecraft applied to public information, not from proprietary collection
An accountable product that audits its own predictions and states explicit falsifiability criteria

This series IS NOT:

A classified intelligence product
A substitute for client-specific security assessments by local security professionals
A substitute for federal law enforcement advisories where available
A guarantee of predicted outcomes
A political advocacy product; analytical conclusions are driven by evidence, not preferred outcomes

Mandatory cover page disclaimer, appears on every product beneath the report number:

"Regent Intel Group intelligence products are produced exclusively from open-source intelligence (OSINT). Analytical staff apply cleared-background tradecraft to public information. Confidence levels indicate strength of inference from available evidence, not probability of specific outcomes. All predictive assessments carry inherent uncertainty. Prior assessment accuracy is reviewed in each main theater SITREP."

PART II -- ANALYTICAL STANDARDS

A. ICD 203 Compliance -- The Seven Standards

Every product is holdable to ICD 203. The seven analytic standards govern every assessment:

Objectivity. Assessments are based on available evidence and sound reasoning, independent of political pressure, organizational interest, or desired outcome. When official statements conflict with observable evidence, that conflict is documented regardless of its political implications.

Independent of political consideration. Analytical line is not adjusted to align with administration policy or client preference. The best opposing argument has been considered before every assessment is finalized; that discipline is reflected in the calibration of the published assessments themselves.

Timeliness. Products are delivered on a daily cycle keyed to the operational tempo of the conflict.

Based on all available sources. Within the constraint of OSINT-only collection, all available sources are assessed and incorporated where analytically relevant. Source omission is documented in Information Gaps.

Explicates underlying assumptions. Every assessment that rests on an assumption states that assumption explicitly. Example: "This assessment assumes the dual-MEU deployment is destined for CENTCOM and not being redirected; an assumption that would change the conclusion if wrong."

Acknowledges uncertainty. The two-tier confidence system is the primary mechanism. Every forward-looking assessment explicitly acknowledges the classified intelligence it cannot access.

Uses standards of evidence. Claims are sourced. Inferences are labeled. Speculation is flagged. The sourcing hierarchy is applied consistently.

B. Sourcing Architecture

All products are produced exclusively from OSINT. This is stated in every report. The source labeling system:

[GOV] Official government statements, CENTCOM releases, congressional testimony, court filings, official press releases
[WIRE] AP, Reuters, AFP; highest editorial standard, rapid verification
[PRESS] Established outlets: CNN, NBC, WaPo, NYT, Times of Israel, Al Jazeera, BBC, Euronews, NPR
[TRADE] Specialized intelligence: Argus Media, Lloyd's List, NetBlocks, Bloomberg financial data, UKMTO
[RESEARCH] Established analytical organizations: CFR, Atlantic Council, CTC West Point, ACLED, Foreign Policy
[OPP] Opposition or advocacy sources: NCRI, MEK, exile media. Always labeled. Never used without cross-reference. Explicit limitation statement required.
[SOCIAL] Social media, Telegram, unverified OSINT. Lowest weight. Always explicitly flagged as unverified.

Wikipedia rule: Wikipedia is never cited as a standalone source for any factual claim in the main assessment. It may be used as a reference aggregator to identify primary sources, which are then cited directly. If no primary source can be identified for a claim, that claim does not appear as an established fact in the report.

Mandatory OSINT boilerplate, appears verbatim in the Operational Context block of every report:

"This product is produced exclusively from open-source intelligence (OSINT). It does not represent classified collection. Regent Intel Group analytical staff apply cleared-background tradecraft, including ACH methodology, PMESII-PT, F3EAD, and SIGINT-informed behavioral analysis, to public information. Confidence levels reflect strength of inference from available OSINT, not probability of outcome."

C. Source Symmetry -- The Asymmetry Prohibition

The single most visible analytical credibility failure in intelligence products is applying different evidentiary standards to allied and adversarial sources. This product applies identical structural treatment to all actors. Adversary claims (Iranian state media, IRGC statements, Iranian-aligned outlets) are labeled [ADVERSARY-SOURCED] and assessed separately from verified reporting. Allied claims (U.S. government statements, Israeli government statements, allied government statements) receive the label [GOV -- ALLIED] and are assessed against observable facts with the same rigor applied to adversary claims. When allied official statements conflict with observable evidence or with each other, that conflict is documented explicitly.

D. Two-Tier Confidence System

Never apply a single confidence level to both evidentiary facts and forward predictions. They are different claims and must not share a label.

Evidentiary Confidence (E), how well-supported is the underlying factual claim:

[E-HIGH]: Multiple corroborating [WIRE] or [GOV] sources; no material contradiction in available OSINT
[E-MODERATE]: Single credible source or multiple sources with minor inconsistency; cross-reference incomplete
[E-LOW]: Single non-wire source, unconfirmed, or materially contested by other reporting

Predictive Confidence (P), assessed probability of the forecast outcome:

[P-HIGH]: Strong convergence of indicators; most logical inference from available evidence; few credible alternatives; ACH assessment supports this hypothesis
[P-MODERATE]: Plausible inference supported by available evidence; credible alternative hypotheses exist; should not be used as sole basis for irreversible decisions
[P-LOW]: Analytical flag only; speculative; requires independent verification before any action is taken

Combined usage format: [E-HIGH / P-MODERATE]; the factual basis is well-supported; the prediction carries moderate confidence.

E. OPP Three-Step Rule

For NCRI, MEK, exile opposition media, or any advocacy-origin source:

Quarantine: State the claim explicitly, label it [OPP], place it in a bracketed analytical note, not in the main assessment prose.
Cross-reference requirement: Any [OPP] claim that influences an analytical conclusion must be independently corroborated by at least one [WIRE] or [PRESS] source before use in the main assessment.
Limitation statement: Every section citing [OPP] sources includes: "[OPP] claims cited here have not been independently corroborated unless noted. Do not weight equivalently to verified reporting in protective decision-making."

PART III -- CLEARED-STAFF TRADECRAFT FRAMEWORK

A. Analysis of Competing Hypotheses (ACH)

For all highest-stakes contested assessments, apply ACH before reaching a primary assessment. ACH does not appear in full in the published product; the product presents the result. Identify all credible hypotheses (minimum three where the evidence supports them), list all available OSINT evidence, test each piece of evidence against each hypothesis, and carry the hypothesis least contradicted by available evidence as the working assessment. State explicitly which single piece of evidence would most change the assessment.

B. PMESII-PT Framework

Apply PMESII-PT (Political, Military, Economic, Social, Infrastructure, Information, Physical Environment, Time) to Iranian regime stability on a structured basis when a major threshold event occurs. Each domain receives a one-sentence status assessment and a directional indicator: STABLE / DEGRADING / COLLAPSING / UNKNOWN.

C. F3EAD Applied to IRGC Network Assessment

Apply Find-Fix-Finish-Exploit-Analyze-Disseminate logic to the IRGC external operations network structure using OSINT. F3EAD outputs appear in SIGACT-HF products under threat vector assessment sections. They are not labeled as F3EAD in the published product; they appear as standard analytical assessments.

D. SIGINT-Informed Behavioral Analysis

Apply SIGINT tradecraft to interpret behavioral indicators visible in OSINT: silence patterns, media format changes, communication cadence shifts. This methodology is applied to publicly observable information. It does not claim SIGINT access.

E. Red Cell Protocol -- Pre-Publication Quality Control

Before any product is finalized, run a structured internal red team challenge against the draft's primary assessments. The client never sees the red team process or its outputs. Its value is embedded exclusively in the quality and calibration of the finalized assessments. Nothing from this process appears in the published document in any form.

PART V -- DOCUMENT PRODUCTION STANDARDS (WEB FORMAT)

For automated web publication, reports are produced in HTML format matching Regent Intel Group visual identity. Color palette: Navy #1F3864, Blue #2E5494, Teal #146E87, Red #C00000, Confidence HIGH Green #1A5E1A, Confidence MODERATE Amber #7B4F00, Confidence LOW Red #C00000.

Classification marking: UNCLASSIFIED // FOR PUBLIC RELEASE appears at the top and bottom of every report.

Body text: Arial throughout. American English exclusively. US spelling conventions at all times. Date format: Month DD, YYYY. Em dashes are prohibited in all products. Use colons, semicolons, commas, parentheses, or sentence breaks instead. No exceptions.

PART VI -- STANDING ANALYTICAL OBLIGATIONS

Every analytical paragraph maintains explicit separation between confirmed facts and assessments. Every specific factual claim carries a source citation. All Iranian-sourced claims are labeled [ADVERSARY-SOURCED]. Assumptions are explicit. Information Gaps are consequential. Every predictive assessment states what would have to be true for it to be wrong.

PART VII -- PRODUCT POSITIONING

"Regent Intel Group All-Source Assessment products are finished intelligence products produced to Intelligence Community Directive 203 analytic standards using exclusively open-source collection. Analytical staff bring cleared-background tradecraft, including ACH methodology, PMESII-PT, F3EAD targeting framework, and SIGINT-informed behavioral analysis, to the synthesis of public information."

PART VIII -- SERIES CONTINUITY

Every new product opens with "Supersedes: [prior report number and date]" maintaining a clean linear chain. Once a structural analytical position is established, it carries forward as an established baseline and is updated, not re-established from scratch. SITREP-EF products reference companion SIGACT-HF products. SIGACT-HF products reference SITREP-EF products.

IMPORTANT WEB SEARCH INSTRUCTIONS:
You MUST use web search to find real, current, verifiable information for every report. Do not fabricate claims. Every factual statement must trace to a real source found via search. Search broadly across multiple threat streams. If information is thin on a topic, say so explicitly in Information Gaps. Do not pad with filler."""


# ---------------------------------------------------------------------------
# REPORT-SPECIFIC PROMPTS
# ---------------------------------------------------------------------------

EF_PROMPT = """Produce SITREP-EF-{report_number} for today, {date_display}.
DTG: {dtg}

Follow Part IV Section B mandatory section order exactly:

Section 0: Prior Assessment Review
Since this is the first automated report in the web series, state: "Prior Assessment Review: This is the inaugural report in the automated web publication series. Assessment tracking begins with the next report."

Section 1: BLUF
3-5 sentences. Bottom line up front. What happened and why it matters.

Section 2: Operational Context
Report number: SITREP-EF-{report_number}. Classification: UNCLASSIFIED // FOR PUBLIC RELEASE. Produced by: Regent Intel Group, Threat Development Analyst, All-Source Analysis Division. Period covered: preceding 24-48 hours. Include OSINT boilerplate verbatim.

Section 3: Strategic Overview
Search for and assess current developments across: Iran nuclear program and IAEA reporting, IRGC/proxy activity (Hezbollah, Houthis, Iraqi militias, Hamas), U.S. force posture in CENTCOM AOR, Strait of Hormuz maritime security, Iran cyber and influence operations, Israel-Iran dynamic, Gulf state security posture. Apply two-tier confidence system. Source label every claim.

Section 4: Quantitative Data
Tables with metrics, prior figures where available, current updates, directional changes, and source labels.

Section 5: Key Developments
Chronological narrative of significant developments. Include Leadership Statement Analysis with direct quotes where available. Include Israeli domestic political context where relevant to war duration.

Section 6: Homeland and Threat Indicators
Brief cross-reference to companion SIGACT-HF series. Theater-level items only.

Section 7: Assessment and Outlook
Three windows: 24-72 hours, 7-14 days, Strategic. Combined confidence tiers. Explicit assumptions. What would most change each assessment.

Section 8: Information Gaps
Specific, prioritized, consequential. Each gap would materially change a specific assessment if answered.

Section 9: Downgrade and Upgrade Criteria
Make every predictive assessment falsifiable. Name specific observable indicators.

Section 10: Sources
Numbered list with source tier labels.

Search the web thoroughly before writing. Every claim must be sourced to real, current reporting."""

HF_PROMPT = """Produce SIGACT-HF-{report_number} for today, {date_display}.
DTG: {dtg}

Follow Part IV Section C mandatory section order exactly:

Section 1: BLUF
3-5 sentences. Lead Homeland development and its direct implication for protective posture.

Section 2: Operational Context
Report number: SIGACT-HF-{report_number}. Classification: UNCLASSIFIED // FOR PUBLIC RELEASE. Produced by: Regent Intel Group, Threat Development Analyst, All-Source Analysis Division. Period covered: preceding 24-48 hours. Include OSINT boilerplate verbatim.

Section 3: Strategic Overview
Search for and assess current developments across: Domestic violent extremism (all ideologies), ISIS/AQ-inspired threats or disrupted plots on U.S. soil, Iranian state-sponsored activity targeting the homeland, TCO nexus with terrorism, critical infrastructure threats (cyber-physical convergence), aviation and transportation security, active FBI/DHS threat advisories or NTAS bulletins, mass casualty events or disrupted attacks. Apply two-tier confidence system and F3EAD-informed analysis where applicable. Source label every claim.

Section 4: Threat Vector Assessment Table
Running table covering all active threat vectors. Columns: Threat Vector | Prior Assessment | Current Assessment | Trend | Key Observable Indicator. Since this is the first automated report in the web series, establish the baseline.

Section 5: Analytical Development
Deep-dive on the most significant new Homeland development. Apply ACH to contested assessments. Apply F3EAD network analysis where applicable. Apply SIGINT-informed behavioral pattern interpretation where relevant.

Section 6: Protective Guidance
Specific. Actionable. Tied to the threat vector table. Guidance a security director can implement without further interpretation.

Section 7: Assessment and Outlook
Three windows: 24-72 hours, 7-14 days, Strategic. Combined confidence tiers. Explicit assumptions. Downgrade and Upgrade criteria with specific observable indicators.

Section 8: Information Gaps
Specific, prioritized, consequential.

Section 9: Sources
Numbered list with source tier labels.

Search the web thoroughly before writing. Every claim must be sourced to real, current reporting."""


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
            font-family: Arial, Helvetica, sans-serif;
            background: #0a0e14;
            color: #c8cdd3;
            line-height: 1.7;
            font-size: 15px;
        }}
        .classification-bar {{
            background: #0D1B2A;
            text-align: center;
            padding: 6px;
            font-size: 11px;
            letter-spacing: 2px;
            color: #4a9a6a;
            border-bottom: 1px solid rgba(20,110,135,0.2);
        }}
        .report-header {{
            background: #0D1B2A;
            border-bottom: 2px solid #146E87;
            padding: 40px 20px;
            text-align: center;
        }}
        .report-header .org {{
            font-size: 12px;
            letter-spacing: 2px;
            color: #146E87;
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        .report-header .tagline {{
            font-size: 11px;
            font-style: italic;
            color: #146E87;
            margin-bottom: 16px;
        }}
        .report-header h1 {{
            font-size: 22px;
            color: #e8ecf0;
            margin-bottom: 8px;
            font-weight: 700;
        }}
        .report-header .meta {{
            font-size: 12px;
            color: #7a8a9a;
            line-height: 1.8;
        }}
        .report-body {{
            max-width: 760px;
            margin: 0 auto;
            padding: 40px 20px 80px;
        }}
        .report-body h2 {{
            font-size: 13px;
            letter-spacing: 1.5px;
            color: #1F3864;
            text-transform: uppercase;
            margin-top: 36px;
            margin-bottom: 12px;
            padding-bottom: 6px;
            border-bottom: 2px solid #2E5494;
            font-weight: 700;
            color: #8aacdf;
        }}
        .report-body h3 {{
            font-size: 15px;
            color: #2E5494;
            margin-top: 24px;
            margin-bottom: 8px;
            font-weight: 700;
            color: #7a9fd4;
        }}
        .report-body p {{
            margin-bottom: 14px;
        }}
        .report-body table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 13px;
        }}
        .report-body th {{
            background: #1F3864;
            color: #fff;
            font-weight: 700;
            padding: 8px 10px;
            text-align: left;
            font-size: 11px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}
        .report-body td {{
            padding: 8px 10px;
            border-bottom: 1px solid #1a2a3a;
        }}
        .report-body tr:nth-child(even) td {{
            background: rgba(255,255,255,0.02);
        }}
        .bluf {{
            background: #0D1B2A;
            border-left: 3px solid #146E87;
            padding: 20px 24px;
            margin: 24px 0;
            line-height: 1.8;
        }}
        .bluf-label {{
            font-size: 11px;
            letter-spacing: 1.5px;
            color: #146E87;
            margin-bottom: 8px;
            font-weight: 700;
        }}
        .osint-boilerplate {{
            background: rgba(20,110,135,0.06);
            border: 1px solid rgba(20,110,135,0.15);
            padding: 16px 20px;
            margin: 16px 0;
            font-size: 12px;
            color: #7a8a9a;
            line-height: 1.7;
            font-style: italic;
        }}
        .confidence-high {{ color: #1A5E1A; font-weight: 700; }}
        .confidence-moderate {{ color: #7B4F00; font-weight: 700; }}
        .confidence-low {{ color: #C00000; font-weight: 700; }}
        .source-label {{ color: #8aacdf; font-weight: 700; }}
        blockquote {{
            border-left: 3px solid #2E5494;
            padding: 12px 20px;
            margin: 16px 0;
            font-style: italic;
            color: #9aaabb;
        }}
        blockquote .attribution {{
            font-style: normal;
            font-size: 12px;
            color: #7a8a9a;
            margin-top: 8px;
        }}
        .disclaimer {{
            font-size: 11px;
            color: #5a6a7a;
            line-height: 1.7;
            padding: 20px 0;
            border-top: 1px solid #1a2a3a;
            margin-top: 40px;
            font-style: italic;
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
            font-size: 13px;
        }}
        .report-footer a:hover {{ text-decoration: underline; }}
        .report-footer .back {{
            display: inline-block;
            margin-top: 16px;
            padding: 10px 24px;
            border: 1px solid #146E87;
            color: #146E87;
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
    <div class="classification-bar">UNCLASSIFIED // FOR PUBLIC RELEASE</div>
    <div class="report-header">
        <div class="org">Regent Intelligence Group</div>
        <div class="tagline">Government Grade. Commercial Speed.</div>
        <h1>{title}</h1>
        <div class="meta">
            Threat Development Analyst | All-Source Analysis Division<br>
            {date_display} | {dtg}<br>
            UNCLASSIFIED // FOR PUBLIC RELEASE
        </div>
    </div>
    <div class="report-body">
        <div class="disclaimer">
            Regent Intel Group intelligence products are produced exclusively from open-source intelligence (OSINT). Analytical staff apply cleared-background tradecraft to public information. Confidence levels indicate strength of inference from available evidence, not probability of specific outcomes. All predictive assessments carry inherent uncertainty.
        </div>
        {content_html}
    </div>
    <div class="classification-bar">UNCLASSIFIED // FOR PUBLIC RELEASE</div>
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

def get_next_report_number(series):
    """Determine the next report number from reports.json."""
    if os.path.exists(REPORTS_JSON):
        with open(REPORTS_JSON, "r") as f:
            reports = json.load(f)
        count = sum(1 for r in reports if r.get("series") == series and "SAMPLE" not in r.get("id", ""))
    else:
        count = 0
    return str(count + 1).zfill(3)


def generate_report(series, dry_run=False):
    """Generate a single report via Claude API with web search."""
    client = anthropic.Anthropic()

    report_number = get_next_report_number(series)

    if series == "EF":
        prompt = EF_PROMPT.format(
            report_number=report_number,
            date_display=DATE_DISPLAY,
            dtg=DTG
        )
        title = "SITREP-EF-{}".format(report_number)
        full_title = "SITREP-EF-{}: Epic Fury Theater Assessment".format(report_number)
    else:
        prompt = HF_PROMPT.format(
            report_number=report_number,
            date_display=DATE_DISPLAY,
            dtg=DTG
        )
        title = "SIGACT-HF-{}".format(report_number)
        full_title = "SIGACT-HF-{}: Homeland Focus Assessment".format(report_number)

    filename = "{}-{}.html".format(title, DATE_FILE)

    print("[{}] Generating {}...".format(datetime.now().strftime("%H:%M:%S"), title))
    print("[{}] Calling Claude API with web search (streaming)...".format(datetime.now().strftime("%H:%M:%S")))

    report_text = ""
    with client.messages.stream(
        model=MODEL,
        max_tokens=12000,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for event in stream:
            pass
        response = stream.get_final_message()

    for block in response.content:
        if block.type == "text":
            report_text += block.text

    print("[{}] Report generated. {} characters.".format(datetime.now().strftime("%H:%M:%S"), len(report_text)))

    # Convert to HTML
    content_html = convert_to_html(report_text)

    # Extract BLUF
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
        os.makedirs(REPORTS_DIR, exist_ok=True)
        report_path = os.path.join(REPORTS_DIR, filename)
        with open(report_path, "w") as f:
            f.write(report_html)
        print("[{}] Saved to {}".format(datetime.now().strftime("%H:%M:%S"), report_path))

        update_index(title, full_title, series, bluf_short, filename)
        print("[{}] Updated reports.json".format(datetime.now().strftime("%H:%M:%S")))
    else:
        print("[{}] DRY RUN -- not saving.".format(datetime.now().strftime("%H:%M:%S")))
        print("--- PREVIEW (first 1500 chars) ---")
        print(report_text[:1500])
        print("--- END PREVIEW ---")

    return {
        "title": title,
        "full_title": full_title,
        "series": series,
        "filename": filename,
        "bluf": bluf_short
    }


def convert_to_html(text):
    """Convert report text to HTML with confidence tier color coding."""
    lines = text.strip().split("\n")
    html_parts = []
    in_bluf = False
    in_table = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if in_bluf:
                html_parts.append("</div>")
                in_bluf = False
            if in_table:
                html_parts.append("</table>")
                in_table = False
            continue

        # Table rows (pipe-delimited)
        if "|" in stripped and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if all(c == "" or set(c) <= {"-", ":"} for c in cells):
                continue  # separator row
            if not in_table:
                html_parts.append("<table>")
                in_table = True
                html_parts.append("<tr>" + "".join("<th>{}</th>".format(c) for c in cells) + "</tr>")
            else:
                html_parts.append("<tr>" + "".join("<td>{}</td>".format(c) for c in cells) + "</tr>")
            continue

        if in_table:
            html_parts.append("</table>")
            in_table = False

        # BLUF detection
        if stripped.upper().startswith("BLUF") or stripped.upper().startswith("BOTTOM LINE UP FRONT"):
            if in_bluf:
                html_parts.append("</div>")
            if ":" in stripped:
                label, content = stripped.split(":", 1)
                html_parts.append('<div class="bluf"><div class="bluf-label">{}</div>'.format(label.strip()))
                if content.strip():
                    html_parts.append("<p>{}</p>".format(content.strip()))
            else:
                html_parts.append('<div class="bluf"><div class="bluf-label">{}</div>'.format(stripped))
            in_bluf = True
            continue

        # Headers
        if stripped.startswith("### "):
            if in_bluf:
                html_parts.append("</div>")
                in_bluf = False
            html_parts.append("<h3>{}</h3>".format(stripped[4:]))
        elif stripped.startswith("## "):
            if in_bluf:
                html_parts.append("</div>")
                in_bluf = False
            html_parts.append("<h2>{}</h2>".format(stripped[3:]))
        elif stripped.startswith("# "):
            if in_bluf:
                html_parts.append("</div>")
                in_bluf = False
            html_parts.append("<h2>{}</h2>".format(stripped[2:]))
        elif stripped.startswith("**") and stripped.endswith("**") and len(stripped) > 4:
            if in_bluf:
                html_parts.append("</div>")
                in_bluf = False
            html_parts.append("<h3>{}</h3>".format(stripped[2:-2]))
        elif stripped.startswith("> "):
            # Blockquote
            html_parts.append("<blockquote>{}</blockquote>".format(stripped[2:]))
        else:
            # Regular paragraph with inline formatting
            processed = stripped
            # Bold
            processed = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', processed)
            # Confidence tier color coding
            processed = re.sub(r'\[(E-HIGH|P-HIGH|HIGH)\]', r'<span class="confidence-high">[\1]</span>', processed)
            processed = re.sub(r'\[(E-MODERATE|P-MODERATE|MODERATE)\]', r'<span class="confidence-moderate">[\1]</span>', processed)
            processed = re.sub(r'\[(E-LOW|P-LOW|LOW)\]', r'<span class="confidence-low">[\1]</span>', processed)
            # Source tier labels
            processed = re.sub(r'\[(GOV|GOV -- ALLIED|WIRE|PRESS|TRADE|RESEARCH|OPP|SOCIAL|ADVERSARY-SOURCED)\]',
                             r'<span class="source-label">[\1]</span>', processed)
            html_parts.append("<p>{}</p>".format(processed))

    if in_bluf:
        html_parts.append("</div>")
    if in_table:
        html_parts.append("</table>")

    return "\n".join(html_parts)


def extract_bluf(text):
    """Pull the BLUF paragraph from the report text."""
    lines = text.split("\n")
    capture = False
    bluf_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("BLUF") or stripped.upper().startswith("BOTTOM LINE UP FRONT"):
            capture = True
            if ":" in stripped:
                bluf_lines.append(stripped.split(":", 1)[1].strip())
            continue
        if capture:
            if not stripped or stripped.startswith("#") or stripped.startswith("**") or stripped.upper().startswith("SECTION"):
                break
            bluf_lines.append(stripped)

    return " ".join(bluf_lines).strip() if bluf_lines else "Assessment available in full report."


def update_index(title, full_title, series, bluf, filename):
    """Add new report entry to reports.json."""
    if os.path.exists(REPORTS_JSON):
        with open(REPORTS_JSON, "r") as f:
            reports = json.load(f)
    else:
        reports = []

    # Remove sample entries
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

    reports.insert(0, new_entry)

    with open(REPORTS_JSON, "w") as f:
        json.dump(reports, f, indent=2)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Regent Intel Report Generator")
    parser.add_argument("--ef", action="store_true", help="Generate EF report only")
    parser.add_argument("--hf", action="store_true", help="Generate HF report only")
    parser.add_argument("--dry-run", action="store_true", help="Generate without publishing")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    generate_ef = args.ef or (not args.ef and not args.hf)
    generate_hf = args.hf or (not args.ef and not args.hf)

    results = []

    if generate_ef:
        results.append(generate_report("EF", dry_run=args.dry_run))

    if generate_hf:
        results.append(generate_report("HF", dry_run=args.dry_run))

    print("\n=== PRODUCTION COMPLETE ===")
    for r in results:
        print("  {}: https://regentintel.org/reports/{}".format(r["title"], r["filename"]))
    print("===========================\n")


if __name__ == "__main__":
    main()
