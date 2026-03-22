# Farmer Revenue Optimizer — Cloud Edition

> Help small and medium Indian farmers earn more, spend less — in their own language.

---

## The Problem

A small farmer in India makes most of her crop decisions based on what neighbours grew last year,
or what the local trader recommends. She has no easy way to know:

- Whether her current crop is giving a fair return vs. its input cost
- Which crops could grow alongside hers to increase income with zero extra land
- Whether switching irrigation method or seed type would actually save money
- What government MSP (minimum support price) her crop is entitled to

This app puts a structured, bilingual advisory report in her hands — or her advisor's — in under
3 minutes, on any phone or computer with a browser.

---

## What it does

| Step | Action |
|---|---|
| 1. Select your field | Click on your farm on a live satellite map. No address needed. |
| 2. Enter crop details | Crop, acreage, yield, irrigation type, state, season. Optionally override costs. |
| 3. Get your report | Revenue estimate, net margin, itemised cost table, intercropping ideas, seasonal tips, downloadable PDF. |

Fully bilingual: English + Hindi throughout the UI. Toggle language at any time.

---

## Repo structure

```
farmer-revenue-optimizer-cloud/
├── app.py                          # Landing page (Streamlit entry point)
├── pages/
│   ├── 1_Land_Selection.py         # Step 1: satellite map + lat/lng capture
│   ├── 2_Farm_Details.py           # Step 2: crop + cost input form
│   └── 3_Recommendations.py        # Step 3: results + PDF download
├── core/                           # Pure Python domain layer (no Streamlit dependency)
│   ├── models.py
│   ├── crop_data.py
│   ├── cost_calculator.py
│   ├── recommendation_engine.py
│   ├── report_generator.py
│   └── scene_provider.py           # Abstract 3D hook (Skyfall-GS ready)
├── utils/
│   ├── map_utils.py
│   └── pdf_utils.py
├── data/
│   ├── crops.json                  # 15 major Indian crops, MSP/FRP 2023-24
│   └── intercrop_rules.json        # 13 intercrop compatibility rules
├── tests/
│   ├── test_cost_calculator.py
│   ├── test_recommendation_engine.py
│   ├── test_report_generator.py
│   └── test_map_utils.py
├── .streamlit/config.toml
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## How to run locally

```bash
git clone https://github.com/<your-username>/farmer-revenue-optimizer-cloud.git
cd farmer-revenue-optimizer-cloud

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

streamlit run app.py
```

Opens at http://localhost:8501

---

## How to run tests

```bash
pytest
```

---

## Deploy to Streamlit Community Cloud (free)

1. Push this repo to GitHub (public or private)
2. Go to https://share.streamlit.io and sign in with GitHub
3. Click **New app**
4. Set repository, branch `main`, main file `app.py`
5. Click **Deploy**

No secrets or environment variables required for v1.

---

## Deploy to Hugging Face Spaces (alternative)

1. Create a new Space at https://huggingface.co/spaces
2. Select **Streamlit** as the SDK
3. Push the repo — HF Spaces auto-detects `requirements.txt` and `app.py`

---

## Skyfall-GS 3D terrain view — how to plug it in

The integration point is at `core/scene_provider.py`. The abstract class `BaseSceneProvider`
defines one method:

```python
def render(self, container, lat: float, lng: float, bbox: Optional[dict] = None) -> None: ...
```

To add a real 3D module:

1. Create `core/skyfall_scene_provider.py` extending `BaseSceneProvider`
2. Implement `render()` using `st.components.v1.iframe()` or `st.components.v1.html()`
3. In `pages/1_Land_Selection.py`, change one import:

```python
# Before
from core.scene_provider import default_scene_provider
# After
from core.skyfall_scene_provider import SkyFallSceneProvider
default_scene_provider = SkyFallSceneProvider(api_key=st.secrets["SKYFALL_KEY"])
```

Zero changes to any other file.

---

## Future upgrade paths

| Feature | Where to plug in |
|---|---|
| ML yield prediction | `core/recommendation_engine.py` — replace `run()` body, keep signature |
| Claude API narrative | `recommendation_engine._generate_narrative()` — swap f-string for API call |
| Real-time mandi prices | `core/crop_data.py` — replace static MSP with Agmarknet API |
| Hindi PDF | `core/report_generator.py` — add Noto Sans Devanagari `.ttf` via `pdf.add_font()` |
| Weather integration | New `utils/weather_utils.py` feeding into seasonal_tips |

---

## Data sources

- MSP / FRP 2023-24: Government of India, CACP
- Typical yields: ICAR crop production guidelines
- Intercropping rules: ICAR, state KVK publications, traditional farming literature
- Satellite imagery: Esri World Imagery (free CDN, no API key required)

---

## Disclaimer

This application provides automated advisory output for informational purposes only.
Always verify with your local Krishi Vigyan Kendra (KVK) or agriculture extension officer
before making financial decisions.
