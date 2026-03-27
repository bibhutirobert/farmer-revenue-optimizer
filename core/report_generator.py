"""
PDF Report Generator — V3
Dual-language: English section first, Hindi section second, one file.

Font strategy:
  - Tries to load fonts/DejaVuSans.ttf for Unicode (Hindi) support
  - If font file missing: generates English-only PDF with a note
  - Never crashes — graceful degradation

To enable Hindi PDF:
  1. Download DejaVuSans.ttf (see fonts/README.txt)
  2. Place in the fonts/ directory
  3. Redeploy — Hindi section activates automatically
"""

import os
from fpdf import FPDF
from typing import Optional
from core.models import RecommendationResult

# Paths
ROOT_DIR  = os.path.dirname(os.path.dirname(__file__))
FONTS_DIR = os.path.join(ROOT_DIR, "fonts")
DEJAVU_PATH = os.path.join(FONTS_DIR, "DejaVuSans.ttf")
DEJAVU_BOLD_PATH = os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf")

# Colors
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
COLOR_HINDI_HEADER   = (13, 71, 161)   # Deep blue for Hindi section divider


def _has_devanagari_font() -> bool:
    return os.path.exists(DEJAVU_PATH)


class FarmReport(FPDF):
    def __init__(self, result: RecommendationResult, farm_location: str = ""):
        super().__init__()
        self.result       = result
        self.farm_location = farm_location
        self._unicode_loaded = False
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 15, 15)

        # Try to load Unicode font
        if _has_devanagari_font():
            try:
                self.add_font("DejaVu", "", DEJAVU_PATH, uni=True)
                if os.path.exists(DEJAVU_BOLD_PATH):
                    self.add_font("DejaVu", "B", DEJAVU_BOLD_PATH, uni=True)
                else:
                    self.add_font("DejaVu", "B", DEJAVU_PATH, uni=True)
                self._unicode_loaded = True
            except Exception:
                self._unicode_loaded = False

    def _font(self, style="", size=10):
        """Set appropriate font based on availability."""
        if self._unicode_loaded:
            self.set_font("DejaVu", style, size)
        else:
            self.set_font("Helvetica", style, size)

    def _safe(self, text: str) -> str:
        """
        Sanitize text for Helvetica (Latin-1 only).
        Replaces common Unicode characters that break Helvetica rendering.
        Only applied when DejaVu font is NOT loaded.
        When DejaVu IS loaded, text passes through unchanged.
        """
        if self._unicode_loaded:
            return text
        replacements = {
            "—": "-",   # em-dash — -> -
            "–": "-",   # en-dash – -> -
            "‘": "'",   # left single quote
            "’": "'",   # right single quote / apostrophe
            "“": '"',  # left double quote
            "”": '"',  # right double quote
            "•": "-",   # bullet •
            "₹": "Rs.", # rupee symbol ₹
            "…": "...", # ellipsis …
            "×": "x",   # multiplication sign ×
            "é": "e",   # e with accent
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        # Final safety: encode to latin-1, replacing anything still unmappable
        return text.encode("latin-1", errors="replace").decode("latin-1")

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
        self.cell(0, 10, f"Page {self.page_no()} | Advisory only. Verify with local KVK.", align="C")

    def section_title(self, title: str, color=COLOR_DARK_GREEN):
        self.ln(4)
        self.set_fill_color(*color)
        self.set_text_color(*COLOR_WHITE)
        self._font("B", 11)
        self.cell(0, 8, f"  {title}", ln=True, fill=True)
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

    def kpi_row(self, label: str, value: str, color=COLOR_DARK_GREEN):
        self._font("B", 11)
        self.set_text_color(*color)
        self.cell(90, 8, label, border=0)
        self._font("B", 12)
        self.cell(0, 8, value, border=0, ln=True)
        self.set_text_color(*COLOR_DARK_GRAY)

    def cost_table(self):
        col_widths = [70, 32, 32, 46]
        headers    = ["Cost Category", "Total (Rs.)", "Save Up To", "How to Reduce"]
        self._font("B", 9)
        self.set_fill_color(*COLOR_TABLE_HEADER)
        self.set_text_color(*COLOR_WHITE)
        self.set_draw_color(*COLOR_BORDER)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True)
        self.ln()
        self.set_text_color(*COLOR_DARK_GRAY)
        alt = False
        for item in self.result.cost_items:
            self.set_fill_color(*(COLOR_TABLE_ALT if alt else COLOR_WHITE))
            alt = not alt
            self._font("B", 8)
            self.cell(col_widths[0], 6, item.name_en, border=1, fill=True)
            self._font("", 8)
            self.cell(col_widths[1], 6, f"Rs. {item.amount:,}", border=1, fill=True, align="R")
            self.set_text_color(*COLOR_MID_GREEN)
            self.cell(col_widths[2], 6, f"Rs. {item.reducible_by:,}", border=1, fill=True, align="R")
            self.set_text_color(*COLOR_DARK_GRAY)
            tip = item.reduction_tip_en[:55] + "..." if len(item.reduction_tip_en) > 55 else item.reduction_tip_en
            self.cell(col_widths[3], 6, tip, border=1, fill=True)
            self.ln()
        # Totals row
        self._font("B", 9)
        self.set_fill_color(*COLOR_LIGHT_GREEN_BG)
        self.cell(col_widths[0], 7, "TOTAL", border=1, fill=True)
        self.cell(col_widths[1], 7, f"Rs. {self.result.total_cost:,}", border=1, fill=True, align="R")
        self.set_text_color(*COLOR_MID_GREEN)
        self.cell(col_widths[2], 7, f"Rs. {self.result.total_reducible_cost:,}", border=1, fill=True, align="R")
        self.set_text_color(*COLOR_DARK_GRAY)
        self.cell(col_widths[3], 7, "Apply all tips above", border=1, fill=True)
        self.ln()

    # ── Hindi-language helpers (only called when DejaVu loaded) ────────────────

    def hindi_cost_table(self):
        col_widths = [70, 32, 32, 46]
        headers    = ["लागत श्रेणी", "कुल (Rs.)", "बचत संभव", "कैसे बचाएं"]
        self._font("B", 9)
        self.set_fill_color(*COLOR_TABLE_HEADER)
        self.set_text_color(*COLOR_WHITE)
        self.set_draw_color(*COLOR_BORDER)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True)
        self.ln()
        self.set_text_color(*COLOR_DARK_GRAY)
        alt = False
        for item in self.result.cost_items:
            self.set_fill_color(*(COLOR_TABLE_ALT if alt else COLOR_WHITE))
            alt = not alt
            self._font("B", 8)
            self.cell(col_widths[0], 6, item.name_hi, border=1, fill=True)
            self._font("", 8)
            self.cell(col_widths[1], 6, f"Rs. {item.amount:,}", border=1, fill=True, align="R")
            self.set_text_color(*COLOR_MID_GREEN)
            self.cell(col_widths[2], 6, f"Rs. {item.reducible_by:,}", border=1, fill=True, align="R")
            self.set_text_color(*COLOR_DARK_GRAY)
            tip = item.reduction_tip_hi[:55] + "..." if len(item.reduction_tip_hi) > 55 else item.reduction_tip_hi
            self.cell(col_widths[3], 6, tip, border=1, fill=True)
            self.ln()
        self._font("B", 9)
        self.set_fill_color(*COLOR_LIGHT_GREEN_BG)
        self.cell(col_widths[0], 7, "कुल", border=1, fill=True)
        self.cell(col_widths[1], 7, f"Rs. {self.result.total_cost:,}", border=1, fill=True, align="R")
        self.set_text_color(*COLOR_MID_GREEN)
        self.cell(col_widths[2], 7, f"Rs. {self.result.total_reducible_cost:,}", border=1, fill=True, align="R")
        self.set_text_color(*COLOR_DARK_GRAY)
        self.cell(col_widths[3], 7, "सभी सुझाव अपनाएं", border=1, fill=True)
        self.ln()


def _build_english_section(pdf: FarmReport, r: RecommendationResult, farm_location: str):
    """Write the complete English section."""
    pdf.add_page()

    # Hero box
    pdf.set_fill_color(*COLOR_LIGHT_GREEN_BG)
    pdf.rect(14, pdf.get_y(), 182, 52, "F")
    pdf.set_xy(18, pdf.get_y() + 3)
    pdf._font("B", 14)
    pdf.set_text_color(*COLOR_MID_GREEN)
    crop_label = f"{r.crop_name_en}  |  {r.acreage:.1f} acres"
    if farm_location:
        crop_label += f"  |  {farm_location}"
    if r.soil_name_en:
        crop_label += f"  |  {r.soil_name_en}"
    pdf.cell(0, 9, crop_label, ln=True)
    pdf.set_x(18); pdf.kpi_row("Gross Revenue:",   f"Rs. {r.gross_revenue:,}")
    pdf.set_x(18); pdf.kpi_row("Total Input Cost:", f"Rs. {r.total_cost:,}",  color=COLOR_AMBER)
    margin_color = COLOR_MID_GREEN if r.net_margin >= 0 else COLOR_RED
    pdf.set_x(18); pdf.kpi_row("Net Margin:",       f"Rs. {r.net_margin:,}",  color=margin_color)
    pdf.set_x(18); pdf.kpi_row("Potential Savings:", f"Rs. {r.total_reducible_cost:,}", color=COLOR_MID_GREEN)
    pdf.ln(6)

    # Price info
    pdf.section_title("Price Information")
    price_label = r.price_type.upper()
    price_note  = f"Price: Rs. {r.price_per_quintal:,}/quintal ({price_label}) — Source: {r.price_source}, updated {r.price_updated_at}"
    if r.price_type == "market":
        price_note += " — Conservative avg. Actual may vary."
    pdf.body_text(price_note)

    if r.soil_name_en:
        pdf.section_title("Location Intelligence")
        pdf.body_text(f"Detected Soil: {r.soil_name_en} | Climate Zone: {r.climate_zone}")

    # Summary
    pdf.section_title("Summary")
    pdf.body_text(r.narrative_en)

    if r.risk_flag:
        pdf.set_fill_color(*COLOR_RED)
        pdf.set_text_color(*COLOR_WHITE)
        pdf._font("B", 10)
        pdf.cell(0, 8, "  WARNING: Net margin below Rs. 5,000/acre. Urgent action required.", ln=True, fill=True)
        pdf.set_text_color(*COLOR_DARK_GRAY)
        pdf.ln(2)

    # Cost table
    pdf.section_title("Cost Breakdown & Reduction Opportunities")
    pdf.cost_table()
    pdf.ln(2)

    # Tips
    pdf.section_title("Low-Cost & Ancient Farming Techniques")
    for tip in r.low_cost_tips_en:
        pdf.bullet(tip)
    pdf.ln(3)

    # Intercropping
    if r.intercrop_suggestions:
        pdf.section_title("Intercropping Opportunities")
        for sugg in r.intercrop_suggestions:
            pdf._font("B", 9); pdf.set_text_color(*COLOR_MID_GREEN)
            pdf.cell(0, 6, f"{sugg.companion_name_en}  (Ratio: {sugg.row_ratio})", ln=True)
            pdf.set_text_color(*COLOR_DARK_GRAY); pdf._font("", 8)
            pdf.multi_cell(0, 5, sugg.benefit_en)
            pdf._font("B", 8); pdf.set_text_color(*COLOR_MID_GREEN)
            pdf.cell(0, 5, f"+{sugg.revenue_uplift_percent:.0f}% estimated revenue uplift", ln=True)
            pdf.set_text_color(*COLOR_DARK_GRAY); pdf.ln(2)

    # Seasonal tips
    pdf.section_title("Seasonal Planting Tips")
    for tip in r.seasonal_tips_en:
        pdf.bullet(tip)
    pdf.ln(3)

    # Vertical farming
    pdf.section_title("Vertical Farming & Value Addition")
    pdf.body_text(r.vertical_farming_en)

    # Disclaimer
    pdf.section_title("Disclaimer", color=COLOR_MID_GRAY)
    pdf._font("", 8); pdf.set_text_color(*COLOR_MID_GRAY)
    pdf.multi_cell(0, 5,
        "Generated by automated advisory system using MSP 2023-24 data. "
        "Does not account for micro-climate, local pest pressure, or real-time markets. "
        "Verify with local KVK before financial decisions.")


def _build_hindi_section(pdf: FarmReport, r: RecommendationResult, farm_location: str):
    """Write the complete Hindi section. Only called when DejaVu font is loaded."""
    pdf.add_page()

    # Hindi section header
    pdf.set_fill_color(*COLOR_HINDI_HEADER)
    pdf.rect(0, pdf.get_y() - 2, 210, 14, "F")
    pdf._font("B", 13)
    pdf.set_text_color(*COLOR_WHITE)
    pdf.set_xy(0, pdf.get_y())
    pdf.cell(0, 10, "  हिंदी अनुभाग — किसान सलाहकार रिपोर्ट", ln=True)
    pdf.set_text_color(*COLOR_DARK_GRAY)
    pdf.ln(4)

    # Hero box
    pdf.set_fill_color(*COLOR_LIGHT_GREEN_BG)
    pdf.rect(14, pdf.get_y(), 182, 52, "F")
    pdf.set_xy(18, pdf.get_y() + 3)
    pdf._font("B", 14)
    pdf.set_text_color(*COLOR_MID_GREEN)
    crop_label = f"{r.crop_name_hi}  |  {r.acreage:.1f} एकड़"
    if farm_location:
        crop_label += f"  |  {farm_location}"
    pdf.cell(0, 9, crop_label, ln=True)
    pdf.set_x(18); pdf.kpi_row("सकल आय:",       f"Rs. {r.gross_revenue:,}")
    pdf.set_x(18); pdf.kpi_row("कुल लागत:",      f"Rs. {r.total_cost:,}",  color=COLOR_AMBER)
    margin_color = COLOR_MID_GREEN if r.net_margin >= 0 else COLOR_RED
    pdf.set_x(18); pdf.kpi_row("शुद्ध लाभ:",     f"Rs. {r.net_margin:,}",  color=margin_color)
    pdf.set_x(18); pdf.kpi_row("संभावित बचत:",   f"Rs. {r.total_reducible_cost:,}", color=COLOR_MID_GREEN)
    pdf.ln(6)

    # Summary
    pdf.section_title("सारांश", color=COLOR_HINDI_HEADER)
    pdf.body_text(r.narrative_hi)

    if r.risk_flag:
        pdf.set_fill_color(*COLOR_RED); pdf.set_text_color(*COLOR_WHITE); pdf._font("B", 10)
        pdf.cell(0, 8, "  चेतावनी: शुद्ध मार्जिन Rs. 5,000/एकड़ से कम। तत्काल कदम उठाएं।", ln=True, fill=True)
        pdf.set_text_color(*COLOR_DARK_GRAY); pdf.ln(2)

    # Cost table
    pdf.section_title("लागत विश्लेषण और बचत के अवसर", color=COLOR_HINDI_HEADER)
    pdf.hindi_cost_table()
    pdf.ln(2)

    # Tips
    pdf.section_title("कम लागत और प्राचीन तकनीकें", color=COLOR_HINDI_HEADER)
    for tip in r.low_cost_tips_hi:
        pdf.bullet(tip)
    pdf.ln(3)

    # Intercropping
    if r.intercrop_suggestions:
        pdf.section_title("अंतरफसल सुझाव", color=COLOR_HINDI_HEADER)
        for sugg in r.intercrop_suggestions:
            pdf._font("B", 9); pdf.set_text_color(*COLOR_MID_GREEN)
            pdf.cell(0, 6, f"{sugg.companion_name_hi}  (अनुपात: {sugg.row_ratio})", ln=True)
            pdf.set_text_color(*COLOR_DARK_GRAY); pdf._font("", 8)
            pdf.multi_cell(0, 5, sugg.benefit_hi)
            pdf._font("B", 8); pdf.set_text_color(*COLOR_MID_GREEN)
            pdf.cell(0, 5, f"+{sugg.revenue_uplift_percent:.0f}% अनुमानित राजस्व वृद्धि", ln=True)
            pdf.set_text_color(*COLOR_DARK_GRAY); pdf.ln(2)

    # Seasonal tips
    pdf.section_title("मौसमी रोपण सुझाव", color=COLOR_HINDI_HEADER)
    for tip in r.seasonal_tips_hi:
        pdf.bullet(tip)
    pdf.ln(3)

    # Vertical farming
    pdf.section_title("ऊर्ध्वाधर खेती / मूल्य संवर्धन", color=COLOR_HINDI_HEADER)
    pdf.body_text(r.vertical_farming_hi)

    # Disclaimer
    pdf.section_title("अस्वीकरण", color=COLOR_MID_GRAY)
    pdf._font("", 8); pdf.set_text_color(*COLOR_MID_GRAY)
    pdf.multi_cell(0, 5,
        "यह रिपोर्ट स्वचालित सलाहकार प्रणाली द्वारा MSP 2023-24 डेटा का उपयोग करके तैयार की गई है। "
        "वित्तीय निर्णय लेने से पहले अपने स्थानीय कृषि विभाग या KVK से सत्यापित करें।")


def generate_pdf(result: RecommendationResult, farm_location: str = "") -> bytes:
    """
    Generate complete dual-language PDF.
    - Always produces English section
    - Appends Hindi section if DejaVuSans.ttf is present in fonts/
    - Returns bytes ready for st.download_button
    """
    pdf = FarmReport(result, farm_location)

    # English section
    _build_english_section(pdf, result, farm_location)

    # Hindi section (conditional on font availability)
    if pdf._unicode_loaded:
        _build_hindi_section(pdf, result, farm_location)
    else:
        # Add a note page explaining how to enable Hindi
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
            "The Hindi section will activate automatically once the font file is detected.\n"
            "Hindi text is already available in the Streamlit web interface — "
            "this limitation only affects the PDF download."
        )

    return bytes(pdf.output())
