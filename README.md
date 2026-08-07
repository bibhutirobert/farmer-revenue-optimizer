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
│   ├── 3_Recommendations.py        # Step 3: results + PDF download + save-to-account
│   ├── 4_Dashboard.py              # Internal risk panel — admin-only (Google sign-in gate)
│   └── 5_My_Reports.py             # Signed-in farmer's saved report history
├── core/                           # Pure Python domain layer (no Streamlit dependency)
│   ├── models.py
│   ├── crop_data.py
│   ├── cost_calculator.py
│   ├── recommendation_engine.py
│   ├── report_generator.py
│   ├── auth_service.py             # Google sign-in (OIDC) + admin allowlist gate
│   ├── db_service.py                # Supabase Postgres client (usage events, farm records)
│   ├── storage_service.py          # Supabase Storage client (saved PDF reports)
│   └── scene_provider.py           # Abstract 3D hook (Skyfall-GS ready)
├── utils/
│   ├── map_utils.py
│   └── pdf_utils.py
├── data/
│   ├── crops.json                  # 15 major Indian crops, MSP/FRP 2023-24
│   └── intercrop_rules.json        # 13 intercrop compatibility rules
├── supabase/
│   └── schema.sql                  # Postgres schema + RLS + storage bucket setup
├── tests/
│   ├── test_cost_calculator.py
│   ├── test_recommendation_engine.py
│   ├── test_report_generator.py
│   ├── test_map_utils.py
│   ├── test_auth_service.py
│   ├── test_db_service.py
│   └── test_storage_service.py
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

**Google Sign-In must be configured before the advisory flow will work** — an
account is required for every farmer (see "Security & data protection" below).
Add `[auth]`, `[admin]`, and `[supabase]` to your app's Secrets before or
right after deploying.

---

## Deploy to Hugging Face Spaces (alternative)

1. Create a new Space at https://huggingface.co/spaces
2. Select **Streamlit** as the SDK
3. Push the repo — HF Spaces auto-detects `requirements.txt` and `app.py`

---

## Security & data protection

The app runs entirely server-side (Streamlit) — a browser never talks to the
database or storage directly, only this Python backend does. That shapes the
whole security model:

| Layer | How it's protected |
|---|---|
| **Secrets** | Never hardcoded. Read from `.streamlit/secrets.toml` (git-ignored) or the platform's secrets manager. `.streamlit/secrets.toml.example` ships only placeholder values. |
| **Auth** | Google Sign-In via Streamlit's native OIDC (`core/auth_service.py`) is **mandatory** — every farmer must have an account before using Land Selection, Farm Details, Recommendations, or My Reports (`require_login()`). The internal Dashboard needs sign-in **plus** an email on the `[admin] emails` allowlist (`require_admin()`), and admin status lives only in that secrets file, never in the database, so it can't be escalated by editing a row. Every gate fails closed — unconfigured or logged-out always means "denied", never "allowed" or silent guest access. Mobile-number verification is a full OTP implementation (`core/phone_auth_service.py`) — see "Mobile OTP" below. |
| **Database** | Supabase Postgres (`core/db_service.py`), connected with the **service role** key (server-side only, never sent to the browser). Row Level Security is enabled on every table with no policies granted to `anon`/`authenticated` — even a leaked public key returns zero rows. Per-user access (a farmer only sees their own saved reports) is enforced in application code, scoped by the authenticated `owner_email`. See `supabase/schema.sql` for the full rationale. |
| **Storage** | Supabase Storage bucket for saved PDF reports (`core/storage_service.py`) is private, objects are namespaced by a one-way hash of the owner's email (never the raw address), and access is only ever via short-lived (1 hour) signed URLs minted server-side for the authenticated owner. |
| **Transport** | Streamlit Cloud / any standard host serves the app over HTTPS by default. |
| **Logging** | Usage events (crop, margin, risk flag, and the signed-in `owner_email`) go to Supabase; a legacy Google Sheets webhook and local file remain as optional/fallback sinks. Every sink is best-effort — a missing secret or failed write never crashes the app. |
| **Data minimization** | The farmer-facing app never exposes another user's data — "My Reports" is scoped to the signed-in account only. Portfolio-level analytics, the full account list (`profiles` table — name, email, phone, login history), and aggregate risk data are visible on the Dashboard to admins only; nothing about other farmers is ever shown to a farmer. |

### What's captured about each signed-in user

On every sign-in, `core/auth_service.sync_profile_once()` upserts a `profiles`
row (`supabase/schema.sql`) with everything Google's OIDC token provides —
email, full/given/family name, profile picture URL, locale, and the stable
Google subject id — plus app-specific fields the token doesn't carry:
preferred language, self-reported state, and an optional mobile number
(captured on Page 1, unverified until OTP is wired in). This is the
"complete picture" record referenced above; admins can browse it under
**Dashboard → Farmer Accounts**, farmers only ever see their own profile
implicitly through their own saved reports.

### Authentication setup

1. In Google Cloud Console → APIs & Services → Credentials, create an OAuth
   2.0 Client ID (type: Web application). Add an authorized redirect URI —
   `http://localhost:8501/oauth2callback` for local dev, or
   `https://<your-app>.streamlit.app/oauth2callback` in production.
2. Add the `[auth]` block to `.streamlit/secrets.toml` (see
   `secrets.toml.example`) with `client_id`, `client_secret`, `redirect_uri`,
   and a random `cookie_secret`.
3. Add your own email under `[admin] emails` to unlock the Dashboard.

### Mobile OTP

`core/phone_auth_service.py` is a complete one-time-code implementation, not
a placeholder. It generates codes with `secrets`, stores only an
HMAC-SHA256 digest bound to the phone number (a database dump yields no
usable codes), expires them after 5 minutes, caps verification attempts at 5
(a 6-digit code is only 10⁶ combinations — without a cap it is brute-forceable),
rate-limits sends to 3 per 15 minutes per number, and burns each challenge on
use so a code can't be replayed. Comparison is constant-time.

Configure a provider under `[sms]`:

| `provider` | What it does |
|---|---|
| `dev` | **Sends no SMS** — shows the code on screen so you can exercise the whole flow with no paid account. Never ship this to production: it would let anyone "verify" any number they type. |
| `msg91` | India-first. Needs a DLT/TRAI-registered sender id + template id (that registration is a real regulatory step and takes a few days). |
| `twilio` | Needs `account_sid`, `auth_token`, `from_number`. |

Omit `[sms]` entirely and verification stays off — the app then just captures
numbers unverified, and says so in the UI.

**Phone as a *login* method** (rather than verification on an existing
account) is deliberately not done with this module. It needs a durable
session for someone who never touches Google, and Streamlit's `st.login()`
is OIDC-only with no cookie-writing API — hand-rolling that is where phone
auth usually goes wrong. The clean route is to add a second OIDC provider
that does SMS auth (Supabase Auth, Firebase, or an Auth0 phone connection)
to `[auth]` and call `st.login("<provider>")`. Because every page gates on
`auth_service.require_login()` rather than on Google specifically, that's a
config change plus one button — not a rewrite.

### Database & storage setup (Supabase)

1. Create a free project at [supabase.com](https://supabase.com).
2. Open the SQL editor and run `supabase/schema.sql` — creates
   `usage_events`, `farm_records`, `profiles`, `otp_challenges`, and enables
   RLS on all four.
3. Under Storage, create a bucket named `farm-reports` and leave **Public**
   turned **off**.
4. Add the `[supabase]` block to secrets with your project `url` and the
   **service role** key (Project Settings → API) — not the anon/public key.

`[auth]` is required — without it, sign-in is unavailable and the entire
farmer flow (Land Selection onward) stays locked, by design. `[supabase]` is
additive on top of that: without it, sign-in still works but nothing is
saved (no history, no admin account list) and the Dashboard falls back to
its synthetic demo dataset.

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
