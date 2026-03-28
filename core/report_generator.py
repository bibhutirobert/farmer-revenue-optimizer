"""
PDF Report Generator — V3 Final
=================================
Design principles (no more horizontal space crashes):
  1. One text method: _ml(). Always resets X before writing. No cursor assumptions.
  2. Cost table: 3 columns only (Category | Total | Save Up To). No tip column.
     Full tips printed as numbered list below the table — better UX, zero crashes.
  3. No set_xy(0, y) anywhere in executable code.
  4. No saved cursor coordinates across multi_cell() calls.
  5. Hindi KPI lines use kpi_line() which is multi_cell-based — safe for Devanagari.
"""

import os
from fpdf import FPDF
from typing import Optional
from core.models import RecommendationResult

ROOT_DIR         = os.path.dirname(os.path.dirname(__file__))
FONTS_DIR        = os.path.join(ROOT_DIR, "fonts")
DEJAVU_PATH      = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
DEJAVU_BOLD_PATH = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")

COLOR_MID_GREEN      = (46, 125, 50)
COLOR_DARK_GREEN     = (30, 100, 30)
COLOR_LIGHT_GREEN_BG = (232, 245, 233)
COLOR_AMBER          = (255, 143, 0)
COLOR_RED            = (198, 40, 40)
COLOR_WHITE          = (255, 255, 255)
COLOR_DARK_GRAY      = (40, 40, 40)
COLOR_MID_GRAY       = (100, 100, 100)
COLOR_TABLE_HEADER   = (27, 94, 32)
COLOR_TABLE_ALT      = (240, 248, 240)
COLOR_BORDER         = (180, 180, 180)
COLOR_HINDI_HEADER   = (13, 71, 161)
COLOR_AI_HEADER      = (74, 20, 140)

L_MARGIN  = 15
R_MARGIN  = 15
PAGE_W    = 210
USABLE_W  = PAGE_W - L_MARGIN - R_MARGIN  # 180mm


def _has_font() -> bool:
    return os.path.exists(DEJAVU_PATH)


class FarmReport(FPDF):

    def __init__(self, result: RecommendationResult, farm_location: str = ""):
        super().__init__()
        self.result          = result
        self.farm_location   = farm_location
        self._unicode_loaded = False
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(L_MARGIN, L_MARGIN, R_MARGIN)

        if _has_font():
            try:
                self.add_font("DejaVu", "", DEJAVU_PATH, uni=True)
                bold = DEJAVU_BOLD_PATH if os.path.exists(DEJAVU_BOLD_PATH) else DEJAVU_PATH
                self.add_font("DejaVu", "B", bold, uni=True)
                self._unicode_loaded = True
            except Exception:
                self._unicode_loaded = False

    # ── Core helpers ───────────────────────────────────────────────────────────

    def _f(self, style: str = "", size: int = 10):
        """Set font — DejaVu when available, Helvetica otherwise."""
        self.set_font("DejaVu" if self._unicode_loaded else "Helvetica", style, size)

    def _s(self, text: str) -> str:
        """Sanitise for Helvetica. No-op when DejaVu loaded."""
        if self._unicode_loaded:
            return text
        for ch, rep in {
            "\u2014": "-", "\u2013": "-",
            "\u2018": "'", "\u2019": "'",
            "\u201c": '"', "\u201d": '"',
            "\u2022": "-", "\u20b9": "Rs.",
            "\u2026": "...",
        }.items():
            text = text.replace(ch, rep)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    def _ml(self, text: str, lh: float = 6, size: int = 10,
            style: str = "", color=None, indent: int = 0):
        """
        THE only text-output method. Always resets X first.
        Safe regardless of what happened before.
        """
        self._f(style, size)
        self.set_text_color(*(color or COLOR_DARK_GRAY))
        self.set_x(L_MARGIN + indent)
        self.multi_cell(USABLE_W - indent, lh, self._s(text))

    # ── Page chrome ────────────────────────────────────────────────────────────

    def header(self):
        self.set_fill_color(*COLOR_MID_GREEN)
        self.rect(0, 0, PAGE_W, 22, "F")
        self.set_text_color(*COLOR_WHITE)
        self.set_font("Helvetica", "B", 13)
        self.set_x(L_MARGIN)
        self.cell(USABLE_W, 16,
                  "Farmer Revenue Optimizer  |  Crop Advisory Report",
                  align="C")
        self.ln(6)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*COLOR_MID_GRAY)
        self.set_x(L_MARGIN)
        self.cell(USABLE_W, 10,
                  f"Page {self.page_no()} | Advisory only. Verify with local KVK.",
                  align="C")

    # ── Layout primitives ──────────────────────────────────────────────────────

    def section_title(self, title: str, color=COLOR_DARK_GREEN):
        self.ln(4)
        self.set_fill_color(*color)
        self.set_text_color(*COLOR_WHITE)
        self._f("B", 11)
        self.set_x(L_MARGIN)
        self.cell(USABLE_W, 8, self._s(f"  {title}"), ln=True, fill=True)
        self.ln(2)

    def kpi_line(self, label: str, value: str, color=COLOR_DARK_GREEN):
        """KPI row using multi_cell — safe for both Latin and Devanagari."""
        self._f("B", 11)
        self.set_text_color(*color)
        self.set_x(L_MARGIN + 3)
        self.multi_cell(USABLE_W - 6, 8,
                        self._s(f"{label:<26}{value}"))

    def bullet(self, text: str):
        self._f("", 9)
        self.set_text_color(*COLOR_DARK_GRAY)
        self.set_x(L_MARGIN + 4)
        self.multi_cell(USABLE_W - 4, 5.5, self._s(f"- {text}"))

    def numbered_tip(self, n: int, label: str, tip: str):
        """Numbered cost-reduction tip. set_x before every write."""
        # Write label + tip as one multi_cell block to avoid
        # label orphaning at page breaks
        combined = self._s(f"{n}. {label}\n    {tip}")
        self._f("B", 9)
        self.set_text_color(*COLOR_MID_GREEN)
        self.set_x(L_MARGIN + 2)
        self.multi_cell(USABLE_W - 2, 5.5,
                        self._s(f"{n}. {label}"))
        self._f("", 9)
        self.set_text_color(*COLOR_DARK_GRAY)
        self.set_x(L_MARGIN + 6)
        self.multi_cell(USABLE_W - 6, 5.5, self._s(tip))
        self.ln(1)

    def band(self, color, h: int = 10):
        """Full-width colour band at current Y."""
        self.set_fill_color(*color)
        self.rect(L_MARGIN, self.get_y(), USABLE_W, h, "F")

    # ── Cost table (3 columns — no tip column, no crashes) ────────────────────

    def cost_table(self, use_hindi: bool = False):
        """
        3-column table: Category | Total | Save Up To
        Full tips are printed as numbered items in the section below.
        3 columns with cell() only = zero crash risk.
        """
        if use_hindi:
            headers = ["लागत श्रेणी", "कुल (Rs.)", "बचत संभव (Rs.)"]
        else:
            headers = ["Cost Category", "Total (Rs.)", "Save Up To (Rs.)"]

        # Widths sum to USABLE_W = 180
        col_w  = [80, 50, 50]
        row_h  = 7

        self.set_x(L_MARGIN)
        self._f("B", 9)
        self.set_fill_color(*COLOR_TABLE_HEADER)
        self.set_text_color(*COLOR_WHITE)
        self.set_draw_color(*COLOR_BORDER)
        for i, h in enumerate(headers):
            self.cell(col_w[i], row_h, self._s(h), border=1, fill=True,
                      align="C")
        self.ln()

        alt = False
        for item in self.result.cost_items:
            self.set_fill_color(*(COLOR_TABLE_ALT if alt else COLOR_WHITE))
            alt = not alt
            name = item.name_hi if use_hindi else item.name_en
            self.set_x(L_MARGIN)
            self._f("B", 9)
            self.set_text_color(*COLOR_DARK_GRAY)
            self.cell(col_w[0], row_h, self._s(name), border=1, fill=True)
            self._f("", 9)
            self.cell(col_w[1], row_h, f"Rs. {item.amount:,}",
                      border=1, fill=True, align="R")
            self.set_text_color(*COLOR_MID_GREEN)
            self.cell(col_w[2], row_h, f"Rs. {item.reducible_by:,}",
                      border=1, fill=True, align="R")
            self.ln()

        self.set_x(L_MARGIN)
        self._f("B", 9)
        self.set_fill_color(*COLOR_LIGHT_GREEN_BG)
        self.set_text_color(*COLOR_DARK_GRAY)
        total_lbl = "कुल" if use_hindi else "TOTAL"
        self.cell(col_w[0], row_h, total_lbl, border=1, fill=True)
        self.cell(col_w[1], row_h, f"Rs. {self.result.total_cost:,}",
                  border=1, fill=True, align="R")
        self.set_text_color(*COLOR_MID_GREEN)
        self.cell(col_w[2], row_h,
                  f"Rs. {self.result.total_reducible_cost:,}",
                  border=1, fill=True, align="R")
        self.ln()


# ── Price label ────────────────────────────────────────────────────────────────

def _price_lbl(price_type: str, lang: str = "en") -> str:
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

def _en(pdf: FarmReport, r: RecommendationResult, farm_location: str):
    pdf.add_page()

    # Hero band
    pdf.set_fill_color(*COLOR_LIGHT_GREEN_BG)
    pdf.rect(L_MARGIN, pdf.get_y(), USABLE_W, 54, "F")
    pdf.ln(3)
    pdf._ml(f"{r.crop_name_en}  |  {r.acreage:.1f} acres",
            lh=9, size=13, style="B", color=COLOR_MID_GREEN, indent=3)
    if farm_location:
        pdf._ml(farm_location, lh=6, size=9, color=COLOR_MID_GRAY, indent=3)
    if r.soil_name_en:
        pdf._ml(f"Soil: {r.soil_name_en}  |  Climate: {r.climate_zone}",
                lh=6, size=9, color=COLOR_MID_GRAY, indent=3)
    pdf.ln(1)
    pdf.kpi_line("Gross Revenue:",     f"Rs. {r.gross_revenue:,}")
    pdf.kpi_line("Total Input Cost:",  f"Rs. {r.total_cost:,}", color=COLOR_AMBER)
    mc = COLOR_MID_GREEN if r.net_margin >= 0 else COLOR_RED
    pdf.kpi_line("Net Margin:",        f"Rs. {r.net_margin:,}", color=mc)
    pdf.kpi_line("Potential Savings:", f"Rs. {r.total_reducible_cost:,}",
                 color=COLOR_MID_GREEN)
    pdf.ln(4)

    # Price info
    pdf.section_title("Price Information")
    pdf._ml(f"Price: Rs. {r.price_per_quintal:,}/quintal\n"
            f"Basis: {_price_lbl(r.price_type, 'en')}", lh=6)

    # Summary
    pdf.section_title("Summary")
    narrative = r.narrative_en
    narrative = narrative.replace(" soil soil ", " soil ")
    narrative = narrative.replace(" Soil soil ", " Soil ")
    narrative = narrative.replace(" Soil Soil ", " Soil ")
    pdf._ml(narrative, lh=6)

    if r.risk_flag:
        pdf.ln(2)
        pdf.set_fill_color(*COLOR_RED)
        pdf.rect(L_MARGIN, pdf.get_y(), USABLE_W, 9, "F")
        pdf._f("B", 10)
        pdf.set_text_color(*COLOR_WHITE)
        pdf.set_x(L_MARGIN + 2)
        pdf.multi_cell(USABLE_W - 2, 9,
            "WARNING: Net margin below Rs. 5,000/acre. Urgent action required.")
        pdf.set_text_color(*COLOR_DARK_GRAY)
        pdf.ln(2)

    # Cost table
    pdf.section_title("Cost Breakdown")
    pdf.cost_table(use_hindi=False)
    pdf.ln(2)

    # Full tips numbered below table
    pdf.section_title("Cost Reduction Guide (Full Detail)")
    for i, item in enumerate(r.cost_items, 1):
        pdf.numbered_tip(i, item.name_en, item.reduction_tip_en)
    pdf.ln(1)

    # Low-cost tips
    pdf.section_title("Low-Cost & Ancient Farming Techniques")
    for tip in r.low_cost_tips_en:
        pdf.bullet(tip)
    pdf.ln(3)

    # Intercropping
    if r.intercrop_suggestions:
        pdf.section_title("Intercropping Opportunities")
        for sugg in r.intercrop_suggestions:
            pdf._ml(
                f"{sugg.companion_name_en}  |  Row ratio: {sugg.row_ratio}  "
                f"|  +{sugg.revenue_uplift_percent:.0f}% estimated revenue uplift",
                lh=6, style="B", color=COLOR_MID_GREEN)
            pdf._ml(sugg.benefit_en, lh=5, size=9, indent=4)
            pdf.ln(2)

    # Seasonal tips
    pdf.section_title("Seasonal Planting Tips")
    for tip in r.seasonal_tips_en:
        pdf.bullet(tip)
    pdf.ln(3)

    # Vertical farming
    pdf.section_title("Vertical Farming & Value Addition")
    pdf._ml(r.vertical_farming_en, lh=6)

    # Disclaimer
    pdf.section_title("Disclaimer", color=COLOR_MID_GRAY)
    pdf._ml(
        "Generated by automated advisory system using MSP/FRP 2023-24 reference data. "
        "Does not account for micro-climate, pest pressure, or real-time markets. "
        "Verify with your local KVK before financial decisions.",
        lh=5, size=8, color=COLOR_MID_GRAY)


# ── AI advisory section ────────────────────────────────────────────────────────

def _ai(pdf: FarmReport, advisory: str, lang: str = "en"):
    if lang == "hi":
        pdf.section_title("AI-संचालित अतिरिक्त सलाह", color=COLOR_AI_HEADER)
        pdf._ml("OpenAI GPT द्वारा संचालित। गणना किए गए डेटा पर आधारित।",
                lh=5, size=8, color=COLOR_MID_GRAY)
    else:
        pdf.section_title("AI-Powered Additional Advisory", color=COLOR_AI_HEADER)
        pdf._ml("Powered by OpenAI GPT. Based on computed farm data only.",
                lh=5, size=8, color=COLOR_MID_GRAY)
    pdf.ln(1)
    pdf._ml(advisory, lh=6)


# ── Hindi section ──────────────────────────────────────────────────────────────

def _hi(pdf: FarmReport, r: RecommendationResult, farm_location: str):
    pdf.add_page()

    # Hindi header band
    pdf.set_fill_color(*COLOR_HINDI_HEADER)
    pdf.rect(L_MARGIN, pdf.get_y(), USABLE_W, 11, "F")
    pdf._f("B", 13)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_x(L_MARGIN)
    pdf.multi_cell(USABLE_W, 11,
                   "हिंदी अनुभाग — किसान सलाहकार रिपोर्ट")
    pdf.set_text_color(*COLOR_DARK_GRAY)
    pdf.ln(3)

    # Hero band
    pdf.set_fill_color(*COLOR_LIGHT_GREEN_BG)
    pdf.rect(L_MARGIN, pdf.get_y(), USABLE_W, 54, "F")
    pdf.ln(3)
    crop_line = f"{r.crop_name_hi}  |  {r.acreage:.1f} एकड़"
    if farm_location:
        crop_line += f"  |  {farm_location}"
    pdf._ml(crop_line, lh=9, size=13, style="B",
            color=COLOR_MID_GREEN, indent=3)
    if r.soil_name_en:
        pdf._ml(f"मिट्टी: {r.soil_name_en}  |  जलवायु: {r.climate_zone}",
                lh=6, size=9, color=COLOR_MID_GRAY, indent=3)
    pdf.ln(1)
    pdf.kpi_line("सकल आय:",      f"Rs. {r.gross_revenue:,}")
    pdf.kpi_line("कुल लागत:",    f"Rs. {r.total_cost:,}", color=COLOR_AMBER)
    mc = COLOR_MID_GREEN if r.net_margin >= 0 else COLOR_RED
    pdf.kpi_line("शुद्ध लाभ:",   f"Rs. {r.net_margin:,}", color=mc)
    pdf.kpi_line("संभावित बचत:", f"Rs. {r.total_reducible_cost:,}",
                 color=COLOR_MID_GREEN)
    pdf.ln(4)

    # Price info
    pdf.section_title("मूल्य जानकारी", color=COLOR_HINDI_HEADER)
    pdf._ml(f"मूल्य: Rs. {r.price_per_quintal:,}/क्विंटल\n"
            f"आधार: {_price_lbl(r.price_type, 'hi')}", lh=6)

    # Summary
    pdf.section_title("सारांश", color=COLOR_HINDI_HEADER)
    narrative_hi = r.narrative_hi.replace(" मिट्टी मिट्टी ", " मिट्टी ")
    pdf._ml(narrative_hi, lh=6)

    if r.risk_flag:
        pdf.ln(2)
        pdf.set_fill_color(*COLOR_RED)
        pdf.rect(L_MARGIN, pdf.get_y(), USABLE_W, 9, "F")
        pdf._f("B", 10)
        pdf.set_text_color(*COLOR_WHITE)
        pdf.set_x(L_MARGIN + 2)
        pdf.multi_cell(USABLE_W - 2, 9,
            "चेतावनी: शुद्ध मार्जिन Rs. 5,000/एकड़ से कम। तत्काल कदम उठाएं।")
        pdf.set_text_color(*COLOR_DARK_GRAY)
        pdf.ln(2)

    # Cost table
    pdf.section_title("लागत विश्लेषण", color=COLOR_HINDI_HEADER)
    pdf.cost_table(use_hindi=True)
    pdf.ln(2)

    # Full tips numbered
    pdf.section_title("लागत कटौती मार्गदर्शिका (पूर्ण विवरण)",
                      color=COLOR_HINDI_HEADER)
    for i, item in enumerate(r.cost_items, 1):
        pdf.numbered_tip(i, item.name_hi, item.reduction_tip_hi)
    pdf.ln(1)

    # Low-cost tips
    pdf.section_title("कम लागत और प्राचीन तकनीकें", color=COLOR_HINDI_HEADER)
    for tip in r.low_cost_tips_hi:
        pdf.bullet(tip)
    pdf.ln(3)

    # Intercropping
    if r.intercrop_suggestions:
        pdf.section_title("अंतरफसल सुझाव", color=COLOR_HINDI_HEADER)
        for sugg in r.intercrop_suggestions:
            pdf._ml(
                f"{sugg.companion_name_hi}  |  अनुपात: {sugg.row_ratio}  "
                f"|  +{sugg.revenue_uplift_percent:.0f}% अनुमानित राजस्व वृद्धि",
                lh=6, style="B", color=COLOR_MID_GREEN)
            pdf._ml(sugg.benefit_hi, lh=5, size=9, indent=4)
            pdf.ln(2)

    # Seasonal tips
    pdf.section_title("मौसमी रोपण सुझाव", color=COLOR_HINDI_HEADER)
    for tip in r.seasonal_tips_hi:
        pdf.bullet(tip)
    pdf.ln(3)

    # Vertical farming
    pdf.section_title("ऊर्ध्वाधर खेती / मूल्य संवर्धन", color=COLOR_HINDI_HEADER)
    pdf._ml(r.vertical_farming_hi, lh=6)

    # Disclaimer
    pdf.section_title("अस्वीकरण", color=COLOR_MID_GRAY)
    pdf._ml(
        "यह रिपोर्ट स्वचालित सलाहकार प्रणाली द्वारा तैयार की गई है। "
        "वित्तीय निर्णय लेने से पहले स्थानीय KVK से सत्यापित करें।",
        lh=5, size=8, color=COLOR_MID_GRAY)


# ── No-font note page ──────────────────────────────────────────────────────────

def _no_font_page(pdf: FarmReport):
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*COLOR_HINDI_HEADER)
    pdf.set_x(L_MARGIN)
    pdf.multi_cell(USABLE_W, 10, "Hindi Section — Font Required")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*COLOR_DARK_GRAY)
    pdf.set_x(L_MARGIN)
    pdf.multi_cell(USABLE_W, 6,
        "To enable the Hindi section:\n\n"
        "1. Download DejaVuSans.ttf from https://dejavu-fonts.github.io/\n"
        "2. Place it in the fonts/ folder of your GitHub repository\n"
        "3. Redeploy the app\n\n"
        "Hindi is fully available in the Streamlit web interface already."
    )


# ── Public entry point ─────────────────────────────────────────────────────────

def generate_pdf(
    result: RecommendationResult,
    farm_location: str = "",
    llm_advisory_en: str = "",
    llm_advisory_hi: str = "",
) -> bytes:
    pdf = FarmReport(result, farm_location)
    _en(pdf, result, farm_location)
    if llm_advisory_en and llm_advisory_en.strip():
        _ai(pdf, llm_advisory_en.strip(), lang="en")
    if pdf._unicode_loaded:
        _hi(pdf, result, farm_location)
        if llm_advisory_hi and llm_advisory_hi.strip():
            _ai(pdf, llm_advisory_hi.strip(), lang="hi")
    else:
        _no_font_page(pdf)
    return bytes(pdf.output())
