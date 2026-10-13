"""
Overview Page - Codebase Evolution Intelligence System.
Displays high-level KPI cards, repository metadata, and essential summary charts.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from analysis import (
    get_repository_summary,
    get_commits_df,
    get_files_df,
    get_hotspots_df
)
from chart_theme import apply_chart_theme, VIBRANT_PALETTE, VIBRANT_BLUE, TEXT_PRIMARY


def render_overview():
    repo_id = st.session_state.get("selected_repo_id")
    if not repo_id:
        st.info("👈 Please select or analyze a GitHub repository from the sidebar to view overview metrics.")
        return

    summary = get_repository_summary(repo_id)
    if not summary:
        st.warning("Repository details could not be found.")
        return

    # Header section
    st.title("📊 Repository Overview")
    st.markdown(
        f"**Repository:** `{summary['name']}` | **Branch:** `{summary['default_branch']}` | "
        f"**Last Analyzed:** {summary['analyzed_at'].strftime('%Y-%m-%d %H:%M UTC') if summary.get('analyzed_at') else 'N/A'}"
    )
    st.markdown("---")

    # KPI Metric Cards
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric(label="Total Commits", value=f"{summary['total_commits']:,}")
    with col2:
        st.metric(label="Total Files", value=f"{summary['total_files']:,}")
    with col3:
        st.metric(label="Contributors", value=f"{summary['contributors_count']:,}")
    with col4:
        st.metric(label="Lines of Code", value=f"{summary['total_loc']:,}")
    with col5:
        st.metric(
            label="Possible Bug Fixes",
            value=f"{summary['bug_fix_commits']:,}",
            help="Heuristic keyword detection: commit messages matching 'fix', 'bug', 'error', 'issue', 'hotfix'."
        )
    with col6:
        st.metric(
            label="Hotspot Files",
            value=f"{summary['hotspots_count']:,}",
            help="Files identified with high hotspot score based on change frequency, bug-fix activity, and Radon complexity."
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Fetch Data
    commits_df = get_commits_df(repo_id)
    files_df = get_files_df(repo_id)
    hotspots_df = get_hotspots_df(repo_id)

    # Row 1: Charts
    col_chart1, col_chart2 = st.columns([3, 2])

    with col_chart1:
        st.subheader("📈 Commit Activity Over Time")
        if not commits_df.empty:
            df_time = commits_df.copy()
            df_time["Date"] = pd.to_datetime(df_time["Date"])
            # Group by month
            df_monthly = df_time.resample("ME", on="Date").agg({
                "Commit Hash": "count",
                "Lines Added": "sum",
                "Lines Deleted": "sum"
            }).reset_index().rename(columns={"Commit Hash": "Commits"})

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_monthly["Date"],
                y=df_monthly["Commits"],
                name="Monthly Commits",
                marker_color="#2563eb",
                marker_line_color="#1d4ed8",
                marker_line_width=1,
                opacity=0.9
            ))
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Commits",
                hovermode="x unified",
            )
            apply_chart_theme(fig, height=330, show_legend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No commit data available.")

    with col_chart2:
        st.subheader("🧩 File Types Breakdown")
        if not files_df.empty:
            ext_counts = files_df["Extension"].value_counts().head(8).reset_index()
            ext_counts.columns = ["Extension", "Count"]
            ext_counts["Extension"] = ext_counts["Extension"].replace("", "no extension")

            pie_fig = px.pie(
                ext_counts,
                names="Extension",
                values="Count",
                hole=0.45,
                color_discrete_sequence=VIBRANT_PALETTE
            )
            pie_fig.update_traces(
                textposition="inside",
                textinfo="percent+label",
                textfont=dict(color="#ffffff", size=11, family="Inter, sans-serif"),
                marker=dict(line=dict(color="#ffffff", width=2))
            )
            apply_chart_theme(pie_fig, height=330, show_legend=True)
            st.plotly_chart(pie_fig, use_container_width=True)
        else:
            st.info("No file data available.")

    st.markdown("---")

    # Row 2: Top Hotspots Preview & Recent Commits
    col_hot, col_rec = st.columns([3, 2])

    with col_hot:
        st.subheader("🔥 Top 5 Code Hotspots Preview")
        st.caption("Files with the highest combined change frequency, bug-fix involvement, and Radon complexity.")
        if not hotspots_df.empty:
            top_hotspots = hotspots_df.head(5)[[
                "File Path", "Hotspot Score", "Risk Level", "Commits", "Bug Fixes", "Complexity (CC)"
            ]]
            st.dataframe(
                top_hotspots,
                use_container_width=True,
                column_config={
                    "Hotspot Score": st.column_config.ProgressColumn(
                        "Hotspot Score",
                        format="%.1f",
                        min_value=0,
                        max_value=100
                    )
                },
                hide_index=True
            )
        else:
            st.info("No hotspot files calculated.")

    with col_rec:
        st.subheader("🕒 Recent Commits Preview")
        st.caption("Latest commits recorded in the repository.")
        if not commits_df.empty:
            recent_commits = commits_df.head(5)[[
                "Commit Hash", "Author", "Date", "Possible Bug Fix"
            ]]
            st.dataframe(recent_commits, use_container_width=True, hide_index=True)
        else:
            st.info("No commits available.")


render_overview()
