"""
JAPS – Candidate Placement Analytics Dashboard
================================================
Reads candidate data from the PostgreSQL database that was populated in
`JAPS_Analysis_prediction.ipynb` (table: job_placement_data) and renders
a KPI dashboard with Streamlit.

Run:
    streamlit run app.py

Configure the database connection with ONE of the following (checked in order):
    1. Environment variable  DATABASE_URL
    2. Streamlit secrets     .streamlit/secrets.toml -> DATABASE_URL = "..."
    3. Sidebar CSV upload (fallback / offline demo mode)

IMPORTANT SECURITY NOTE
------------------------
A hardcoded connection string is included below as a fallback so the app
works out of the box, matching the notebook. Since this password now lives
in a plain-text file, treat it as exposed: rotate it in the Render
dashboard periodically, don't push this file to a public repo, and prefer
setting DATABASE_URL as an environment variable or Streamlit secret in any
shared/deployed environment.
"""

import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# --------------------------------------------------------------------------- #
# Page configuration & styling
# --------------------------------------------------------------------------- #

st.set_page_config(
    page_title="JAPS Placement Analytics Dashboard",
    page_icon="Logo-PTS.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
/* Overall page */
.main {
    background-color: #f6f8fb;
}

/* Header */
.dashboard-header {
    padding: 1.2rem 1.6rem;
    border-radius: 14px;
    background: linear-gradient(135deg, #1f3c88 0%, #3a6ea5 100%);
    color: white;
    margin-bottom: 1.4rem;
}
.dashboard-header h1 {
    margin: 0;
    font-size: 1.9rem;
    font-weight: 700;
}
.dashboard-header p {
    margin: 0.3rem 0 0 0;
    opacity: 0.9;
    font-size: 0.95rem;
}

/* KPI cards */
.kpi-card {
    background: white;
    border-radius: 14px;
    padding: 1.1rem 1.2rem;
    box-shadow: 0 2px 10px rgba(20, 30, 60, 0.06);
    border-left: 5px solid var(--accent, #3a6ea5);
    height: 100%;
}
.kpi-label {
    font-size: 0.82rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: #6b7280;
    margin-bottom: 0.35rem;
}
.kpi-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #111827;
    line-height: 1.1;
}
.kpi-sub {
    font-size: 0.78rem;
    color: #9ca3af;
    margin-top: 0.3rem;
}

/* Section titles */
.section-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #1f2937;
    margin: 1.6rem 0 0.6rem 0;
}

/* Data source badge */
.badge {
    display: inline-block;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-db { background: #dcfce7; color: #166534; }
.badge-csv { background: #fef3c7; color: #92400e; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

TABLE_NAME = "job_placement_data"
LOCAL_CSV_FALLBACK = "HR_Job_Placement_Cleaned_Engineered.csv"

# Fallback connection string (used only if DATABASE_URL is not set via env
# var or Streamlit secrets). Matches the credentials used in the notebook.
DEFAULT_DATABASE_URL = (
    "postgresql://japs_user:soVpMsGaQ4F44Vqsy3E2VE0yfGxwwvAJ"
    "@dpg-da585k3tqb8s739o5jig-a.virginia-postgres.render.com/japs_db_ne2r"
)


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #

@st.cache_resource(show_spinner=False)
def get_engine(database_url: str):
    """Create (and cache) a SQLAlchemy engine for the given connection string."""
    return create_engine(database_url, pool_pre_ping=True)


def resolve_database_url() -> str | None:
    """Look for a DB connection string in env vars, then Streamlit secrets,
    then fall back to the hardcoded default so the app works out of the box."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    return DEFAULT_DATABASE_URL


@st.cache_data(show_spinner="Loading candidate data from the database...", ttl=600)
def load_from_database(database_url: str) -> pd.DataFrame:
    engine = get_engine(database_url)
    with engine.connect() as conn:
        df = pd.read_sql(text(f"SELECT * FROM {TABLE_NAME}"), conn)
    return df


@st.cache_data(show_spinner="Loading candidate data from CSV...")
def load_from_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)


def normalize_status(df: pd.DataFrame) -> pd.DataFrame:
    """Add a boolean `is_placed` column regardless of whether `status` is
    stored as 0/1 or as 'Placed' / 'Not Placed' strings."""
    df = df.copy()
    if df["status"].dtype == object:
        df["is_placed"] = df["status"].astype(str).str.strip().str.lower().eq("placed")
    else:
        df["is_placed"] = df["status"].astype(float).eq(1)
    return df


# --------------------------------------------------------------------------- #
# Sidebar — data source & filters
# --------------------------------------------------------------------------- #

st.sidebar.title("⚙️ Data Source")

database_url = resolve_database_url()
data_source = None
df_raw = None

if database_url:
    try:
        df_raw = load_from_database(database_url)
        data_source = "Database (PostgreSQL)"
    except SQLAlchemyError as exc:
        st.sidebar.error(f"Could not connect to the database:\n{exc}")

if df_raw is None:
    st.sidebar.info(
        "No live database connection found (or the connection failed). "
        "Upload the cleaned CSV to explore the dashboard instead."
    )
    uploaded_file = st.sidebar.file_uploader(
        "Upload HR_Job_Placement_Cleaned_Engineered.csv", type=["csv"]
    )
    if uploaded_file is not None:
        df_raw = load_from_csv(uploaded_file)
        data_source = "CSV upload"
    elif os.path.exists(LOCAL_CSV_FALLBACK):
        df_raw = load_from_csv(LOCAL_CSV_FALLBACK)
        data_source = "Local CSV fallback"

if df_raw is None:
    st.warning(
        "No data available yet. Set the `DATABASE_URL` environment variable "
        "(or add it to `.streamlit/secrets.toml`), or upload the CSV file "
        "from the sidebar to get started."
    )
    st.stop()

df = normalize_status(df_raw)

st.sidebar.success(f"Loaded {len(df):,} records")
if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.title("🔎 Filters")


def sidebar_multiselect(column: str, label: str):
    if column in df.columns:
        options = sorted(df[column].dropna().unique().tolist())
        return st.sidebar.multiselect(label, options, default=options)
    return None


company_tier_filter = sidebar_multiselect("company_tier", "Company Tier")
experience_cat_filter = sidebar_multiselect("experience_category", "Experience Category")
academic_band_filter = sidebar_multiselect("academic_band", "Academic Band")

filtered_df = df.copy()
if company_tier_filter is not None:
    filtered_df = filtered_df[filtered_df["company_tier"].isin(company_tier_filter)]
if experience_cat_filter is not None:
    filtered_df = filtered_df[filtered_df["experience_category"].isin(experience_cat_filter)]
if academic_band_filter is not None:
    filtered_df = filtered_df[filtered_df["academic_band"].isin(academic_band_filter)]

if filtered_df.empty:
    st.warning("No candidates match the selected filters.")
    st.stop()


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #

badge_class = "badge-db" if data_source and "Database" in data_source else "badge-csv"
st.markdown(
    f"""
    <div class="dashboard-header">
        <h1>📊 JAPS Candidate Placement Analytics Dashboard</h1>
        <p>
            Live view of candidate placement performance &nbsp;·&nbsp;
            <span class="badge {badge_class}">{data_source}</span>
            &nbsp;·&nbsp; Last refreshed: {datetime.now().strftime('%d %b %Y, %H:%M')}
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# KPI calculations
# --------------------------------------------------------------------------- #

total_candidates = len(filtered_df)
placed_count = int(filtered_df["is_placed"].sum())

placement_rate = (placed_count / total_candidates) * 100
job_acceptance_rate = placement_rate  # candidates who accepted = candidates placed
offer_dropout_rate = 100 - placement_rate

avg_interview_score = (
    filtered_df["interview_average"].mean()
    if "interview_average" in filtered_df.columns
    else float("nan")
)
avg_skill_match = (
    filtered_df["skills_match_percentage"].mean()
    if "skills_match_percentage" in filtered_df.columns
    else float("nan")
)

if "placement_probability_score" in filtered_df.columns:
    high_risk_candidates = int((filtered_df["placement_probability_score"] < 50).sum())
    high_risk_percentage = (high_risk_candidates / total_candidates) * 100
else:
    high_risk_candidates, high_risk_percentage = 0, float("nan")


def kpi_card(label: str, value: str, sub: str, accent: str):
    st.markdown(
        f"""
        <div class="kpi-card" style="--accent:{accent}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# KPI cards — row 1
# --------------------------------------------------------------------------- #

st.markdown('<div class="section-title">Key Metrics</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Total Candidates", f"{total_candidates:,}", "in current filter", "#1f3c88")
with c2:
    kpi_card("Placement Rate", f"{placement_rate:.2f}%", f"{placed_count:,} placed", "#16a34a")
with c3:
    kpi_card("Job Acceptance Rate", f"{job_acceptance_rate:.2f}%", "offers accepted", "#0891b2")
with c4:
    kpi_card("Avg. Interview Score", f"{avg_interview_score:.2f}", "out of 100", "#7c3aed")

c5, c6, c7 = st.columns(3)
with c5:
    kpi_card("Avg. Skills Match", f"{avg_skill_match:.2f}%", "candidate ↔ role fit", "#ea580c")
with c6:
    kpi_card("Offer Dropout Rate", f"{offer_dropout_rate:.2f}%", "not placed", "#dc2626")
with c7:
    kpi_card(
        "High-Risk Candidates",
        f"{high_risk_percentage:.2f}%",
        f"{high_risk_candidates:,} candidates (score < 50)",
        "#b91c1c",
    )


# --------------------------------------------------------------------------- #
# Charts
# --------------------------------------------------------------------------- #

st.markdown('<div class="section-title">Placement Breakdown</div>', unsafe_allow_html=True)

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    status_counts = (
        filtered_df["is_placed"]
        .map({True: "Placed", False: "Not Placed"})
        .value_counts()
        .reset_index()
    )
    status_counts.columns = ["Status", "Candidates"]
    fig_status = px.pie(
        status_counts,
        names="Status",
        values="Candidates",
        color="Status",
        color_discrete_map={"Placed": "#16a34a", "Not Placed": "#dc2626"},
        hole=0.55,
        title="Placement Status Distribution",
    )
    fig_status.update_layout(margin=dict(t=50, b=0, l=0, r=0))
    st.plotly_chart(fig_status, use_container_width=True)

with chart_col2:
    if "company_tier" in filtered_df.columns:
        tier_rate = (
            filtered_df.groupby("company_tier")["is_placed"]
            .mean()
            .mul(100)
            .reset_index(name="Placement Rate (%)")
            .sort_values("Placement Rate (%)", ascending=False)
        )
        fig_tier = px.bar(
            tier_rate,
            x="company_tier",
            y="Placement Rate (%)",
            color="Placement Rate (%)",
            color_continuous_scale="Blues",
            title="Placement Rate by Company Tier",
        )
        fig_tier.update_layout(margin=dict(t=50, b=0, l=0, r=0), coloraxis_showscale=False)
        st.plotly_chart(fig_tier, use_container_width=True)
    else:
        st.info("Column `company_tier` not found in the data.")

chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    if "experience_category" in filtered_df.columns:
        exp_rate = (
            filtered_df.groupby("experience_category")["is_placed"]
            .mean()
            .mul(100)
            .reset_index(name="Placement Rate (%)")
        )
        fig_exp = px.bar(
            exp_rate,
            x="experience_category",
            y="Placement Rate (%)",
            title="Placement Rate by Experience Category",
            color_discrete_sequence=["#3a6ea5"],
        )
        fig_exp.update_layout(margin=dict(t=50, b=0, l=0, r=0))
        st.plotly_chart(fig_exp, use_container_width=True)
    else:
        st.info("Column `experience_category` not found in the data.")

with chart_col4:
    if "skills_match_percentage" in filtered_df.columns and "interview_average" in filtered_df.columns:
        fig_scatter = px.scatter(
            filtered_df,
            x="skills_match_percentage",
            y="interview_average",
            color=filtered_df["is_placed"].map({True: "Placed", False: "Not Placed"}),
            color_discrete_map={"Placed": "#16a34a", "Not Placed": "#dc2626"},
            title="Skills Match vs. Interview Score",
            labels={"color": "Status"},
            opacity=0.6,
        )
        fig_scatter.update_layout(margin=dict(t=50, b=0, l=0, r=0))
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("Required columns for this chart are not present.")


# --------------------------------------------------------------------------- #
# Data table
# --------------------------------------------------------------------------- #

st.markdown('<div class="section-title">Candidate Records</div>', unsafe_allow_html=True)
st.dataframe(filtered_df, use_container_width=True, height=380)

st.download_button(
    "⬇️ Download filtered data as CSV",
    data=filtered_df.to_csv(index=False).encode("utf-8"),
    file_name="japs_filtered_candidates.csv",
    mime="text/csv",
)

st.caption(
    "Data source: PostgreSQL table `job_placement_data` "
    "(populated in JAPS_Analysis_prediction.ipynb), with CSV fallback."
)

# ============================================================
# FOOTER
# ============================================================

st.markdown("---")
st.markdown(
    "<div style='text-align:center;'>Created by <b>Pearlraj</b></div>",
    unsafe_allow_html=True
)