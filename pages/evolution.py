"""
Evolution Page - Codebase Evolution Intelligence System.
Displays comprehensive Plotly time-series visualizations for:
- Commits over time
- Lines added vs deleted
- Cumulative code growth
- Contributor activity
- Bug-fix activity
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from analysis import get_commits_df, get_repository_summary
from chart_theme import apply_chart_theme


def render_evolution():
    repo_id = st.session_state.get("selected_repo_id")
    if not repo_id:
        st.info("👈 Please select or analyze a GitHub repository from the sidebar to view evolution metrics.")
        return

    summary = get_repository_summary(repo_id)
    commits_df = get_commits_df(repo_id)

    st.title("📈 Codebase Evolution Analytics")
    st.caption(f"Repository: **{summary.get('name', 'N/A')}** | Tracking long-term trajectory, velocity, and maintenance")
    st.markdown("---")

    if commits_df.empty:
        st.warning("No commit data found for this repository.")
        return

    # Prepare time-series dataframe
    df = commits_df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df["is_bug"] = df["Possible Bug Fix"] == "Yes"
    df["Net Lines"] = df["Lines Added"] - df["Lines Deleted"]

    # Controls
    col_ctrl1, col_ctrl2 = st.columns([2, 4])
    with col_ctrl1:
        time_frequency = st.selectbox(
            "Aggregation Interval",
            options=["Monthly (ME)", "Weekly (W)", "Daily (D)"],
            index=0
        )
    with col_ctrl2:
        freq_alias = "ME" if "Monthly" in time_frequency else ("W" if "Weekly" in time_frequency else "D")
        st.caption(f"Aggregating **{len(df):,}** commits by **{time_frequency.split()[0]}** intervals.")

    # Resample time series
    df_ts = df.resample(freq_alias, on="Date").agg({
        "Commit Hash": "count",
        "Lines Added": "sum",
        "Lines Deleted": "sum",
        "Net Lines": "sum",
        "is_bug": "sum",
        "Author": "nunique"
    }).reset_index().rename(columns={
        "Commit Hash": "Commits",
        "is_bug": "Bug Fix Commits",
        "Author": "Active Contributors"
    })

    # Sort chronological for cumulative growth calculation
    df_ts = df_ts.sort_values(by="Date")
    df_ts["Cumulative Code Growth (LOC)"] = df_ts["Net Lines"].cumsum()
    df_ts["Cumulative Commits"] = df_ts["Commits"].cumsum()

    # Chart 1: Commits Over Time
    st.subheader("1. 📅 Commit Velocity Over Time")
    fig_commits = go.Figure()
    fig_commits.add_trace(go.Bar(
        x=df_ts["Date"],
        y=df_ts["Commits"],
        name="Total Commits",
        marker_color="#2563eb",
        marker_line_color="#1d4ed8",
        marker_line_width=1,
        opacity=0.9
    ))
    fig_commits.add_trace(go.Scatter(
        x=df_ts["Date"],
        y=df_ts["Commits"].rolling(window=3, min_periods=1).mean(),
        name="3-Period Moving Avg",
        line=dict(color="#4338ca", width=3)
    ))
    fig_commits.update_layout(
        xaxis_title="Date",
        yaxis_title="Commits Count",
        hovermode="x unified"
    )
    apply_chart_theme(fig_commits, height=330, show_legend=True)
    st.plotly_chart(fig_commits, use_container_width=True)

    # Chart 2: Lines Added vs Deleted
    st.subheader("2. ⚖️ Lines Added vs Deleted Over Time")
    fig_churn = go.Figure()
    fig_churn.add_trace(go.Bar(
        x=df_ts["Date"],
        y=df_ts["Lines Added"],
        name="Lines Added (+)",
        marker_color="#10b981",
        marker_line_color="#047857",
        marker_line_width=1,
        opacity=0.9
    ))
    fig_churn.add_trace(go.Bar(
        x=df_ts["Date"],
        y=-df_ts["Lines Deleted"],
        name="Lines Deleted (-)",
        marker_color="#ef4444",
        marker_line_color="#b91c1c",
        marker_line_width=1,
        opacity=0.9
    ))
    fig_churn.update_layout(
        barmode="relative",
        xaxis_title="Date",
        yaxis_title="Code Churn (Lines)",
        hovermode="x unified"
    )
    apply_chart_theme(fig_churn, height=330, show_legend=True)
    st.plotly_chart(fig_churn, use_container_width=True)

    # Chart 3: Cumulative Code Growth
    st.subheader("3. 🌱 Cumulative Code Growth (Net Lines Over Time)")
    fig_growth = px.area(
        df_ts,
        x="Date",
        y="Cumulative Code Growth (LOC)",
        color_discrete_sequence=["#8b5cf6"],
    )
    fig_growth.update_traces(
        line=dict(color="#6d28d9", width=2.5),
    )
    fig_growth.update_layout(
        xaxis_title="Date",
        yaxis_title="Net Lines of Code",
        hovermode="x unified"
    )
    apply_chart_theme(fig_growth, height=330, show_legend=False)
    st.plotly_chart(fig_growth, use_container_width=True)

    # Row with Charts 4 & 5
    col_ev1, col_ev2 = st.columns(2)

    with col_ev1:
        st.subheader("4. 🐛 Heuristic Bug-Fix Activity Over Time")
        fig_bugs = go.Figure()
        fig_bugs.add_trace(go.Bar(
            x=df_ts["Date"],
            y=df_ts["Bug Fix Commits"],
            name="Possible Bug Fixes",
            marker_color="#f97316",
            marker_line_color="#c2410c",
            marker_line_width=1,
            opacity=0.9
        ))
        fig_bugs.update_layout(
            xaxis_title="Date",
            yaxis_title="Bug-Fix Commits",
            hovermode="x unified"
        )
        apply_chart_theme(fig_bugs, height=320, show_legend=False)
        st.plotly_chart(fig_bugs, use_container_width=True)

    with col_ev2:
        st.subheader("5. 👥 Active Contributors Over Time")
        fig_devs = go.Figure()
        fig_devs.add_trace(go.Scatter(
            x=df_ts["Date"],
            y=df_ts["Active Contributors"],
            name="Active Contributors",
            mode="lines+markers",
            line=dict(color="#06b6d4", width=3),
            marker=dict(size=7, color="#0891b2", line=dict(color="#0f172a", width=1.5))
        ))
        fig_devs.update_layout(
            xaxis_title="Date",
            yaxis_title="Unique Contributors",
            hovermode="x unified"
        )
        apply_chart_theme(fig_devs, height=320, show_legend=False)
        st.plotly_chart(fig_devs, use_container_width=True)


render_evolution()
