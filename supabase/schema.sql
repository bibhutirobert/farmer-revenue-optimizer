-- Farmer Revenue Optimizer — Supabase schema
-- =============================================
-- Run this once in the Supabase SQL editor of a new/existing project.
--
-- SECURITY MODEL
-- ----------------
-- This app is server-rendered (Streamlit). Browsers never talk to Supabase
-- directly — only the Python backend does, using the SERVICE ROLE key
-- (see core/db_service.py). That key bypasses Row Level Security by design.
--
-- Row Level Security is enabled on every table below, and deliberately NO
-- policies are granted to the `anon` or `authenticated` Postgres roles.
-- That means: if the project's `anon`/public key ever leaked, or someone
-- guessed the project URL, they would get ZERO rows back — RLS with no
-- policy = deny all for those roles. Only the service role (used
-- exclusively, server-side, in this codebase) can read or write.
--
-- Per-user isolation (a farmer only ever sees their own saved reports) is
-- therefore enforced in application code (core/db_service.py), which
-- always filters by owner_email taken from the authenticated Streamlit
-- session (st.user.email) — never from user-editable input.

-- ── usage_events ────────────────────────────────────────────────────────────
-- One row per recommendation run. Powers the internal Risk Intelligence
-- dashboard (pages/4_Dashboard.py). No PII beyond an optional owner_email
-- for logged-in farmers; anonymous usage is logged with owner_email = NULL.

create table if not exists usage_events (
    id              bigint generated always as identity primary key,
    created_at      timestamptz not null default now(),
    ts              timestamptz not null,
    owner_email     text,                    -- null for anonymous/guest usage
    crop            text not null,
    state           text not null,
    season          text not null,
    acreage         numeric not null,
    gross_revenue   numeric not null,
    total_cost      numeric not null,
    net_margin      numeric not null,
    margin_per_acre numeric,
    risk_flag       boolean not null default false,
    price_source    text,
    soil_code       text,
    climate_zone    text,
    llm_used        boolean not null default false,
    irrigation      text
);

create index if not exists usage_events_ts_idx on usage_events (ts desc);
create index if not exists usage_events_owner_idx on usage_events (owner_email);

alter table usage_events enable row level security;
-- No policies granted -> anon/authenticated get zero rows. Service role only.

-- ── farm_records ────────────────────────────────────────────────────────────
-- A signed-in farmer's saved farm runs ("My Reports"), including a pointer
-- to their PDF in Supabase Storage (see storage bucket setup below).

create table if not exists farm_records (
    id                  uuid primary key default gen_random_uuid(),
    created_at          timestamptz not null default now(),
    owner_email         text not null,
    crop                text not null,
    acreage             numeric not null,
    state               text not null,
    season              text not null,
    irrigation_type     text,
    lat                 double precision,
    lng                 double precision,
    soil_type           text,
    climate_zone        text,
    gross_revenue       numeric,
    total_cost          numeric,
    net_margin          numeric,
    risk_flag           boolean not null default false,
    report_storage_path text                 -- path in the farm-reports bucket
);

create index if not exists farm_records_owner_idx on farm_records (owner_email, created_at desc);

alter table farm_records enable row level security;
-- No policies granted -> anon/authenticated get zero rows. Service role only.

-- ── profiles ─────────────────────────────────────────────────────────────────
-- One row per signed-in user (farmer or admin), keyed by email. Populated by
-- core/auth_service.py.sync_profile_once() from the Google OIDC claims on
-- every new sign-in — this is the "complete picture" record: everything
-- Google's identity token gives us, plus the app-specific fields (phone
-- number for the future OTP flow, preferred language) that the OAuth claims
-- don't carry. Admin status is intentionally NOT stored here — it stays
-- solely in the [admin] emails allowlist in secrets, so a database row can
-- never be edited to grant admin access.

create table if not exists profiles (
    email             text primary key,
    google_sub        text,                  -- Google's stable OIDC subject id
    full_name         text,
    given_name        text,
    family_name       text,
    picture_url       text,
    locale            text,
    preferred_lang    text,                  -- 'en' | 'hi', last language used in-app
    phone_number      text,                  -- captured now, unverified — see core/phone_auth_service.py
    phone_verified    boolean not null default false,
    state             text,                  -- self-reported home state, optional
    first_login_at    timestamptz not null default now(),
    last_login_at     timestamptz not null default now()
);

alter table profiles enable row level security;
-- No policies granted -> anon/authenticated get zero rows. Service role only.

-- ── Storage bucket for saved PDF reports ────────────────────────────────────
-- Create via the Supabase dashboard (Storage -> New bucket) or the snippet
-- below. MUST be private (public = false). Objects are named
-- "<sha256(owner_email)[:24]>/<filename>.pdf" (see core/storage_service.py)
-- so the raw email is never exposed even if someone lists the bucket.
--
-- insert into storage.buckets (id, name, public)
-- values ('farm-reports', 'farm-reports', false)
-- on conflict (id) do nothing;
--
-- No storage.objects policies are granted to anon/authenticated either —
-- all reads/writes go through the service role, and farmers only ever get
-- a short-lived signed URL (1 hour TTL) minted server-side for their own
-- report, generated on demand in core/storage_service.py.
