"""
UI Utils — shared presentation helpers.
=======================================

Two things live here:

  inject_mobile_css()  Touch-target and spacing fixes for phone use. Most
                       farmers will open this on a phone, and Leaflet's
                       default controls are ~26 px — well under the ~44 px
                       that guidance (WCAG 2.5.5 / Apple HIG) treats as the
                       minimum comfortable tap target.

  render_how_to_use()  The "how to use this app" walkthrough, with an
                       optional video clip.

VIDEO SOURCE RESOLUTION (first match wins):
  1. [help] video_url in secrets — a YouTube link or a direct .mp4 URL
  2. assets/how_to_use.mp4 committed in the repo
  3. no video — the written walkthrough renders on its own

The written steps are not a placeholder waiting to be replaced: they stay
visible alongside the video, because a farmer on a slow connection or a
metered plan may never play it.
"""

import os
from typing import List, Optional, Tuple

import streamlit as st

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
LOCAL_VIDEO = os.path.join(ASSETS_DIR, "how_to_use.mp4")

_MOBILE_CSS = """
<style>
/* Leaflet's default controls are far too small for thumbs. */
.leaflet-touch .leaflet-bar a,
.leaflet-bar a {
    width: 44px !important;
    height: 44px !important;
    line-height: 44px !important;
    font-size: 20px !important;
}
.leaflet-draw-toolbar a {
    background-size: 300px 30px !important;
}
/* Keep the layer/draw controls clear of the very edge, where phone
   browsers put their own gesture zones. */
.leaflet-top, .leaflet-bottom { z-index: 900; }
.leaflet-control-container .leaflet-top.leaflet-right { margin-top: 4px; }

@media (max-width: 640px) {
    /* Full-width, thumb-sized primary actions. */
    .stButton > button {
        min-height: 48px;
        font-size: 1rem;
    }
    /* Reclaim horizontal space that is precious on a phone. */
    .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-top: 2.5rem !important;
    }
    /* Stacked columns shouldn't leave a dead gap. */
    div[data-testid="column"] { margin-bottom: 0.25rem; }
}
</style>
"""


def inject_mobile_css() -> None:
    """Idempotent per rerun — Streamlit re-renders the whole script anyway."""
    st.markdown(_MOBILE_CSS, unsafe_allow_html=True)


def get_help_video() -> Tuple[Optional[str], str]:
    """
    Resolve the walkthrough video.

    Returns (source, kind) where kind is "url" | "file" | "none".
    `source` is None when nothing is configured.
    """
    try:
        url = st.secrets.get("help", {}).get("video_url", "")
        if url and url.strip():
            return url.strip(), "url"
    except Exception:
        pass

    if os.path.exists(LOCAL_VIDEO):
        return LOCAL_VIDEO, "file"

    return None, "none"


def _steps(lang: str) -> List[Tuple[str, str]]:
    """(title, detail) pairs describing the real flow, in order."""
    if lang == "hi":
        return [
            ("1. साइन इन करें",
             "Google से साइन इन करें ताकि आपकी रिपोर्ट सुरक्षित रहे और बाद में देख सकें।"),
            ("2. अपना खेत चुनें",
             "नक्शे पर **'मुझे कहाँ हूँ दिखाएँ'** बटन दबाएँ — अगर आप खेत में खड़े हैं तो "
             "नक्शा वहीं पहुँच जाएगा। या पिनकोड/गाँव खोजें, फिर अपने खेत पर टैप करें "
             "और **पुष्टि करें** दबाएँ।"),
            ("3. फसल का विवरण भरें",
             "फसल, एकड़, उपज और लागत दर्ज करें। राज्य, मिट्टी और जलवायु अपने आप भर जाते हैं।"),
            ("4. रिपोर्ट देखें",
             "आय, लागत, बचत के सुझाव, अंतरफसल, मौसम और 3D भू-दृश्य — सब एक जगह।"),
            ("5. PDF डाउनलोड करें",
             "पूरी रिपोर्ट PDF में सहेजें। यह **मेरी रिपोर्ट्स** में अपने आप सुरक्षित रहती है।"),
        ]
    return [
        ("1. Sign in",
         "Sign in with Google so your reports are saved and you can come back to them."),
        ("2. Select your field",
         "Tap **'Show me where I am'** on the map — if you're standing in the field, "
         "the map jumps straight to it. Otherwise search a pincode or village, tap your "
         "field, then press **Confirm**."),
        ("3. Enter crop details",
         "Crop, acreage, yield and costs. State, soil and climate fill in automatically "
         "from the location you picked."),
        ("4. Read your report",
         "Revenue, cost breakdown, savings tips, intercropping, weather outlook and a "
         "3D view of your land — all in one place."),
        ("5. Download the PDF",
         "Save the full report as a PDF. It's also kept for you under **My Reports**."),
    ]


def render_how_to_use(lang: str = "en", expanded: bool = False) -> None:
    """
    Render the walkthrough. Safe to call on any page.

    Shows the video when one is configured, and always shows the written
    steps underneath it.
    """
    title = "❓ How to use this app" if lang == "en" else "❓ इस ऐप का उपयोग कैसे करें"

    with st.expander(title, expanded=expanded):
        source, kind = get_help_video()

        if source:
            try:
                st.video(source)
            except Exception:
                # A bad URL or missing codec must not take the page down —
                # the written steps below still carry the whole explanation.
                st.info(
                    "The walkthrough video could not be loaded. The written steps below "
                    "cover the same ground."
                    if lang == "en"
                    else "वीडियो लोड नहीं हो सका। नीचे दिए चरण वही जानकारी देते हैं।"
                )
        else:
            st.caption(
                "A short video walkthrough will appear here once it's added."
                if lang == "en"
                else "एक छोटा वीडियो यहाँ जल्द जोड़ा जाएगा।"
            )

        for heading, detail in _steps(lang):
            st.markdown(f"**{heading}** — {detail}")
