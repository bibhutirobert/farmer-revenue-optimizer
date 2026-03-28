"""
PDF Report Generator — V3 (stable rewrite)

Design rules that prevent all "not enough horizontal space" crashes:
1. NEVER use set_xy(0, y) — always set_x(left_margin) or set_x(18)
2. NEVER mix cell() and multi_cell() with cursor-position dependencies
3. ALL text output uses multi_cell() — consistent, safe, never crashes
4. Hero box uses ln/set_x flow only — no rect-then-set_xy tricks
5. KPI rows: label + value on same multi_cell line, tab-aligned with spaces
6. Cost table: pure cell() only, widths sum exactly to 180mm
"""

import os
from fpdf import FPDF
from typing import Optional
from core.models import RecommendationResult

ROOT_DIR         = os.path.dirname(os.path.dirname(__file__))
FONTS_DIR        = os.path.join(ROOT_DIR, "fonts")
DEJAVU_PATH      = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
DEJAVU_BOLD_PATH = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")

# Colours
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

L_MARGIN = 15   # left margin mm
R_MARGIN = 15   # right margin mm
PAGE_W   = 210  # A4 width mm
CONTENT_W = PAGE_W - L_MARGIN - R_MARGIN  # 180mm usable


def _has_devanagari_font() -> bool:
    return os.path.exists(DEJAVU_PATH)


class FarmReport(FPDF):

    def __init__(self, result: RecommendationResult, farm_location: str = ""):
        super().__init__()
        self.result        = result
        self.farm_location = farm_location
        self._unicode_loaded = False
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(L_MARGIN, L_MARGIN, R_MARGIN)

        if _has_devanagari_font():
            try:
                self.add_font("DejaVu", "", DEJAVU_PATH, uni=True)
                bold = DEJAVU_BOLD_PATH if os.path.exists(DEJAVU_BOLD_PATH) else DEJAVU_PATH
                self.add_font("DejaVu", "B", bold, uni=True)
                self._unicode_loaded = True
            except Exception:
                self._unicode_loaded = False

    # ── Font & safety helpers ──────────────────────────────────────────────────

    def _font(self, style: str = "", size: int = 10):
        if self._unicode_loaded:
            self.set_font("DejaVu", style, size)
        else:
            self.set_font("Helvetica", style, size)

    def _safe(self, text: str) -> str:
        """Replace Unicode chars that crash Helvetica. No-op when DejaVu loaded."""
        if self._unicode_loaded:
            return text
        replacements = {
            "\u2014": "-", "\u2013": "-",
            "\u2018": "'", "\u2019": "'",
            "\u201c": '"', "\u201d": '"',
            "\u2022": "-", "\u20b9": "Rs.",
            "\u2026": "...", "\u00d7": "x",
        }
        for ch, rep in replacements.items():
            text = text.replace(ch, rep)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    def _ml(self, text: str, line_h: float = 6, size: int = 10,
            style: str = "", color=None, indent: int = 0):
        """
        Safe multi_cell wrapper. Always resets X to left_margin + indent first.
        This is the ONLY text-output method used throughout — no raw cell() for body text.
        """
        self._font(style, size)
        if color:
            self.set_text_color(*color)
        else:
            self.set_text_color(*COLOR_DARK_GRAY)
        self.set_x(L_MARGIN + indent)
        self.multi_cell(CONTENT_W - indent, line_h, self._safe(text))

    # ── Page chrome ────────────────────────────────────────────────────────────

    def header(self):
        self.set_fill_color(*COLOR_MID_GREEN)
        self.rect(0, 0, PAGE_W, 22, "F")
        self.set_text_color(*COLOR_WHITE)
        self.set_font("Helvetica", "B", 13)
        self.set_xy(L_MARGIN, 6)
        self.cell(CONTENT_W, 10,
                  "Farmer Revenue Optimizer  |  Crop Advisory Report",
                  align="C")
        self.set_text_color(*COLOR_DARK_GRAY)
        self.ln(16)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*COLOR_MID_GRAY)
        self.set_x(L_MARGIN)
        self.cell(CONTENT_W, 10,
                  f"Page {self.page_no()} | Advisory only. Verify with local KVK.",
                  align="C")

    # ── Layout helpers ─────────────────────────────────────────────────────────

    def section_title(self, title: str, color=COLOR_DARK_GREEN):
        self.ln(4)
        self.set_fill_color(*color)
        self.set_text_color(*COLOR_WHITE)
        self._font("B", 11)
        self.set_x(L_MARGIN)
        self.cell(CONTENT_W, 8, self._safe(f"  {title}"), ln=True, fill=True)
        self.set_text_color(*COLOR_DARK_GRAY)
        self.ln(2)

    def kpi_line(self, label: str, value: str, color=COLOR_DARK_GREEN):
        """
        Single KPI line. Uses multi_cell so both Latin and Devanagari render safely.
        Format: "Label:                Rs. X,XXX"
        Padding with spaces approximates right-alignment without cell() cursor games.
        """
        self._font("B", 11)
        self.set_text_color(*color)
        self.set_x(L_MARGIN + 3)
        # Pad label to fixed width so value appears right-aligned visually
        line = f"{label:<28}{value}"
        self.multi_cell(CONTENT_W - 6, 8, self._safe(line))
        self.set_text_color(*COLOR_DARK_GRAY)

    def bullet(self, text: str):
        self._font("", 9)
        self.set_text_color(*COLOR_DARK_GRAY)
        self.set_x(L_MARGIN + 4)
        self.multi_cell(CONTENT_W - 4, 5.5, self._safe(f"- {text}"))

    def colored_band(self, color, height: int = 10):
        """Draw a full-width coloured band at current Y."""
        self.set_fill_color(*color)
        self.rect(0, self.get_y(), PAGE_W, height, "F")

    # ── Cost table ─────────────────────────────────────────────────────────────

    def cost_table(self, use_hindi: bool = False):
        """
        Pure cell() cost table. Widths sum to exactly 180mm (CONTENT_W).
        Tips truncated to fit — full tips are in the bullets section below.
        """
        if use_hindi:
            headers = ["लागत श्रेणी", "कुल (Rs.)", "बचत", "सुझाव (नीचे पूर्ण)"]
        else:
            headers = ["Cost Category", "Total (Rs.)", "Save Up To",
                       "Tip (full detail in bullets below)"]

        col_w = [50, 30, 30, 70]   # sum = 180 = CONTENT_W exactly
        row_h = 7

        self.set_x(L_MARGIN)
        self._font("B", 8)
        self.set_fill_color(*COLOR_TABLE_HEADER)
        self.set_text_color(*COLOR_WHITE)
        self.set_draw_color(*COLOR_BORDER)
        for i, h in enumerate(headers):
            self.cell(col_w[i], row_h, self._safe(h), border=1, fill=True)
        self.ln()

        alt = False
        for item in self.result.cost_items:
            self.set_fill_color(*(COLOR_TABLE_ALT if alt else COLOR_WHITE))
            alt = not alt
            name = item.name_hi if use_hindi else item.name_en
            tip  = item.reduction_tip_hi if use_hindi else item.reduction_tip_en
            tip_short = self._safe(
                tip[:56] + "..." if len(tip) > 56 else tip
            )
            self.set_x(L_MARGIN)
            self._font("B", 8)
            self.set_text_color(*COLOR_DARK_GRAY)
            self.cell(col_w[0], row_h, self._safe(name), border=1, fill=True)
            self._font("", 8)
            self.cell(col_w[1], row_h, f"Rs. {item.amount:,}",
                      border=1, fill=True, align="R")
            self.set_text_color(*COLOR_MID_GREEN)
            self.cell(col_w[2], row_h, f"Rs. {item.reducible_by:,}",
                      border=1, fill=True, align="R")
            self.set_text_color(*COLOR_DARK_GRAY)
            self.cell(col_w[3], row_h, tip_short, border=1, fill=True)
            self.ln()

        # Totals
        self.set_x(L_MARGIN)
        self._font("B", 9)
        self.set_fill_color(*COLOR_LIGHT_GREEN_BG)
        total_label = "कुल" if use_hindi else "TOTAL"
        self.cell(col_w[0], row_h, total_label, border=1, fill=True)
        self.cell(col_w[1], row_h, f"Rs. {self.result.total_cost:,}",
                  border=1, fill=True, align="R")
        self.set_text_color(*COLOR_MID_GREEN)
        self.cell(col_w[2], row_h, f"Rs. {self.result.total_reducible_cost:,}",
                  border=1, fill=True, align="R")
        self.set_text_color(*COLOR_DARK_GRAY)
        apply_all = "सभी सुझाव अपनाएं" if use_hindi else "Apply all tips above"
        self.cell(col_w[3], row_h, apply_all, border=1, fill=True)
        self.ln()


# ── Price label helper ─────────────────────────────────────────────────────────

def _price_label(price_type: str, lang: str = "en") -> str:
    if lang == "hi":
        return {
            "msp":     "MSP 2023-24 (सरकारी न्यूनतम समर्थन मूल्य)",
            "frp":     "FRP 2023-24 (सरकारी उचित एवं लाभकारी मूल्य)",
            "market":  "बाजार औसत (रूढ़िवादी अनुमान)",
            "default": "संदर्भ मूल्य (MSP/FRP 2023-24)",
        }.get(price_type, price_type.upper())
    return {
        "msp":     "MSP 2023-24 (Govt. Minimum Support Price)",
        "frp":     "FRP 2023-24 (Govt. Fair & Remunerative Price)",
        "market":  "Market Average (conservative — actual may vary)",
        "default": "Reference price (MSP/FRP 2023-24)",
    }.get(price_type, price_type.upper())


# ── English section ────────────────────────────────────────────────────────────

def _english_section(pdf: FarmReport, r: RecommendationResult,
                     farm_location: str):
    pdf.add_page()

    # Hero band
    pdf.set_fill_color(*COLOR_LIGHT_GREEN_BG)
    band_y = pdf.get_y()
    pdf.rect(L_MARGIN, band_y, CONTENT_W, 58, "F")
    pdf.ln(3)

    # Crop + location
    pdf._ml(f"{r.crop_name_en}  |  {r.acreage:.1f} acres",
            line_h=9, size=13, style="B", color=COLOR_MID_GREEN, indent=3)
    if farm_location:
        pdf._ml(farm_location, line_h=6, size=9,
                color=COLOR_MID_GRAY, indent=3)
    if r.soil_name_en:
        pdf._ml(f"Soil: {r.soil_name_en}  |  Climate: {r.climate_zone}",
                line_h=6, size=9, color=COLOR_MID_GRAY, indent=3)
    pdf.ln(1)

    # KPI lines
    pdf.kpi_line("Gross Revenue:",    f"Rs. {r.gross_revenue:,}")
    pdf.kpi_line("Total Input Cost:", f"Rs. {r.total_cost:,}",
                 color=COLOR_AMBER)
    mc = COLOR_MID_GREEN if r.net_margin >= 0 else COLOR_RED
    pdf.kpi_line("Net Margin:",       f"Rs. {r.net_margin:,}", color=mc)
    pdf.kpi_line("Potential Savings:", f"Rs. {r.total_reducible_cost:,}",
                 color=COLOR_MID_GREEN)
    pdf.ln(4)

    # Price info
    pdf.section_title("Price Information")
    pdf._ml(
        f"Price used: Rs. {r.price_per_quintal:,} per quintal\n"
        f"Basis: {_price_label(r.price_type, 'en')}",
        line_h=6
    )

    # Summary
    pdf.section_title("Summary")
    narrative = r.narrative_en.replace(" soil soil ", " soil ").replace(
        " Soil soil ", " Soil ")
    pdf._ml(narrative, line_h=6)

    if r.risk_flag:
        pdf.ln(2)
        pdf.colored_band(COLOR_RED, 9)
        pdf.set_text_color(*COLOR_WHITE)
        pdf._font("B", 10)
        pdf.set_x(L_MARGIN + 2)
        pdf.multi_cell(CONTENT_W - 2, 9,
            "WARNING: Net margin below Rs. 5,000/acre. Urgent action required.")
        pdf.set_text_color(*COLOR_DARK_GRAY)
        pdf.ln(2)

    # Cost table
    pdf.section_title("Cost Breakdown & Reduction Opportunities")
    pdf._ml("Full tip text is in the 'Low-Cost Techniques' section below the table.",
            line_h=5, size=8, color=COLOR_MID_GRAY)
    pdf.ln(1)
    pdf.cost_table(use_hindi=False)
    pdf.ln(2)

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
                line_h=6, style="B", color=COLOR_MID_GREEN
            )
            pdf._ml(sugg.benefit_en, line_h=5, size=9, indent=4)
            pdf.ln(2)

    # Seasonal tips
    pdf.section_title("Seasonal Planting Tips")
    for tip in r.seasonal_tips_en:
        pdf.bullet(tip)
    pdf.ln(3)

    # Vertical farming
    pdf.section_title("Vertical Farming & Value Addition")
    pdf._ml(r.vertical_farming_en, line_h=6)

    # Disclaimer
    pdf.section_title("Disclaimer", color=COLOR_MID_GRAY)
    pdf._ml(
        "Generated by automated advisory system using MSP/FRP 2023-24 reference data. "
        "Does not account for micro-climate, local pest pressure, or real-time markets. "
        "Verify with your local Krishi Vigyan Kendra (KVK) before financial decisions.",
        line_h=5, size=8, color=COLOR_MID_GRAY
    )


# ── LLM advisory section ───────────────────────────────────────────────────────

def _llm_section(pdf: FarmReport, advisory: str, lang: str = "en"):
    if lang == "hi":
        pdf.section_title("AI-संचालित अतिरिक्त सलाह", color=COLOR_AI_HEADER)
        pdf._ml(
            "OpenAI GPT द्वारा संचालित। आपके गणना किए गए खेत डेटा पर आधारित। "
            "संख्याएं और जोखिम वर्गीकरण इंजन द्वारा निर्धारित हैं।",
            line_h=5, size=8, color=COLOR_MID_GRAY
        )
    else:
        pdf.section_title("AI-Powered Additional Advisory", color=COLOR_AI_HEADER)
        pdf._ml(
            "Powered by OpenAI GPT. Based on computed farm data only. "
            "Numbers and risk classifications are determined by the rule engine.",
            line_h=5, size=8, color=COLOR_MID_GRAY
        )
    pdf.ln(1)
    pdf._ml(advisory, line_h=6)


# ── Hindi section ──────────────────────────────────────────────────────────────

def _hindi_section(pdf: FarmReport, r: RecommendationResult,
                   farm_location: str):
    pdf.add_page()

    # Hindi section header band — use set_x(L_MARGIN) not set_xy(0, ...)
    pdf.colored_band(COLOR_HINDI_HEADER, 12)
    pdf._font("B", 13)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_x(L_MARGIN)
    pdf.multi_cell(CONTENT_W, 12,
                   "हिंदी अनुभाग — किसान सलाहकार रिपोर्ट")
    pdf.set_text_color(*COLOR_DARK_GRAY)
    pdf.ln(3)

    # Hero band
    pdf.set_fill_color(*COLOR_LIGHT_GREEN_BG)
    pdf.rect(L_MARGIN, pdf.get_y(), CONTENT_W, 58, "F")
    pdf.ln(3)

    # Crop + location
    crop_line = f"{r.crop_name_hi}  |  {r.acreage:.1f} एकड़"
    if farm_location:
        crop_line += f"  |  {farm_location}"
    pdf._ml(crop_line, line_h=9, size=13, style="B",
            color=COLOR_MID_GREEN, indent=3)
    if r.soil_name_en:
        pdf._ml(f"मिट्टी: {r.soil_name_en}  |  जलवायु: {r.climate_zone}",
                line_h=6, size=9, color=COLOR_MID_GRAY, indent=3)
    pdf.ln(1)

    # KPI lines — use kpi_line (multi_cell based, safe for Devanagari)
    pdf.kpi_line("सकल आय:",      f"Rs. {r.gross_revenue:,}")
    pdf.kpi_line("कुल लागत:",    f"Rs. {r.total_cost:,}", color=COLOR_AMBER)
    mc = COLOR_MID_GREEN if r.net_margin >= 0 else COLOR_RED
    pdf.kpi_line("शुद्ध लाभ:",   f"Rs. {r.net_margin:,}", color=mc)
    pdf.kpi_line("संभावित बचत:", f"Rs. {r.total_reducible_cost:,}",
                 color=COLOR_MID_GREEN)
    pdf.ln(4)

    # Price info
    pdf.section_title("मूल्य जानकारी", color=COLOR_HINDI_HEADER)
    pdf._ml(
        f"उपयोग किया गया मूल्य: Rs. {r.price_per_quintal:,} प्रति क्विंटल\n"
        f"आधार: {_price_label(r.price_type, 'hi')}",
        line_h=6
    )

    # Summary
    pdf.section_title("सारांश", color=COLOR_HINDI_HEADER)
    narrative_hi = r.narrative_hi.replace(" मिट्टी मिट्टी ", " मिट्टी ")
    pdf._ml(narrative_hi, line_h=6)

    if r.risk_flag:
        pdf.ln(2)
        pdf.colored_band(COLOR_RED, 9)
        pdf.set_text_color(*COLOR_WHITE)
        pdf._font("B", 10)
        pdf.set_x(L_MARGIN + 2)
        pdf.multi_cell(CONTENT_W - 2, 9,
            "चेतावनी: शुद्ध मार्जिन Rs. 5,000/एकड़ से कम। तत्काल कदम उठाएं।")
        pdf.set_text_color(*COLOR_DARK_GRAY)
        pdf.ln(2)

    # Cost table
    pdf.section_title("लागत विश्लेषण और बचत के अवसर", color=COLOR_HINDI_HEADER)
    pdf._ml("पूर्ण सुझाव नीचे 'कम लागत तकनीकें' अनुभाग में हैं।",
            line_h=5, size=8, color=COLOR_MID_GRAY)
    pdf.ln(1)
    pdf.cost_table(use_hindi=True)
    pdf.ln(2)

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
                line_h=6, style="B", color=COLOR_MID_GREEN
            )
            pdf._ml(sugg.benefit_hi, line_h=5, size=9, indent=4)
            pdf.ln(2)

    # Seasonal tips
    pdf.section_title("मौसमी रोपण सुझाव", color=COLOR_HINDI_HEADER)
    for tip in r.seasonal_tips_hi:
        pdf.bullet(tip)
    pdf.ln(3)

    # Vertical farming
    pdf.section_title("ऊर्ध्वाधर खेती / मूल्य संवर्धन", color=COLOR_HINDI_HEADER)
    pdf._ml(r.vertical_farming_hi, line_h=6)

    # Disclaimer
    pdf.section_title("अस्वीकरण", color=COLOR_MID_GRAY)
    pdf._ml(
        "यह रिपोर्ट स्वचालित सलाहकार प्रणाली द्वारा MSP/FRP 2023-24 संदर्भ डेटा "
        "का उपयोग करके तैयार की गई है। वित्तीय निर्णय लेने से पहले अपने स्थानीय "
        "कृषि विभाग या KVK से सत्यापित करें।",
        line_h=5, size=8, color=COLOR_MID_GRAY
    )


# ── Public entry point ─────────────────────────────────────────────────────────

def generate_pdf(
    result: RecommendationResult,
    farm_location: str = "",
    llm_advisory_en: str = "",
    llm_advisory_hi: str = "",
) -> bytes:
    """
    Generate complete dual-language PDF report.

    Args:
        result          : RecommendationResult from the engine
        farm_location   : human-readable location string
        llm_advisory_en : AI advisory in English — included if non-empty
        llm_advisory_hi : AI advisory in Hindi — included if non-empty

    Always produces English section.
    Appends Hindi section if DejaVuSans.ttf is in fonts/.
    Returns bytes for st.download_button.
    """
    pdf = FarmReport(result, farm_location)

    _english_section(pdf, result, farm_location)

    if llm_advisory_en and llm_advisory_en.strip():
        _llm_section(pdf, llm_advisory_en.strip(), lang="en")

    if pdf._unicode_loaded:
        _hindi_section(pdf, result, farm_location)
        if llm_advisory_hi and llm_advisory_hi.strip():
            _llm_section(pdf, llm_advisory_hi.strip(), lang="hi")
    else:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*COLOR_HINDI_HEADER)
        pdf.set_x(L_MARGIN)
        pdf.multi_cell(CONTENT_W, 10, "Hindi Section Not Available in This Build")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*COLOR_DARK_GRAY)
        pdf.set_x(L_MARGIN)
        pdf.multi_cell(CONTENT_W, 6,
            "To enable Hindi PDF:\n"
            "1. Download DejaVuSans.ttf from https://dejavu-fonts.github.io/\n"
            "2. Place it in the fonts/ directory of this repository\n"
            "3. Redeploy the app\n\n"
            "Hindi is fully available in the Streamlit web interface already."
        )

    return bytes(pdf.output())
