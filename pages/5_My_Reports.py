"""
Page 5 — My Reports
Shows a signed-in farmer's own saved farm records, pulled from Supabase
(core/db_service.py), scoped to their account by owner_email. Requires
sign-in; never shows another user's data (see db_service.py docstring for
how ownership is enforced server-side).
"""
import streamlit as st
import pandas as pd
from core.auth_service import require_login, current_user_email, render_account_widget
from core.db_service import get_farm_history, delete_farm_record, is_db_configured
from core.storage_service import get_signed_url
from core.crop_data import get_crop_display_name
from utils.ui_utils import inject_mobile_css

st.set_page_config(page_title="My Reports | FRO", page_icon="📂", layout="wide")

if "lang" not in st.session_state:
    st.session_state["lang"] = "en"
lang = st.session_state["lang"]

require_login(lang)
inject_mobile_css()
render_account_widget(lang)

st.title("📂 My Reports" if lang == "en" else "📂 मेरी रिपोर्ट्स")

if not is_db_configured():
    st.info(
        "Database isn't configured for this deployment yet — nothing has been saved."
        if lang == "en"
        else "इस डिप्लॉयमेंट के लिए डेटाबेस अभी कॉन्फ़िगर नहीं है — कुछ भी सहेजा नहीं गया है।"
    )
    st.stop()

owner_email = current_user_email()
records = get_farm_history(owner_email, limit=50)

if not records:
    st.info(
        "No saved reports yet. Every completed advisory run is saved here automatically."
        if lang == "en"
        else "अभी तक कोई सहेजी गई रिपोर्ट नहीं। हर पूर्ण सलाहकार रन यहाँ स्वतः सहेजा जाता है।"
    )
    st.stop()

for rec in records:
    crop_label = get_crop_display_name(rec.get("crop", ""), lang) if rec.get("crop") else rec.get("crop", "")
    header = f"{crop_label} — {rec.get('acreage')} ac — {rec.get('state')} ({rec.get('created_at', '')[:10]})"
    with st.expander(header):
        col1, col2, col3 = st.columns(3)
        col1.metric("Gross Revenue" if lang == "en" else "सकल आय", f"Rs.{rec.get('gross_revenue', 0):,.0f}")
        col2.metric("Total Cost" if lang == "en" else "कुल लागत", f"Rs.{rec.get('total_cost', 0):,.0f}")
        col3.metric("Net Margin" if lang == "en" else "शुद्ध लाभ", f"Rs.{rec.get('net_margin', 0):,.0f}")

        storage_path = rec.get("report_storage_path")
        if storage_path:
            url = get_signed_url(storage_path)
            if url:
                st.link_button("⬇️ Download saved PDF" if lang == "en" else "⬇️ सहेजी गई PDF डाउनलोड करें", url)

        if st.button("🗑️ Delete" if lang == "en" else "🗑️ हटाएं", key=f"del_{rec.get('id')}"):
            if delete_farm_record(owner_email, rec.get("id")):
                st.rerun()
