import streamlit as st
import pandas as pd


JAPS_Cleaned_df = pd.read_csv("D:\Project3_JAPS_Analysis&prediction\HR_Job_Placement_Cleaned_Dataset.csv")


st.set_page_config(
    page_title="JAPS Placement Analytics Dashboard",
    layout="wide"
)


st.title(
    "📊 JAPS Candidate Placement Analytics Dashboard"
)

# KPI Calculations


total_candidates = len(JAPS_Cleaned_df)


# Placement Rate

placement_rate = (
    JAPS_Cleaned_df['status']
    .mean()
    * 100
)


# Job Acceptance Rate

acceptance_rate = (
    JAPS_Cleaned_df[
        JAPS_Cleaned_df['status']==1
    ]
    .shape[0]
    /
    total_candidates
) * 100


# Average Interview Score

avg_interview_score = (
    JAPS_Cleaned_df[
        'interview_average'
    ]
    .mean()
)


# Average Skills Match

avg_skill_match = (
    JAPS_Cleaned_df[
        'skills_match_percentage'
    ]
    .mean()
)


# Offer Dropout Rate

offer_dropout_rate = (
    JAPS_Cleaned_df[
        'status'
    ]
    .value_counts(normalize=True)
    .get(0,0)
)*100


# High Risk Candidates

high_risk_candidates = (
    JAPS_Cleaned_df[
        JAPS_Cleaned_df[
            'placement_probability_score'
        ] < 50
    ]
    .shape[0]
)


high_risk_percentage = (
    high_risk_candidates /
    total_candidates
)*100




# KPI Cards


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Total Candidates",
        f"{total_candidates:,}"
    )


with col2:

    st.metric(
        "Placement Rate",
        f"{placement_rate:.2f}%"
    )


with col3:

    st.metric(
        "Job Acceptance Rate",
        f"{acceptance_rate:.2f}%"
    )


with col4:

    st.metric(
        "Average Interview Score",
        f"{avg_interview_score:.2f}"
    )



col5, col6, col7 = st.columns(3)


with col5:

    st.metric(
        "Average Skills Match %",
        f"{avg_skill_match:.2f}%"
    )


with col6:

    st.metric(
        "Offer Dropout Rate",
        f"{offer_dropout_rate:.2f}%"
    )


with col7:

    st.metric(
        "High Risk Candidates",
        f"{high_risk_percentage:.2f}%"
    )