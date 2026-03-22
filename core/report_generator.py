from fpdf import FPDF
from typing import Optional
from core.models import RecommendationResult

COLOR_DARK_GREEN     = (30, 100, 30)
COLOR_MID_GREEN      = (46, 125, 50)
COLOR_LIGHT_GREEN_BG = (232, 245, 233)
COLOR_AMBER          = (255, 143, 0)
COLOR_RED            = (198, 40, 40)
COLOR_WHITE          = (255, 255, 255)
COLOR_DARK_GRAY      = (40, 40, 40)
COLOR_MID_GRAY       = (100, 100, 100)
COLOR_TABLE_HEADER   = (27, 94, 32)
COLOR_TABLE_ALT      = (240, 248, 240)
COLOR_BORDER         = (180, 180, 180)


class FarmReport(FPDF):
    def __init__(self, result: RecommendationResult, farm_location: str = ""):
        super().__init__()
        self.result = result
        self.farm_location = farm_location
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(15, 15, 15)

    def header(self):
        self.set_fill_color(*COLOR_MID_GREEN)
        self.rect(0, 0, 210, 22, "F")
        self.set_text_color(*COLOR_WHITE)
        self.set_font("Helvetica", "B", 13)
        self.set_xy(0, 6)
        self.cell(0, 10, "Farmer Revenue Optimizer  |  Crop Advisory Report", align="C")
        self.set_text_color(*COLOR_DARK_GRAY)
        self.ln(18)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*COLOR_MID_GRAY)
        self.cell(
            0, 10,
            f"Page {self.page_no()} | Data is advisory only. Verify with local agricultural officer.",
            align="C",
        )

    def section_title(self, title: str, color=COLOR_DARK_GREEN):
        self.ln(4)
        self.set_fill_color(*color)
        self.set_text_color(*COLOR_WHITE)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, f"  {title}", ln=True, fill=True)
        self.set_text_color(*COLOR_DARK_GRAY)
        self.ln(2)

    def body_text(self, text: str, size: int = 10):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*COLOR_DARK_GRAY)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def bullet(self, text: str):
        self.set_font("Helvetica", "", 9)
        self.set_x(20)
        self.set_text_color(*COLOR_DARK_GRAY)
        self.multi_cell(0, 5.5, f"- {text}")

    def kpi_row(self, label: str, value: str, color=COLOR_DARK_GREEN):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*color)
        self.cell(90, 8, label, border=0)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, value, border=0, ln=True)
        self.set_text_color(*COLOR_DARK_GRAY)

    def cost_table(self):
        col_widths = [70, 32, 32, 46]
        headers = ["Cost Category", "Total (Rs.)", "Save Up To", "How to Reduce"]
        self.set_font("Helvetica", "B", 9)
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
            self.set_font("Helvetica", "B", 8)
            self.cell(col_widths[0], 6, item.name_en, border=1, fill=True)
            self.set_font("Helvetica", "", 8)
            self.cell(col_widths[1], 6, f"Rs. {item.amount:,}", border=1, fill=True, align="R")
            self.set_text_color(*COLOR_MID_GREEN)
            self.cell(col_widths[2], 6, f"Rs. {item.reducible_by:,}", border=1, fill=True, align="R")
            self.set_text_color(*COLOR_DARK_GRAY)
            tip = item.reduction_tip_en[:55] + "..." if len(item.reduction_tip_en) > 55 else item.reduction_tip_en
            self.cell(col_widths[3], 6, tip, border=1, fill=True)
            self.ln()
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*COLOR_LIGHT_GREEN_BG)
        self.cell(col_widths[0], 7, "TOTAL", border=1, fill=True)
        self.cell(col_widths[1], 7, f"Rs. {self.result.total_cost:,}", border=1, fill=True, align="R")
        self.set_text_color(*COLOR_MID_GREEN)
        self.cell(col_widths[2], 7, f"Rs. {self.result.total_reducible_cost:,}", border=1, fill=True, align="R")
        self.set_text_color(*COLOR_DARK_GRAY)
        self.cell(col_widths[3], 7, "Apply all tips above", border=1, fill=True)
        self.ln()


def generate_pdf(result: RecommendationResult, farm_location: str = "") -> bytes:
    pdf = FarmReport(result, farm_location)
    pdf.add_page()
    r = result

    pdf.set_fill_color(*COLOR_LIGHT_GREEN_BG)
    pdf.rect(14, pdf.get_y(), 182, 46, "F")
    pdf.set_xy(18, pdf.get_y() + 3)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*COLOR_MID_GREEN)
    crop_label = f"{r.crop_name_en}  |  {r.acreage:.1f} acres"
    if farm_location:
        crop_label += f"  |  {farm_location}"
    pdf.cell(0, 9, crop_label, ln=True)
    pdf.set_x(18)
    pdf.kpi_row("Gross Revenue:", f"Rs. {r.gross_revenue:,}")
    pdf.set_x(18)
    pdf.kpi_row("Total Input Cost:", f"Rs. {r.total_cost:,}", color=COLOR_AMBER)
    margin_color = COLOR_MID_GREEN if r.net_margin >= 0 else COLOR_RED
    pdf.set_x(18)
    pdf.kpi_row("Net Margin:", f"Rs. {r.net_margin:,}", color=margin_color)
    pdf.set_x(18)
    pdf.kpi_row("Potential Savings:", f"Rs. {r.total_reducible_cost:,}", color=COLOR_MID_GREEN)
    pdf.ln(6)

    pdf.section_title("Price Information")
    price_label = r.price_type.upper()
    price_note = f"Price used: Rs. {r.price_per_quintal:,}/quintal ({price_label})"
    if r.price_type == "market":
        price_note += " - This is a conservative market average. Actual price may vary significantly."
    pdf.body_text(price_note)

    pdf.section_title("Summary")
    pdf.body_text(r.narrative_en)

    if r.risk_flag:
        pdf.set_fill_color(*COLOR_RED)
        pdf.set_text_color(*COLOR_WHITE)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(
            0, 8,
            "  WARNING: Net margin is below Rs. 5,000/acre. Urgent action required.",
            ln=True, fill=True,
        )
        pdf.set_text_color(*COLOR_DARK_GRAY)
        pdf.ln(2)

    pdf.section_title("Cost Breakdown & Reduction Opportunities")
    pdf.cost_table()
    pdf.ln(2)

    pdf.section_title("Low-Cost & Ancient Farming Techniques")
    for tip in r.low_cost_tips_en:
        pdf.bullet(tip)
    pdf.ln(3)

    if r.intercrop_suggestions:
        pdf.section_title("Intercropping Opportunities")
        for sugg in r.intercrop_suggestions:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*COLOR_MID_GREEN)
            pdf.cell(0, 6, f"{sugg.companion_name_en}  (Row ratio: {sugg.row_ratio})", ln=True)
            pdf.set_text_color(*COLOR_DARK_GRAY)
            pdf.set_font("Helvetica", "", 8)
            pdf.multi_cell(0, 5, sugg.benefit_en)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*COLOR_MID_GREEN)
            pdf.cell(0, 5, f"Estimated revenue uplift: +{sugg.revenue_uplift_percent:.0f}%", ln=True)
            pdf.set_text_color(*COLOR_DARK_GRAY)
            pdf.ln(2)

    pdf.section_title("Seasonal Planting Tips")
    for tip in r.seasonal_tips_en:
        pdf.bullet(tip)
    pdf.ln(3)

    pdf.section_title("Vertical Farming & Value Addition")
    pdf.body_text(r.vertical_farming_en)

    pdf.section_title("Disclaimer", color=COLOR_MID_GRAY)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*COLOR_MID_GRAY)
    pdf.multi_cell(
        0, 5,
        "This report is generated by an automated advisory system using public MSP data (2023-24 season) "
        "and rule-based estimates. It does not account for micro-climate variations, pest outbreaks, "
        "or real-time market fluctuations. Always verify recommendations with your local Krishi Vigyan Kendra (KVK) "
        "or agriculture extension officer before making financial decisions.",
    )

    return bytes(pdf.output())
