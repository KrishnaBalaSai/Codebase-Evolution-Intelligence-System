"""
Contributors Page - Codebase Evolution Intelligence System.
Displays contributor activity, commits per developer, files changed, and code churn.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from analysis import get_contributors_df, get_repository_summary
from chart_theme import apply_chart_theme, VIBRANT_PALETTE, VIBRANT_GREEN, VIBRANT_RED


def render_contributors():
    repo_id = st.session_state.get("selected_repo_id")
    if not repo_id:
        st.info("👈 Please select or analyze a GitHub repository from the sidebar to view contributor analytics.")
        return

    summary = get_repository_summary(repo_id)
    devs_df = get_contributors_df(repo_id)

    st.title("👥 Contributor Analytics")
    st.caption(f"Repository: **{summary.get('name', 'N/A')}** | Total Unique Contributors: **{len(devs_df):,}**")
    st.markdown("---")

    if devs_df.empty:
        st.warning("No contributor data found for this repository.")
        return

    # Contributor Summary Cards
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Total Contributors", f"{len(devs_df):,}")
    with col_m2:
        top_committer = devs_df.iloc[0]["Contributor"] if not devs_df.empty else "N/A"
        top_commits = devs_df.iloc[0]["Commits"] if not devs_df.empty else 0
        st.metric("Top Contributor", f"{top_committer}", f"{top_commits} commits")
    with col_m3:
        avg_commits = devs_df["Commits"].mean()
        st.metric("Average Commits / Dev", f"{avg_commits:.1f}")
    with col_m4:
        total_code_added = devs_df["Lines Added"].sum()
        st.metric("Total Lines Added", f"{total_code_added:,}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts Section
    col_c1, col_c2 = st.columns([3, 2])

    with col_c1:
        st.subheader("🏆 Top Contributors by Commits")
        top_10 = devs_df.head(10).sort_values(by="Commits", ascending=True)
        bar_fig = px.bar(
            top_10,
            x="Commits",
            y="Contributor",
            orientation="h",
            color="Commits",
            color_continuous_scale=[[0, "#38bdf8"], [1, "#1d4ed8"]],
            hover_data=["Email", "Files Touched", "Lines Added", "Lines Deleted"],
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
        st.subheader("🥧 Contributor Share")
        top_5_and_others = devs_df.head(5).copy()
        other_commits = devs_df["Commits"].iloc[5:].sum() if len(devs_df) > 5 else 0
        if other_commits > 0:
            top_5_and_others = pd.concat([
                top_5_and_others,
                pd.DataFrame([{"Contributor": "Others", "Commits": other_commits}])
            ], ignore_index=True)

        pie_fig = px.pie(
            top_5_and_others,
            names="Contributor",
            values="Commits",
            hole=0.4,
            color_discrete_sequence=VIBRANT_PALETTE
        )
        pie_fig.update_traces(
            textposition="inside",
            textinfo="percent+label",
            textfont=dict(color="#ffffff", size=11, family="Inter, sans-serif"),
            marker=dict(line=dict(color="#ffffff", width=2))
        )
        apply_chart_theme(pie_fig, height=340, show_legend=True)
        st.plotly_chart(pie_fig, use_container_width=True)

    # Churn per Contributor (Lines Added vs Lines Deleted)
    st.subheader("⚖️ Code Contribution: Lines Added vs Deleted")
    churn_df = devs_df.head(10).copy()
    fig_churn = go.Figure()
    fig_churn.add_trace(go.Bar(
        x=churn_df["Contributor"],
        y=churn_df["Lines Added"],
        name="Lines Added (+)",
        marker_color="#10b981",
        marker_line_color="#047857",
        marker_line_width=1
    ))
    fig_churn.add_trace(go.Bar(
        x=churn_df["Contributor"],
        y=churn_df["Lines Deleted"],
        name="Lines Deleted (-)",
        marker_color="#ef4444",
        marker_line_color="#b91c1c",
        marker_line_width=1
    ))
    fig_churn.update_layout(
        barmode="group",
        xaxis_tickangle=-25,
        xaxis_title="Contributor",
        yaxis_title="Lines of Code"
    )
    apply_chart_theme(fig_churn, height=340, show_legend=True)
    st.plotly_chart(fig_churn, use_container_width=True)

    st.markdown("---")

    # Contributor Directory Table
    st.subheader("📋 Contributor Directory")
    search = st.text_input("Search Contributor or Email:", placeholder="e.g. John, @gmail.com")
    table_df = devs_df.copy()
    if search:
        s = search.lower()
        table_df = table_df[
            table_df["Contributor"].str.lower().str.contains(s, na=False) |
            table_df["Email"].str.lower().str.contains(s, na=False)
        ]

    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Commits": st.column_config.NumberColumn("Total Commits", format="%d"),
            "Files Touched": st.column_config.NumberColumn("Files Touched", format="%d"),
            "Lines Added": st.column_config.NumberColumn("Lines Added", format="%d"),
            "Lines Deleted": st.column_config.NumberColumn("Lines Deleted", format="%d"),
            "Net Contribution": st.column_config.NumberColumn("Net Lines", format="%d"),
        }
    )


render_contributors()
