"""
PDF Report Generator — V4
=========================
ReportLab + Noto Sans Devanagari for proper bilingual PDF rendering.
Drop-in replacement for V3: same generate_pdf() signature.

Design principles:
  1. All text via ReportLab Paragraph — native Unicode, no sanitisation hacks.
  2. Platypus flowable pipeline — automatic page breaks, no cursor math.
  3. Cost table via Table + TableStyle — zero layout crashes.
  4. XML-escape every user string (Paragraph parser is XML-based).

Font setup:
  Place these files in the fonts/ directory:
    NotoSansDevanagari-Regular.ttf
    NotoSansDevanagari-Bold.ttf
  Download from https://fonts.google.com/noto/specimen/Noto+Sans+Devanagari
"""

import os
import io
from xml.sax.saxutils import escape as _esc

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import Color, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from core.models import RecommendationResult


# ── Dimensions ─────────────────────────────────────────────────────────────────

PAGE_W, PAGE_H = A4                         # 595.27 × 841.89 pt
L_MARGIN  = 15 * mm
R_MARGIN  = 15 * mm
T_MARGIN  = 28 * mm                         # room for header band
B_MARGIN  = 18 * mm
USABLE_W  = PAGE_W - L_MARGIN - R_MARGIN    # ~467 pt

ROOT_DIR  = os.path.dirname(os.path.dirname(__file__))
FONTS_DIR = os.path.join(ROOT_DIR, "fonts")
NOTO_REG  = os.path.join(FONTS_DIR, "NotoSansDevanagari-Regular.ttf")
NOTO_BOLD = os.path.join(FONTS_DIR, "NotoSansDevanagari-Bold.ttf")


# ── Colours (matching V3 palette) ──────────────────────────────────────────────

def _c(r, g, b):
    return Color(r / 255, g / 255, b / 255)

C_MID_GREEN      = _c(46, 125, 50)
C_DARK_GREEN     = _c(30, 100, 30)
C_LIGHT_GREEN_BG = _c(232, 245, 233)
C_AMBER          = _c(255, 143, 0)
C_RED            = _c(198, 40, 40)
C_WHITE          = white
C_DARK_GRAY      = _c(40, 40, 40)
C_MID_GRAY       = _c(100, 100, 100)
C_TABLE_HEADER   = _c(27, 94, 32)
C_TABLE_ALT      = _c(240, 248, 240)
C_BORDER         = _c(180, 180, 180)
C_HINDI_HEADER   = _c(13, 71, 161)
C_AI_HEADER      = _c(74, 20, 140)


# ── Font registration ──────────────────────────────────────────────────────────

_fonts_ready = False
_has_noto    = False


def _register_fonts():
    """Register Noto Sans Devanagari (regular + bold) once per process."""
    global _fonts_ready, _has_noto
    if _fonts_ready:
        return
    _fonts_ready = True
    if os.path.exists(NOTO_REG):
        try:
            pdfmetrics.registerFont(TTFont("Noto", NOTO_REG))
            bold = NOTO_BOLD if os.path.exists(NOTO_BOLD) else NOTO_REG
            pdfmetrics.registerFont(TTFont("NotoBold", bold))
            pdfmetrics.registerFontFamily(
                "Noto", normal="Noto", bold="NotoBold")
            _has_noto = True
        except Exception:
            _has_noto = False


def _fn():
    """Normal font name."""
    return "Noto" if _has_noto else "Helvetica"


def _fb():
    """Bold font name."""
    return "NotoBold" if _has_noto else "Helvetica-Bold"


# ── Paragraph styles ───────────────────────────────────────────────────────────

def _make_styles():
    """Build style dict. Called after font registration so names resolve."""
    fn, fb = _fn(), _fb()
    return {
        "body":       ParagraphStyle("body",       fontName=fn, fontSize=10,
                                      leading=14,  textColor=C_DARK_GRAY),
        "body_sm":    ParagraphStyle("body_sm",    fontName=fn, fontSize=9,
                                      leading=13,  textColor=C_DARK_GRAY),
        "body_xs":    ParagraphStyle("body_xs",    fontName=fn, fontSize=8,
                                      leading=11,  textColor=C_MID_GRAY),
        "hero":       ParagraphStyle("hero",       fontName=fb, fontSize=13,
                                      leading=18,  textColor=C_MID_GREEN),
        "hero_sub":   ParagraphStyle("hero_sub",   fontName=fn, fontSize=9,
                                      leading=13,  textColor=C_MID_GRAY),
        "bullet":     ParagraphStyle("bullet",     fontName=fn, fontSize=9,
                                      leading=12,  textColor=C_DARK_GRAY,
                                      leftIndent=4 * mm, bulletIndent=0),
        "tip_lbl":    ParagraphStyle("tip_lbl",    fontName=fb, fontSize=9,
                                      leading=12,  textColor=C_MID_GREEN,
                                      leftIndent=2 * mm),
        "tip_body":   ParagraphStyle("tip_body",   fontName=fn, fontSize=9,
                                      leading=12,  textColor=C_DARK_GRAY,
                                      leftIndent=6 * mm),
        "ic_head":    ParagraphStyle("ic_head",    fontName=fb, fontSize=10,
                                      leading=14,  textColor=C_MID_GREEN),
        "ic_detail":  ParagraphStyle("ic_detail",  fontName=fn, fontSize=9,
                                      leading=12,  textColor=C_DARK_GRAY,
                                      leftIndent=4 * mm),
    }


# ── Header / footer (drawn on canvas every page) ──────────────────────────────

def _draw_header_footer(canvas, doc):
    canvas.saveState()
    # Green header band
    canvas.setFillColor(C_MID_GREEN)
    canvas.rect(0, PAGE_H - 22 * mm, PAGE_W, 22 * mm, fill=1, stroke=0)
    canvas.setFillColor(C_WHITE)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawCentredString(
        PAGE_W / 2, PAGE_H - 15 * mm,
        "Farmer Revenue Optimizer  |  Crop Advisory Report")
    # Footer
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(C_MID_GRAY)
    canvas.drawCentredString(
        PAGE_W / 2, 8 * mm,
        f"Page {canvas.getPageNumber()} | Advisory only. Verify with local KVK.")
    canvas.restoreState()


# ── Flowable helpers ───────────────────────────────────────────────────────────

def _section(title, color=C_DARK_GREEN):
    """Section heading: full-width coloured band with white bold text.
    Returns list of flowables [Spacer, Table, Spacer]."""
    p = Paragraph(
        f"<b>{_esc(title)}</b>",
        ParagraphStyle("_sec", fontName=_fb(), fontSize=11,
                        leading=14, textColor=C_WHITE))
    t = Table([[p]], colWidths=[USABLE_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [Spacer(1, 4 * mm), t, Spacer(1, 2 * mm)]


def _hero_band(paragraphs):
    """Light-green hero card built from a list of Paragraphs.
    Each Paragraph becomes its own row so leading is respected."""
    data = [[p] for p in paragraphs]
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, -1), C_LIGHT_GREEN_BG),
        ("LEFTPADDING", (0, 0), (-1, -1), int(3 * mm)),
        ("RIGHTPADDING", (0, 0), (-1, -1), int(3 * mm)),
        ("TOPPADDING", (0, 0), (0, 0), int(3 * mm)),
        ("BOTTOMPADDING", (-1, -1), (-1, -1), int(3 * mm)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for i in range(len(data)):
        if i > 0:
            style_cmds.append(("TOPPADDING", (0, i), (0, i), 1))
        if i < len(data) - 1:
            style_cmds.append(("BOTTOMPADDING", (0, i), (0, i), 1))
    t = Table(data, colWidths=[USABLE_W])
    t.setStyle(TableStyle(style_cmds))
    return t


def _kpi(label, value, color=C_DARK_GREEN):
    """Single KPI row as a Paragraph — safe for any script."""
    sty = ParagraphStyle("_kpi", fontName=_fb(), fontSize=11,
                          leading=16, textColor=color, leftIndent=3 * mm)
    return Paragraph(_esc(f"{label}  {value}"), sty)


def _warning_band(text):
    """Red warning bar. Returns list of flowables."""
    p = Paragraph(
        f"<b>{_esc(text)}</b>",
        ParagraphStyle("_warn", fontName=_fb(), fontSize=10,
                        leading=14, textColor=C_WHITE))
    t = Table([[p]], colWidths=[USABLE_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_RED),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [Spacer(1, 2 * mm), t, Spacer(1, 2 * mm)]


# ── Cost table ─────────────────────────────────────────────────────────────────

def _cost_table(result, use_hindi=False):
    """3-column cost table identical in structure to V3."""
    if use_hindi:
        headers = ["लागत श्रेणी", "कुल (Rs.)", "बचत संभव (Rs.)"]
    else:
        headers = ["Cost Category", "Total (Rs.)", "Save Up To (Rs.)"]

    col_w = [USABLE_W * 0.44, USABLE_W * 0.28, USABLE_W * 0.28]

    hdr_sty   = ParagraphStyle("_th", fontName=_fb(), fontSize=9,
                                leading=12, textColor=C_WHITE,
                                alignment=TA_CENTER)
    cell_bold = ParagraphStyle("_td_b", fontName=_fb(), fontSize=9,
                                leading=12, textColor=C_DARK_GRAY)
    cell_r    = ParagraphStyle("_td_r", fontName=_fn(), fontSize=9,
                                leading=12, textColor=C_DARK_GRAY,
                                alignment=TA_RIGHT)
    cell_g    = ParagraphStyle("_td_g", fontName=_fn(), fontSize=9,
                                leading=12, textColor=C_MID_GREEN,
                                alignment=TA_RIGHT)

    data = [[Paragraph(_esc(h), hdr_sty) for h in headers]]

    for item in result.cost_items:
        name = item.name_hi if use_hindi else item.name_en
        data.append([
            Paragraph(_esc(name), cell_bold),
            Paragraph(f"Rs. {item.amount:,}", cell_r),
            Paragraph(f"Rs. {item.reducible_by:,}", cell_g),
        ])

    total_lbl = "कुल" if use_hindi else "TOTAL"
    data.append([
        Paragraph(f"<b>{_esc(total_lbl)}</b>", cell_bold),
        Paragraph(f"<b>Rs. {result.total_cost:,}</b>", cell_r),
        Paragraph(f"<b>Rs. {result.total_reducible_cost:,}</b>", cell_g),
    ])

    t = Table(data, colWidths=col_w)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), C_TABLE_HEADER),
        ("GRID", (0, 0), (-1, -1), 0.5, C_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, -1), (-1, -1), C_LIGHT_GREEN_BG),
    ]
    for i in range(1, len(data) - 1):
        if (i - 1) % 2 == 1:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), C_TABLE_ALT))
    t.setStyle(TableStyle(style_cmds))
    return t


# ── Price label ────────────────────────────────────────────────────────────────

def _price_lbl(price_type, lang="en"):
    en = {
        "msp":    "MSP 2023-24 (Govt. Minimum Support Price)",
        "frp":    "FRP 2023-24 (Govt. Fair & Remunerative Price)",
        "market": "Market Average (conservative estimate)",
    }
    hi = {
        "msp":    "MSP 2023-24 (सरकारी न्यूनतम समर्थन मूल्य)",
        "frp":    "FRP 2023-24 (सरकारी उचित एवं लाभकारी मूल्य)",
        "market": "बाजार औसत (रूढ़िवादी अनुमान)",
    }
    return (hi if lang == "hi" else en).get(
        price_type, f"Reference price ({price_type.upper()})")


# ── English section ────────────────────────────────────────────────────────────

def _build_en(r, farm_location, S):
    """Return list of flowables for the English section."""
    story = []

    # Hero band
    hero = [Paragraph(_esc(f"{r.crop_name_en}  |  {r.acreage:.1f} acres"),
                       S["hero"])]
    if farm_location:
        hero.append(Paragraph(_esc(farm_location), S["hero_sub"]))
    if r.soil_name_en:
        hero.append(Paragraph(
            _esc(f"Soil: {r.soil_name_en}  |  Climate: {r.climate_zone}"),
            S["hero_sub"]))
    hero.append(_kpi("Gross Revenue:", f"Rs. {r.gross_revenue:,}"))
    hero.append(_kpi("Total Input Cost:", f"Rs. {r.total_cost:,}", C_AMBER))
    mc = C_MID_GREEN if r.net_margin >= 0 else C_RED
    hero.append(_kpi("Net Margin:", f"Rs. {r.net_margin:,}", mc))
    hero.append(_kpi("Potential Savings:",
                      f"Rs. {r.total_reducible_cost:,}", C_MID_GREEN))
    story.append(_hero_band(hero))
    story.append(Spacer(1, 4 * mm))

    # Price information
    story.extend(_section("Price Information"))
    story.append(Paragraph(
        _esc(f"Price: Rs. {r.price_per_quintal:,}/quintal") + "<br/>" +
        _esc(f"Basis: {_price_lbl(r.price_type, 'en')}"), S["body"]))

    # Summary
    story.extend(_section("Summary"))
    narrative = r.narrative_en
    for dup in [" soil soil ", " Soil soil ", " Soil Soil "]:
        narrative = narrative.replace(dup, dup.split()[0] + " ")
    story.append(Paragraph(_esc(narrative), S["body"]))

    if r.risk_flag:
        story.extend(_warning_band(
            "WARNING: Net margin below Rs. 5,000/acre. "
            "Urgent action required."))

    # Cost table
    story.extend(_section("Cost Breakdown"))
    story.append(_cost_table(r, use_hindi=False))
    story.append(Spacer(1, 2 * mm))

    # Cost reduction tips
    story.extend(_section("Cost Reduction Guide (Full Detail)"))
    for i, item in enumerate(r.cost_items, 1):
        story.append(KeepTogether([
            Paragraph(_esc(f"{i}. {item.name_en}"), S["tip_lbl"]),
            Paragraph(_esc(item.reduction_tip_en), S["tip_body"]),
            Spacer(1, 1 * mm),
        ]))

    # Low-cost tips
    story.extend(_section("Low-Cost & Ancient Farming Techniques"))
    for tip in r.low_cost_tips_en:
        story.append(Paragraph(f"- {_esc(tip)}", S["bullet"]))
    story.append(Spacer(1, 3 * mm))

    # Intercropping
    if r.intercrop_suggestions:
        story.extend(_section("Intercropping Opportunities"))
        for sugg in r.intercrop_suggestions:
            story.append(Paragraph(_esc(
                f"{sugg.companion_name_en}  |  Row ratio: {sugg.row_ratio}  "
                f"|  +{sugg.revenue_uplift_percent:.0f}% estimated revenue "
                f"uplift"), S["ic_head"]))
            story.append(Paragraph(_esc(sugg.benefit_en), S["ic_detail"]))
            story.append(Spacer(1, 2 * mm))

    # Seasonal tips
    story.extend(_section("Seasonal Planting Tips"))
    for tip in r.seasonal_tips_en:
        story.append(Paragraph(f"- {_esc(tip)}", S["bullet"]))
    story.append(Spacer(1, 3 * mm))

    # Vertical farming
    story.extend(_section("Vertical Farming & Value Addition"))
    story.append(Paragraph(_esc(r.vertical_farming_en), S["body"]))

    # Disclaimer
    story.extend(_section("Disclaimer", C_MID_GRAY))
    story.append(Paragraph(_esc(
        "Generated by automated advisory system using MSP/FRP 2023-24 "
        "reference data. Does not account for micro-climate, pest pressure, "
        "or real-time markets. Verify with your local KVK before financial "
        "decisions."), S["body_xs"]))

    return story


# ── AI advisory section ────────────────────────────────────────────────────────

def _build_ai(advisory, lang="en", S=None):
    story = []
    if lang == "hi":
        story.extend(_section("AI-संचालित अतिरिक्त सलाह", C_AI_HEADER))
        story.append(Paragraph(_esc(
            "OpenAI GPT द्वारा संचालित। गणना किए गए डेटा पर आधारित।"),
            S["body_xs"]))
    else:
        story.extend(_section("AI-Powered Additional Advisory", C_AI_HEADER))
        story.append(Paragraph(_esc(
            "Powered by OpenAI GPT. Based on computed farm data only."),
            S["body_xs"]))
    story.append(Spacer(1, 1 * mm))

    # Split advisory into separate paragraphs per numbered point.
    # GPT often returns "...sentence. 2. Next point..." as one block.
    # We split on patterns like "1." "2." etc at the start or mid-text.
    import re
    chunks = re.split(r'(?=\b\d+\.\s)', advisory.strip())
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        # Further split on actual newlines within a chunk
        for line in chunk.split('\n'):
            line = line.strip()
            if line:
                story.append(Paragraph(_esc(line), S["body"]))
        story.append(Spacer(1, 2 * mm))

    return story


# ── Hindi section ──────────────────────────────────────────────────────────────

def _build_hi(r, farm_location, S):
    """Return flowables for the Hindi section (starts on new page)."""
    story = [PageBreak()]

    # Hindi header band
    hdr_p = Paragraph(
        f"<b>{_esc('हिंदी अनुभाग — किसान सलाहकार रिपोर्ट')}</b>",
        ParagraphStyle("_hi_hdr", fontName=_fb(), fontSize=13,
                        leading=18, textColor=C_WHITE))
    hdr_t = Table([[hdr_p]], colWidths=[USABLE_W])
    hdr_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_HINDI_HEADER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(hdr_t)
    story.append(Spacer(1, 3 * mm))

    # Hero band
    crop_line = f"{r.crop_name_hi}  |  {r.acreage:.1f} एकड़"
    if farm_location:
        crop_line += f"  |  {farm_location}"
    hero = [Paragraph(_esc(crop_line), S["hero"])]
    if r.soil_name_en:
        hero.append(Paragraph(
            _esc(f"मिट्टी: {r.soil_name_en}  |  जलवायु: {r.climate_zone}"),
            S["hero_sub"]))
    hero.append(_kpi("सकल आय:", f"Rs. {r.gross_revenue:,}"))
    hero.append(_kpi("कुल लागत:", f"Rs. {r.total_cost:,}", C_AMBER))
    mc = C_MID_GREEN if r.net_margin >= 0 else C_RED
    hero.append(_kpi("शुद्ध लाभ:", f"Rs. {r.net_margin:,}", mc))
    hero.append(_kpi("संभावित बचत:",
                      f"Rs. {r.total_reducible_cost:,}", C_MID_GREEN))
    story.append(_hero_band(hero))
    story.append(Spacer(1, 4 * mm))

    # Price info
    story.extend(_section("मूल्य जानकारी", C_HINDI_HEADER))
    story.append(Paragraph(
        _esc(f"मूल्य: Rs. {r.price_per_quintal:,}/क्विंटल") + "<br/>" +
        _esc(f"आधार: {_price_lbl(r.price_type, 'hi')}"), S["body"]))

    # Summary
    story.extend(_section("सारांश", C_HINDI_HEADER))
    narrative_hi = r.narrative_hi.replace(" मिट्टी मिट्टी ", " मिट्टी ")
    story.append(Paragraph(_esc(narrative_hi), S["body"]))

    if r.risk_flag:
        story.extend(_warning_band(
            "चेतावनी: शुद्ध मार्जिन Rs. 5,000/एकड़ से कम। "
            "तत्काल कदम उठाएं।"))

    # Cost table
    story.extend(_section("लागत विश्लेषण", C_HINDI_HEADER))
    story.append(_cost_table(r, use_hindi=True))
    story.append(Spacer(1, 2 * mm))

    # Tips
    story.extend(_section("लागत कटौती मार्गदर्शिका (पूर्ण विवरण)",
                           C_HINDI_HEADER))
    for i, item in enumerate(r.cost_items, 1):
        story.append(KeepTogether([
            Paragraph(_esc(f"{i}. {item.name_hi}"), S["tip_lbl"]),
            Paragraph(_esc(item.reduction_tip_hi), S["tip_body"]),
            Spacer(1, 1 * mm),
        ]))

    # Low-cost tips
    story.extend(_section("कम लागत और प्राचीन तकनीकें", C_HINDI_HEADER))
    for tip in r.low_cost_tips_hi:
        story.append(Paragraph(f"- {_esc(tip)}", S["bullet"]))
    story.append(Spacer(1, 3 * mm))

    # Intercropping
    if r.intercrop_suggestions:
        story.extend(_section("अंतरफसल सुझाव", C_HINDI_HEADER))
        for sugg in r.intercrop_suggestions:
            story.append(Paragraph(_esc(
                f"{sugg.companion_name_hi}  |  अनुपात: {sugg.row_ratio}  "
                f"|  +{sugg.revenue_uplift_percent:.0f}% अनुमानित राजस्व "
                f"वृद्धि"), S["ic_head"]))
            story.append(Paragraph(_esc(sugg.benefit_hi), S["ic_detail"]))
            story.append(Spacer(1, 2 * mm))

    # Seasonal tips
    story.extend(_section("मौसमी रोपण सुझाव", C_HINDI_HEADER))
    for tip in r.seasonal_tips_hi:
        story.append(Paragraph(f"- {_esc(tip)}", S["bullet"]))
    story.append(Spacer(1, 3 * mm))

    # Vertical farming
    story.extend(_section("ऊर्ध्वाधर खेती / मूल्य संवर्धन", C_HINDI_HEADER))
    story.append(Paragraph(_esc(r.vertical_farming_hi), S["body"]))

    # Disclaimer
    story.extend(_section("अस्वीकरण", C_MID_GRAY))
    story.append(Paragraph(_esc(
        "यह रिपोर्ट स्वचालित सलाहकार प्रणाली द्वारा तैयार की गई है। "
        "वित्तीय निर्णय लेने से पहले स्थानीय KVK से सत्यापित करें।"),
        S["body_xs"]))

    return story


# ── No-font fallback page ─────────────────────────────────────────────────────

def _build_no_font():
    """Fallback page when Noto Sans Devanagari is not installed."""
    story = [PageBreak()]
    story.append(Paragraph(
        "<b>Hindi Section — Font Required</b>",
        ParagraphStyle("_nf_hdr", fontName="Helvetica-Bold", fontSize=13,
                        leading=16, textColor=C_HINDI_HEADER)))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "To enable the Hindi section:<br/><br/>"
        "1. Download NotoSansDevanagari-Regular.ttf and "
        "NotoSansDevanagari-Bold.ttf from "
        "https://fonts.google.com/noto/specimen/Noto+Sans+Devanagari"
        "<br/>"
        "2. Place them in the fonts/ folder of your GitHub repository<br/>"
        "3. Redeploy the app<br/><br/>"
        "Hindi is fully available in the Streamlit web interface already.",
        ParagraphStyle("_nf_body", fontName="Helvetica", fontSize=10,
                        leading=14, textColor=C_DARK_GRAY)))
    return story


# ── Public entry point ─────────────────────────────────────────────────────────

def generate_pdf(
    result: RecommendationResult,
    farm_location: str = "",
    llm_advisory_en: str = "",
    llm_advisory_hi: str = "",
) -> bytes:
    """Generate bilingual PDF report. Drop-in replacement for V3.

    Returns raw PDF bytes suitable for st.download_button or HTTP response.
    """
    _register_fonts()
    S = _make_styles()

    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=L_MARGIN,
        rightMargin=R_MARGIN,
        topMargin=T_MARGIN,
        bottomMargin=B_MARGIN,
        title="Farmer Revenue Optimizer — Crop Advisory Report",
        author="Farmer Revenue Optimizer",
    )
    frame = Frame(
        L_MARGIN, B_MARGIN,
        USABLE_W, PAGE_H - T_MARGIN - B_MARGIN,
        id="main",
    )
    doc.addPageTemplates([
        PageTemplate(id="all", frames=[frame],
                     onPage=_draw_header_footer),
    ])

    # Assemble story
    story = _build_en(result, farm_location, S)

    if llm_advisory_en and llm_advisory_en.strip():
        story.extend(_build_ai(llm_advisory_en.strip(), lang="en", S=S))

    if _has_noto:
        story.extend(_build_hi(result, farm_location, S))
        if llm_advisory_hi and llm_advisory_hi.strip():
            story.extend(_build_ai(llm_advisory_hi.strip(), lang="hi", S=S))
    else:
        story.extend(_build_no_font())

    doc.build(story)
    return buf.getvalue()
