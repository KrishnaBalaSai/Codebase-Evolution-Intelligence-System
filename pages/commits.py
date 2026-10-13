"""
Commits Page - Codebase Evolution Intelligence System.
Displays commit history, author activity, lines added/deleted, and heuristic bug-fix tags.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from analysis import get_commits_df, get_repository_summary
from chart_theme import apply_chart_theme, VIBRANT_BLUE, VIBRANT_ORANGE


def render_commits():
    repo_id = st.session_state.get("selected_repo_id")
    if not repo_id:
        st.info("👈 Please select or analyze a GitHub repository from the sidebar to view commit history.")
        return

    summary = get_repository_summary(repo_id)
    commits_df = get_commits_df(repo_id)

    st.title("📜 Commit History & Activity")
    st.caption(f"Repository: **{summary.get('name', 'N/A')}** | Branch: **{summary.get('default_branch', 'main')}**")
    st.markdown("---")

    if commits_df.empty:
        st.warning("No commits found for this repository.")
        return

    # Filter controls
    with st.expander("🔍 Filter & Search Commits", expanded=True):
        col_f1, col_f2, col_f3, col_f4 = st.columns([3, 2, 2, 2])
        with col_f1:
            search_query = st.text_input("Search message or hash", placeholder="e.g. fix, auth, 8a3f...")
        with col_f2:
            authors_list = ["All Authors"] + sorted(commits_df["Author"].dropna().unique().tolist())
            selected_author = st.selectbox("Filter by Author", authors_list)
        with col_f3:
            bug_fix_only = st.checkbox("Only Possible Bug Fixes", value=False)
        with col_f4:
            sort_order = st.selectbox("Sort Order", ["Newest First", "Oldest First", "Most Files Changed", "Most Lines Added"])

    # Apply filters
    filtered_df = commits_df.copy()
    if search_query:
        q = search_query.lower()
        filtered_df = filtered_df[
            filtered_df["Message"].str.lower().str.contains(q, na=False) |
            filtered_df["Full Hash"].str.lower().str.contains(q, na=False) |
            filtered_df["Author"].str.lower().str.contains(q, na=False)
        ]

    if selected_author != "All Authors":
        filtered_df = filtered_df[filtered_df["Author"] == selected_author]

    if bug_fix_only:
        filtered_df = filtered_df[filtered_df["Possible Bug Fix"] == "Yes"]

    if sort_order == "Newest First":
        filtered_df = filtered_df.sort_values(by="Date", ascending=False)
    elif sort_order == "Oldest First":
        filtered_df = filtered_df.sort_values(by="Date", ascending=True)
    elif sort_order == "Most Files Changed":
        filtered_df = filtered_df.sort_values(by="Files Changed", ascending=False)
    elif sort_order == "Most Lines Added":
        filtered_df = filtered_df.sort_values(by="Lines Added", ascending=False)

    # Commits summary metrics
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Filtered Commits", f"{len(filtered_df):,}")
    with col_m2:
        bug_count = (filtered_df["Possible Bug Fix"] == "Yes").sum()
        pct = (bug_count / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
        st.metric("Possible Bug Fixes", f"{bug_count:,} ({pct:.1f}%)")
    with col_m3:
        st.metric("Total Lines Added", f"{filtered_df['Lines Added'].sum():,}")
    with col_m4:
        st.metric("Total Lines Deleted", f"{filtered_df['Lines Deleted'].sum():,}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Commit Distribution Visualizations
    col_c1, col_c2 = st.columns([3, 2])
    with col_c1:
        st.subheader("📊 Commit Velocity (Lines Changed per Commit)")
        scatter_fig = px.scatter(
            filtered_df.head(200),
            x="Date",
            y="Lines Added",
            size="Files Changed",
            color="Possible Bug Fix",
            color_discrete_map={"Yes": "#f97316", "No": "#2563eb"},
            hover_data=["Commit Hash", "Author", "Message"],
            title="Recent 200 Commits: Additions vs Date (Orange = Bug Fix, Blue = Normal)"
        )
        scatter_fig.update_traces(
            marker=dict(line=dict(width=1, color="#1e293b"))
        )
        apply_chart_theme(scatter_fig, height=340, show_legend=True)
        st.plotly_chart(scatter_fig, use_container_width=True)

    with col_c2:
        st.subheader("👥 Commits by Top Authors")
        author_counts = filtered_df["Author"].value_counts().head(7).reset_index()
        author_counts.columns = ["Author", "Commits"]
        bar_fig = px.bar(
            author_counts,
            x="Commits",
            y="Author",
            orientation="h",
            color="Commits",
            color_continuous_scale=[[0, "#60a5fa"], [1, "#1d4ed8"]]
        )
        bar_fig.update_traces(
            marker_line_color="#1e3a8a",
            marker_line_width=1
        )
        bar_fig.update_layout(
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False
        )
        apply_chart_theme(bar_fig, height=340, show_legend=False)
        st.plotly_chart(bar_fig, use_container_width=True)

    # Commits Data Table
    st.subheader("📋 Commit Log")
    display_cols = [
        "Commit Hash", "Author", "Date", "Files Changed",
        "Lines Added", "Lines Deleted", "Net Lines", "Possible Bug Fix", "Message"
    ]

    st.dataframe(
        filtered_df[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD HH:mm"),
            "Possible Bug Fix": st.column_config.TextColumn(
                "Possible Bug Fix",
                help="Keyword heuristic ('fix', 'bug', 'error', etc.)"
            ),
        }
    )

    # Commit Detail Viewer
    st.markdown("---")
    st.subheader("🔎 Commit Details Viewer")
    selected_hash = st.selectbox(
        "Select a commit hash to inspect full message:",
        options=filtered_df["Commit Hash"].tolist()[:100]
    )
    if selected_hash:
        row = filtered_df[filtered_df["Commit Hash"] == selected_hash].iloc[0]
        st.markdown(f"**Commit:** `{row['Full Hash']}`")
        st.markdown(f"**Author:** {row['Author']} `<{row['Email']}>` | **Date:** {row['Date']}")
        st.markdown(f"**Stats:** {row['Files Changed']} files changed, +{row['Lines Added']} / -{row['Lines Deleted']} lines")
        st.markdown("**Message:**")
        st.code(row["Full Message"])


render_commits()
