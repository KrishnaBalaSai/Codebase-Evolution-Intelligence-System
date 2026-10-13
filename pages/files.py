"""
Files Page - Codebase Evolution Intelligence System.
Displays file modification frequency, lines of code (LOC/SLOC),
Radon cyclomatic complexity, and churn analysis.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from analysis import get_files_df, get_repository_summary
from chart_theme import apply_chart_theme


def render_files():
    repo_id = st.session_state.get("selected_repo_id")
    if not repo_id:
        st.info("👈 Please select or analyze a GitHub repository from the sidebar to view file analytics.")
        return

    summary = get_repository_summary(repo_id)
    files_df = get_files_df(repo_id)

    st.title("📁 File Analysis & Complexity")
    st.caption(f"Repository: **{summary.get('name', 'N/A')}** | Total Tracked Files: **{len(files_df):,}**")
    st.markdown("---")

    if files_df.empty:
        st.warning("No file data available for this repository.")
        return

    # Filter Controls
    col_f1, col_f2, col_f3 = st.columns([3, 2, 2])
    with col_f1:
        path_search = st.text_input("Filter by File Path / Name", placeholder="e.g. src/, test_, .py...")
    with col_f2:
        extensions = ["All Extensions"] + sorted(files_df["Extension"].dropna().unique().tolist())
        selected_ext = st.selectbox("File Extension", extensions)
    with col_f3:
        py_only = st.checkbox("Python Files Only (Radon Evaluated)", value=False)

    filtered_df = files_df.copy()
    if path_search:
        filtered_df = filtered_df[filtered_df["File Path"].str.lower().str.contains(path_search.lower(), na=False)]
    if selected_ext != "All Extensions":
        filtered_df = filtered_df[filtered_df["Extension"] == selected_ext]
    if py_only:
        filtered_df = filtered_df[filtered_df["Extension"] == ".py"]

    # File Summary Cards
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Files Matching", f"{len(filtered_df):,}")
    with col_m2:
        st.metric("Total Lines of Code (LOC)", f"{filtered_df['Lines of Code (LOC)'].sum():,}")
    with col_m3:
        avg_cc = filtered_df[filtered_df["Extension"] == ".py"]["Complexity (CC)"].mean() if not filtered_df.empty else 1.0
        st.metric("Avg Python Complexity (CC)", f"{avg_cc:.2f}" if pd.notna(avg_cc) else "N/A")
    with col_m4:
        top_churn = filtered_df["Commits"].max() if not filtered_df.empty else 0
        st.metric("Max Commits on Single File", f"{top_churn:,}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts Section
    col_c1, col_c2 = st.columns([3, 2])

    with col_c1:
        st.subheader("🔥 Top 10 Most Frequently Changed Files")
        top_changed = filtered_df.sort_values(by="Commits", ascending=False).head(10)
        bar_fig = px.bar(
            top_changed,
            x="Commits",
            y="File Name",
            orientation="h",
            color="Commits",
            hover_data=["File Path", "Lines of Code (LOC)", "Bug Fixes"],
            color_continuous_scale=[[0, "#38bdf8"], [0.5, "#2563eb"], [1, "#7c3aed"]],
        )
        bar_fig.update_traces(
            marker_line_color="#1e293b",
            marker_line_width=1
        )
        bar_fig.update_layout(
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False
        )
        apply_chart_theme(bar_fig, height=340, show_legend=False)
        st.plotly_chart(bar_fig, use_container_width=True)

    with col_c2:
        st.subheader("🔬 Complexity vs File Churn")
        st.caption("High CC + High Commits = files that may require refactoring.")
        scatter_fig = px.scatter(
            filtered_df,
            x="Commits",
            y="Complexity (CC)",
            size="Lines of Code (LOC)",
            color="Rank",
            color_discrete_map={
                "A": "#10b981",
                "B": "#06b6d4",
                "C": "#f59e0b",
                "D": "#f97316",
                "E": "#ef4444",
                "F": "#b91c1c"
            },
            hover_data=["File Path", "Bug Fixes"],
        )
        scatter_fig.update_traces(
            marker=dict(line=dict(width=1, color="#0f172a"))
        )
        apply_chart_theme(scatter_fig, height=340, show_legend=True)
        st.plotly_chart(scatter_fig, use_container_width=True)

    # Detailed Table
    st.subheader("📋 Files Inventory & Radon Metrics")
    display_cols = [
        "File Path", "Lines of Code (LOC)", "SLOC", "Comments",
        "Complexity (CC)", "Rank", "Commits", "Bug Fixes",
        "Lines Added", "Lines Deleted", "Active"
    ]

    st.dataframe(
        filtered_df[display_cols].sort_values(by="Commits", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Complexity (CC)": st.column_config.NumberColumn("Complexity (CC)", format="%.2f"),
            "Rank": st.column_config.TextColumn("Radon Rank", help="Radon score rank: A (low complexity) to F (extreme complexity)"),
        }
    )


render_files()
