"""
PDF Report Generator — V3 (fixed)
Dual-language: English section first, Hindi section second, one file.

Key fixes in this version:
- All Hindi text uses multi_cell() instead of cell() — fixes Devanagari rendering
- Cost table "How to Reduce" column uses multi_cell for full tip text
- Crop label truncation fixed — splits to two lines if too long
- "soil soil" double word fixed in narrative caller
- Price provenance shows human-readable label not raw metadata
- "+35% est" expanded to full phrase
- _safe() protects Helvetica fallback from Unicode crashes
"""

import os
from fpdf import FPDF
from typing import Optional
from core.models import RecommendationResult

ROOT_DIR    = os.path.dirname(os.path.dirname(__file__))
FONTS_DIR   = os.path.join(ROOT_DIR, "fonts")
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


def _has_devanagari_font() -> bool:
    return os.path.exists(DEJAVU_PATH)


class FarmReport(FPDF):
    def __init__(self, result: RecommendationResult, farm_location: str = ""):
        super().__init__()
        self.result        = result
        self.farm_location = farm_location
        self._unicode_loaded = False
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 15, 15)

        if _has_devanagari_font():
            try:
                self.add_font("DejaVu", "",  DEJAVU_PATH, uni=True)
                bold_path = DEJAVU_BOLD_PATH if os.path.exists(DEJAVU_BOLD_PATH) else DEJAVU_PATH
                self.add_font("DejaVu", "B", bold_path, uni=True)
                self._unicode_loaded = True
            except Exception:
                self._unicode_loaded = False

    # ── Font helpers ───────────────────────────────────────────────────────────

    def _font(self, style: str = "", size: int = 10):
        if self._unicode_loaded:
            self.set_font("DejaVu", style, size)
        else:
            self.set_font("Helvetica", style, size)

    def _safe(self, text: str) -> str:
        """
        Sanitize text for Helvetica (Latin-1 only).
        When DejaVu is loaded this is a no-op — text passes through unchanged.
        """
        if self._unicode_loaded:
            return text
        replacements = {
            "\u2014": "-",    # em-dash —
            "\u2013": "-",    # en-dash –
            "\u2018": "'",    # left single quote
            "\u2019": "'",    # right single quote
            "\u201c": '"',    # left double quote
            "\u201d": '"',    # right double quote
            "\u2022": "-",    # bullet •
            "\u20b9": "Rs.",  # rupee ₹
            "\u2026": "...",  # ellipsis …
            "\u00d7": "x",    # multiplication ×
        }
        for char, rep in replacements.items():
            text = text.replace(char, rep)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    # ── Page chrome ────────────────────────────────────────────────────────────

    def header(self):
        self.set_fill_color(*COLOR_MID_GREEN)
        self.rect(0, 0, 210, 22, "F")
        self.set_text_color(*COLOR_WHITE)
        self._font("B", 13)
        self.set_xy(0, 6)
        self.cell(0, 10, "Farmer Revenue Optimizer  |  Crop Advisory Report", align="C")
        self.set_text_color(*COLOR_DARK_GRAY)
        self.ln(18)

    def footer(self):
        self.set_y(-13)
        self._font("", 8)
        self.set_text_color(*COLOR_MID_GRAY)
        self.cell(0, 10,
            f"Page {self.page_no()} | Advisory only. Verify with local KVK.",
            align="C")

    # ── Layout helpers ─────────────────────────────────────────────────────────

    def section_title(self, title: str, color=COLOR_DARK_GREEN):
        self.ln(4)
        self.set_fill_color(*color)
        self.set_text_color(*COLOR_WHITE)
        self._font("B", 11)
        self.cell(0, 8, self._safe(f"  {title}"), ln=True, fill=True)
        self.set_text_color(*COLOR_DARK_GRAY)
        self.ln(2)

    def body_text(self, text: str, size: int = 10):
        self._font("", size)
        self.set_text_color(*COLOR_DARK_GRAY)
        self.multi_cell(0, 6, self._safe(text))
        self.ln(1)

    def bullet(self, text: str):
        self._font("", 9)
        self.set_x(20)
        self.set_text_color(*COLOR_DARK_GRAY)
        self.multi_cell(0, 5.5, self._safe(f"- {text}"))

    def kpi_row_en(self, label: str, value: str, color=COLOR_DARK_GREEN):
        """English KPI row — uses cell() safely (Latin-1 labels only)."""
        self._font("B", 11)
        self.set_text_color(*color)
        self.cell(90, 8, self._safe(label), border=0)
        self._font("B", 12)
        self.cell(0, 8, self._safe(value), border=0, ln=True)
        self.set_text_color(*COLOR_DARK_GRAY)

    def kpi_row_hi(self, label: str, value: str, color=COLOR_DARK_GREEN):
        """
        Hindi KPI row — uses multi_cell() for the label because cell() drops
        Devanagari characters silently in fpdf2. Value is numeric so cell() is fine.
        """
        self._font("B", 11)
        self.set_text_color(*color)
        # Save position, write label via multi_cell in a fixed-width column
        x_start = self.get_x()
        y_start = self.get_y()
        self.multi_cell(90, 8, label)
        # Move to value column (same Y as start)
        self.set_xy(x_start + 90, y_start)
        self._font("B", 12)
        self.set_text_color(*color)
        self.cell(0, 8, value, ln=True)
        self.set_text_color(*COLOR_DARK_GRAY)

    # ── Cost tables ────────────────────────────────────────────────────────────

    def _draw_cost_table(self, use_hindi: bool = False):
        """
        Stable cost table using only cell() — no mixed rect+multi_cell.
        Column widths sum to exactly 180 (usable width with 15mm margins each side).
        Tips are truncated in the table; full tips appear as bullets below the table.
        """
        if use_hindi:
            headers = ["लागत श्रेणी", "कुल (Rs.)", "बचत", "सुझाव (संक्षिप्त)"]
        else:
            headers = ["Cost Category", "Total (Rs.)", "Save Up To", "Tip (see bullets below for full)"]

        # Widths must sum to 180 exactly (210mm page - 15mm left - 15mm right)
        col_w = [50, 30, 30, 70]
        row_h = 7

        # Header row
        self._font("B", 8)
        self.set_fill_color(*COLOR_TABLE_HEADER)
        self.set_text_color(*COLOR_WHITE)
        self.set_draw_color(*COLOR_BORDER)
        for i, h in enumerate(headers):
            self.cell(col_w[i], row_h, self._safe(h), border=1, fill=True)
        self.ln()

        self.set_text_color(*COLOR_DARK_GRAY)
        alt = False
        for item in self.result.cost_items:
            self.set_fill_color(*(COLOR_TABLE_ALT if alt else COLOR_WHITE))
            alt = not alt

            name = item.name_hi if use_hindi else item.name_en
            tip  = item.reduction_tip_hi if use_hindi else item.reduction_tip_en

            # Truncate tip to fit column — full tips are in the bullets section below
            max_tip_chars = 58
            tip_display = self._safe(tip[:max_tip_chars] + "..." if len(tip) > max_tip_chars else tip)

            self._font("B", 8)
            self.cell(col_w[0], row_h, self._safe(name),
                      border=1, fill=True)
            self._font("", 8)
            self.cell(col_w[1], row_h, f"Rs. {item.amount:,}",
                      border=1, fill=True, align="R")
            self.set_text_color(*COLOR_MID_GREEN)
            self.cell(col_w[2], row_h, f"Rs. {item.reducible_by:,}",
                      border=1, fill=True, align="R")
            self.set_text_color(*COLOR_DARK_GRAY)
            self.cell(col_w[3], row_h, tip_display,
                      border=1, fill=True)
            self.ln()

        # Totals row
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
        all_tips = "सभी सुझाव अपनाएं" if use_hindi else "Apply all tips above"
        self.cell(col_w[3], row_h, all_tips, border=1, fill=True)
        self.ln()


# ── English section builder ────────────────────────────────────────────────────

def _build_english_section(pdf: FarmReport, r: RecommendationResult,
                            farm_location: str):
    pdf.add_page()

    # ── Hero box ──
    pdf.set_fill_color(*COLOR_LIGHT_GREEN_BG)
    pdf.rect(14, pdf.get_y(), 182, 52, "F")
    pdf.set_xy(18, pdf.get_y() + 3)

    # Crop name line (keep short — soil on separate line to avoid truncation)
    pdf._font("B", 13)
    pdf.set_text_color(*COLOR_MID_GREEN)
    crop_line = f"{r.crop_name_en}  |  {r.acreage:.1f} acres"
    if farm_location:
        crop_line += f"  |  {farm_location}"
    pdf.multi_cell(0, 8, pdf._safe(crop_line))

    # Soil line below crop name (separate to avoid truncation)
    if r.soil_name_en:
        pdf._font("", 9)
        pdf.set_text_color(*COLOR_MID_GRAY)
        pdf.set_x(18)
        pdf.cell(0, 6, pdf._safe(f"Soil: {r.soil_name_en}  |  Climate: {r.climate_zone}"),
                 ln=True)

    pdf.set_x(18)
    pdf.kpi_row_en("Gross Revenue:",    f"Rs. {r.gross_revenue:,}")
    pdf.set_x(18)
    pdf.kpi_row_en("Total Input Cost:", f"Rs. {r.total_cost:,}",
                   color=COLOR_AMBER)
    margin_color = COLOR_MID_GREEN if r.net_margin >= 0 else COLOR_RED
    pdf.set_x(18)
    pdf.kpi_row_en("Net Margin:",       f"Rs. {r.net_margin:,}",
                   color=margin_color)
    pdf.set_x(18)
    pdf.kpi_row_en("Potential Savings:", f"Rs. {r.total_reducible_cost:,}",
                   color=COLOR_MID_GREEN)
    pdf.ln(6)

    # ── Price info ──
    pdf.section_title("Price Information")
    price_type_label = {
        "msp":     "MSP 2023-24 (Govt. Minimum Support Price)",
        "frp":     "FRP 2023-24 (Govt. Fair & Remunerative Price)",
        "market":  "Market Average (conservative estimate — actual may vary)",
        "default": "Reference price (MSP/FRP 2023-24)",
    }.get(r.price_type, r.price_type.upper())
    pdf.body_text(
        f"Price used: Rs. {r.price_per_quintal:,} per quintal\n"
        f"Basis: {price_type_label}"
    )

    # ── Summary ──
    pdf.section_title("Summary")
    # Fix "soil soil" double word
    narrative = r.narrative_en.replace(" soil soil ", " soil ")
    pdf.body_text(narrative)

    if r.risk_flag:
        pdf.set_fill_color(*COLOR_RED)
        pdf.set_text_color(*COLOR_WHITE)
        pdf._font("B", 10)
        pdf.cell(0, 8,
            "  WARNING: Net margin below Rs. 5,000/acre. Urgent action required.",
            ln=True, fill=True)
        pdf.set_text_color(*COLOR_DARK_GRAY)
        pdf.ln(2)

    # ── Cost table ──
    pdf.section_title("Cost Breakdown & Reduction Opportunities")
    pdf._draw_cost_table(use_hindi=False)
    pdf.ln(2)

    # ── Low-cost tips ──
    pdf.section_title("Low-Cost & Ancient Farming Techniques")
    for tip in r.low_cost_tips_en:
        pdf.bullet(tip)
    pdf.ln(3)

    # ── Intercropping ──
    if r.intercrop_suggestions:
        pdf.section_title("Intercropping Opportunities")
        for sugg in r.intercrop_suggestions:
            pdf._font("B", 9)
            pdf.set_text_color(*COLOR_MID_GREEN)
            pdf.multi_cell(0, 6,
                pdf._safe(f"{sugg.companion_name_en}  (Row ratio: {sugg.row_ratio})"))
            pdf.set_text_color(*COLOR_DARK_GRAY)
            pdf._font("", 8)
            pdf.multi_cell(0, 5, pdf._safe(sugg.benefit_en))
            pdf._font("B", 8)
            pdf.set_text_color(*COLOR_MID_GREEN)
            pdf.cell(0, 5,
                pdf._safe(
                    f"+{sugg.revenue_uplift_percent:.0f}% estimated revenue uplift"
                ), ln=True)
            pdf.set_text_color(*COLOR_DARK_GRAY)
            pdf.ln(2)

    # ── Seasonal tips ──
    pdf.section_title("Seasonal Planting Tips")
    for tip in r.seasonal_tips_en:
        pdf.bullet(tip)
    pdf.ln(3)

    # ── Vertical farming ──
    pdf.section_title("Vertical Farming & Value Addition")
    pdf.body_text(r.vertical_farming_en)

    # ── Disclaimer ──
    pdf.section_title("Disclaimer", color=COLOR_MID_GRAY)
    pdf._font("", 8)
    pdf.set_text_color(*COLOR_MID_GRAY)
    pdf.multi_cell(0, 5, pdf._safe(
        "Generated by automated advisory system using MSP/FRP 2023-24 reference data. "
        "Does not account for micro-climate variations, local pest pressure, or "
        "real-time market fluctuations. Always verify with your local Krishi Vigyan "
        "Kendra (KVK) or agriculture extension officer before financial decisions."
    ))


# ── Hindi section builder ──────────────────────────────────────────────────────

def _build_hindi_section(pdf: FarmReport, r: RecommendationResult,
                          farm_location: str):
    pdf.add_page()

    # Hindi section divider header
    pdf.set_fill_color(*COLOR_HINDI_HEADER)
    pdf.rect(0, pdf.get_y() - 2, 210, 14, "F")
    pdf._font("B", 13)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_xy(0, pdf.get_y())
    # Use multi_cell so Devanagari renders
    pdf.multi_cell(0, 10, "  हिंदी अनुभाग — किसान सलाहकार रिपोर्ट")
    pdf.set_text_color(*COLOR_DARK_GRAY)
    pdf.ln(3)

    # ── Hindi Hero box ──
    pdf.set_fill_color(*COLOR_LIGHT_GREEN_BG)
    pdf.rect(14, pdf.get_y(), 182, 56, "F")
    pdf.set_xy(18, pdf.get_y() + 3)

    # Crop name — multi_cell so Devanagari renders
    pdf._font("B", 13)
    pdf.set_text_color(*COLOR_MID_GREEN)
    crop_line = f"{r.crop_name_hi}  |  {r.acreage:.1f} एकड़"
    if farm_location:
        crop_line += f"  |  {farm_location}"
    pdf.set_x(18)
    pdf.multi_cell(0, 8, crop_line)

    if r.soil_name_en:
        pdf._font("", 9)
        pdf.set_text_color(*COLOR_MID_GRAY)
        pdf.set_x(18)
        pdf.multi_cell(0, 6, f"मिट्टी: {r.soil_name_en}  |  जलवायु: {r.climate_zone}")

    pdf.set_x(18)
    pdf.kpi_row_hi("सकल आय:",      f"Rs. {r.gross_revenue:,}")
    pdf.set_x(18)
    pdf.kpi_row_hi("कुल लागत:",    f"Rs. {r.total_cost:,}", color=COLOR_AMBER)
    margin_color = COLOR_MID_GREEN if r.net_margin >= 0 else COLOR_RED
    pdf.set_x(18)
    pdf.kpi_row_hi("शुद्ध लाभ:",   f"Rs. {r.net_margin:,}", color=margin_color)
    pdf.set_x(18)
    pdf.kpi_row_hi("संभावित बचत:", f"Rs. {r.total_reducible_cost:,}",
                   color=COLOR_MID_GREEN)
    pdf.ln(6)

    # ── Price info ──
    pdf.section_title("मूल्य जानकारी", color=COLOR_HINDI_HEADER)
    price_type_label_hi = {
        "msp":     "MSP 2023-24 (सरकारी न्यूनतम समर्थन मूल्य)",
        "frp":     "FRP 2023-24 (सरकारी उचित एवं लाभकारी मूल्य)",
        "market":  "बाजार औसत (रूढ़िवादी अनुमान — वास्तविक भिन्न हो सकता है)",
        "default": "संदर्भ मूल्य (MSP/FRP 2023-24)",
    }.get(r.price_type, r.price_type.upper())
    pdf.body_text(
        f"उपयोग किया गया मूल्य: Rs. {r.price_per_quintal:,} प्रति क्विंटल\n"
        f"आधार: {price_type_label_hi}"
    )

    # ── Summary ──
    pdf.section_title("सारांश", color=COLOR_HINDI_HEADER)
    narrative_hi = r.narrative_hi.replace(" मिट्टी मिट्टी ", " मिट्टी ")
    pdf.body_text(narrative_hi)

    if r.risk_flag:
        pdf.set_fill_color(*COLOR_RED)
        pdf.set_text_color(*COLOR_WHITE)
        pdf._font("B", 10)
        pdf.multi_cell(0, 8,
            "  चेतावनी: शुद्ध मार्जिन Rs. 5,000/एकड़ से कम। तत्काल कदम उठाएं।")
        pdf.set_text_color(*COLOR_DARK_GRAY)
        pdf.ln(2)

    # ── Cost table ──
    pdf.section_title("लागत विश्लेषण और बचत के अवसर", color=COLOR_HINDI_HEADER)
    pdf._draw_cost_table(use_hindi=True)
    pdf.ln(2)

    # ── Tips ──
    pdf.section_title("कम लागत और प्राचीन तकनीकें", color=COLOR_HINDI_HEADER)
    for tip in r.low_cost_tips_hi:
        pdf.bullet(tip)
    pdf.ln(3)

    # ── Intercropping ──
    if r.intercrop_suggestions:
        pdf.section_title("अंतरफसल सुझाव", color=COLOR_HINDI_HEADER)
        for sugg in r.intercrop_suggestions:
            pdf._font("B", 9)
            pdf.set_text_color(*COLOR_MID_GREEN)
            pdf.multi_cell(0, 6,
                f"{sugg.companion_name_hi}  (पंक्ति अनुपात: {sugg.row_ratio})")
            pdf.set_text_color(*COLOR_DARK_GRAY)
            pdf._font("", 8)
            pdf.multi_cell(0, 5, sugg.benefit_hi)
            pdf._font("B", 8)
            pdf.set_text_color(*COLOR_MID_GREEN)
            pdf.multi_cell(0, 5,
                f"+{sugg.revenue_uplift_percent:.0f}% अनुमानित राजस्व वृद्धि")
            pdf.set_text_color(*COLOR_DARK_GRAY)
            pdf.ln(2)

    # ── Seasonal tips ──
    pdf.section_title("मौसमी रोपण सुझाव", color=COLOR_HINDI_HEADER)
    for tip in r.seasonal_tips_hi:
        pdf.bullet(tip)
    pdf.ln(3)

    # ── Vertical farming ──
    pdf.section_title("ऊर्ध्वाधर खेती / मूल्य संवर्धन", color=COLOR_HINDI_HEADER)
    pdf.body_text(r.vertical_farming_hi)

    # ── Disclaimer ──
    pdf.section_title("अस्वीकरण", color=COLOR_MID_GRAY)
    pdf._font("", 8)
    pdf.set_text_color(*COLOR_MID_GRAY)
    pdf.multi_cell(0, 5,
        "यह रिपोर्ट स्वचालित सलाहकार प्रणाली द्वारा MSP/FRP 2023-24 संदर्भ डेटा "
        "का उपयोग करके तैयार की गई है। सूक्ष्म-जलवायु, स्थानीय कीट दबाव, या "
        "वास्तविक समय बाजार उतार-चढ़ाव के लिए जिम्मेदार नहीं है। वित्तीय निर्णय "
        "लेने से पहले अपने स्थानीय कृषि विभाग या KVK से सत्यापित करें।"
    )


# ── LLM advisory section builder ──────────────────────────────────────────────

def _build_llm_section(pdf: FarmReport, llm_advisory: str, lang: str = "en"):
    """
    Renders the AI-generated advisory into the PDF.
    Called only when llm_advisory is a non-empty string.
    Placed after the main sections, before the disclaimer.
    Works in both English and Hindi depending on lang.
    """
    if lang == "hi":
        pdf.section_title("AI-संचालित अतिरिक्त सलाह", color=(74, 20, 140))
        pdf._font("", 8)
        pdf.set_text_color(*COLOR_MID_GRAY)
        pdf.multi_cell(0, 4.5,
            "OpenAI GPT द्वारा संचालित। आपके गणना किए गए खेत डेटा पर आधारित। "
            "संख्याएं और जोखिम वर्गीकरण इंजन द्वारा निर्धारित — AI केवल व्याख्या और "
            "रणनीति प्रदान करती है।")
        pdf.ln(2)
        pdf.set_text_color(*COLOR_DARK_GRAY)
        pdf.body_text(llm_advisory)
    else:
        pdf.section_title("AI-Powered Additional Advisory", color=(74, 20, 140))
        pdf._font("", 8)
        pdf.set_text_color(*COLOR_MID_GRAY)
        pdf.multi_cell(0, 4.5,
            "Powered by OpenAI GPT. Based on your computed farm data only. "
            "All numbers and risk classifications are determined by the rule engine — "
            "AI provides explanation and strategy enrichment only.")
        pdf.ln(2)
        pdf.set_text_color(*COLOR_DARK_GRAY)
        pdf.body_text(llm_advisory)


# ── Public entry point ─────────────────────────────────────────────────────────

def generate_pdf(
    result: RecommendationResult,
    farm_location: str = "",
    llm_advisory_en: str = "",
    llm_advisory_hi: str = "",
) -> bytes:
    """
    Generate complete dual-language PDF.

    Args:
        result          : RecommendationResult from the engine
        farm_location   : human-readable location string (lat/lng)
        llm_advisory_en : AI advisory text in English (empty = section omitted)
        llm_advisory_hi : AI advisory text in Hindi (empty = section omitted)

    Always produces English section.
    Appends Hindi section if DejaVuSans.ttf is in fonts/.
    LLM advisory sections are included only when non-empty strings are passed.
    Returns bytes ready for st.download_button.
    """
    pdf = FarmReport(result, farm_location)

    _build_english_section(pdf, result, farm_location)

    # LLM advisory English — appended after main English section
    if llm_advisory_en and llm_advisory_en.strip():
        _build_llm_section(pdf, llm_advisory_en.strip(), lang="en")

    if pdf._unicode_loaded:
        _build_hindi_section(pdf, result, farm_location)
        # LLM advisory Hindi — appended after Hindi section
        if llm_advisory_hi and llm_advisory_hi.strip():
            _build_llm_section(pdf, llm_advisory_hi.strip(), lang="hi")
    else:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*COLOR_HINDI_HEADER)
        pdf.cell(0, 12, "Hindi Section Not Available in This Build", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*COLOR_DARK_GRAY)
        pdf.multi_cell(0, 6,
            "To enable the Hindi section in your PDF reports:\n\n"
            "1. Download DejaVuSans.ttf from: https://dejavu-fonts.github.io/\n"
            "2. Optionally also download DejaVuSans-Bold.ttf\n"
            "3. Place both files in the fonts/ directory of this repository\n"
            "4. Redeploy the app\n\n"
            "The Hindi section activates automatically once the font file is present.\n"
            "Hindi text is fully available in the Streamlit web interface already."
        )

    return bytes(pdf.output())
