"""
Chart Theme & Vibrant Styling Module for Plotly.
Ensures crisp high contrast, vibrant colors, and fixes label/background blending
across both light and dark system settings.
"""

from typing import Optional
import plotly.graph_objects as go
import plotly.express as px

# High-contrast vibrant color palettes
VIBRANT_PALETTE = [
    "#2563eb",  # Electric Blue
    "#10b981",  # Vivid Emerald
    "#f59e0b",  # Amber / Gold
    "#ef4444",  # Crimson Red
    "#8b5cf6",  # Vibrant Purple
    "#06b6d4",  # Electric Cyan
    "#ec4899",  # Hot Pink
    "#14b8a6",  # Vivid Teal
    "#f97316",  # Bright Orange
    "#6366f1",  # Indigo
]

VIBRANT_BLUE = "#2563eb"
VIBRANT_GREEN = "#10b981"
VIBRANT_RED = "#ef4444"
VIBRANT_ORANGE = "#f97316"
VIBRANT_PURPLE = "#8b5cf6"
VIBRANT_CYAN = "#06b6d4"
VIBRANT_PINK = "#ec4899"
VIBRANT_AMBER = "#f59e0b"

# High-contrast text colors
TEXT_PRIMARY = "#0f172a"    # Deep Slate / Near Black (100% visible on white/light)
TEXT_MUTED = "#334155"      # Medium Slate (for ticks and secondary labels)
BORDER_COLOR = "#cbd5e1"    # Slate 300
GRID_COLOR = "#e2e8f0"      # Slate 200
BG_PAPER = "#ffffff"        # Pure Crisp White
BG_PLOT = "#f8fafc"         # Clean Off-White / Slate 50


def apply_chart_theme(
    fig: go.Figure,
    title: Optional[str] = None,
    height: int = 340,
    show_legend: bool = True
) -> go.Figure:
    """
    Applies high-contrast vibrant styling to any Plotly figure.
    Guarantees that all titles, axis labels, tick marks, legends,
    and hover tooltips have bold, crystal-clear contrast and never blend into backgrounds.
    """
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=25, r=25, t=45 if title else 25, b=25),
        paper_bgcolor=BG_PAPER,
        plot_bgcolor=BG_PLOT,
        font=dict(
            family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            size=12,
            color=TEXT_PRIMARY
        ),
        title=dict(
            text=title or "",
            font=dict(
                family="Inter, -apple-system, sans-serif",
                size=14,
                color=TEXT_PRIMARY,
            ),
            x=0.01,
            xanchor="left"
        ) if title else None,
        hoverlabel=dict(
            bgcolor=TEXT_PRIMARY,
            font_size=12,
            font_family="Inter, sans-serif",
            font_color="#ffffff",
            bordercolor=TEXT_PRIMARY
        ),
        showlegend=show_legend,
        legend=dict(
            font=dict(color=TEXT_PRIMARY, size=11, family="Inter, sans-serif"),
            bgcolor="rgba(255, 255, 255, 0.92)",
            bordercolor=BORDER_COLOR,
            borderwidth=1,
        ) if show_legend else None,
    )

    # Apply sharp, readable styling to all X and Y axes
    fig.update_xaxes(
        title_font=dict(color=TEXT_PRIMARY, size=12, family="Inter, sans-serif"),
        tickfont=dict(color=TEXT_MUTED, size=11, family="Inter, sans-serif"),
        gridcolor=GRID_COLOR,
        gridwidth=1,
        zerolinecolor=BORDER_COLOR,
        zerolinewidth=1,
        linecolor=BORDER_COLOR,
        linewidth=1,
    )

    fig.update_yaxes(
        title_font=dict(color=TEXT_PRIMARY, size=12, family="Inter, sans-serif"),
        tickfont=dict(color=TEXT_MUTED, size=11, family="Inter, sans-serif"),
        gridcolor=GRID_COLOR,
        gridwidth=1,
        zerolinecolor=BORDER_COLOR,
        zerolinewidth=1,
        linecolor=BORDER_COLOR,
        linewidth=1,
    )

    return fig
