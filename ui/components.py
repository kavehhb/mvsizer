"""Reusable HTML-ish UI components for the Streamlit frontend."""
import streamlit as st


def status_chip(label: str, level: str = "good") -> str:
    cls = {"good": "status-good", "warn": "status-warn", "bad": "status-bad"}.get(level, "status-good")
    return f"<span class='{cls}'>{label}</span>"


def card_start(title: str, caption: str = "") -> None:
    extra = f"<span>{caption}</span>" if caption else ""
    st.markdown(
        f"<div class='surface-card'><div class='section-title'><h3>{title}</h3>{extra}</div>",
        unsafe_allow_html=True,
    )


def card_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_sidebar_brand() -> None:
    st.markdown(
        """
        <div class='sidebar-brand'>
            <div class='app-badge'>⚙ Design workspace</div>
            <h1>MV Cable Tool</h1>
            <p>A cleaner control panel for selecting cable data, installation geometry, soil assumptions, and loading conditions.</p>
            <div class='sidebar-note'>Use the form below, then run one calculation when you are ready.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
        <div class='hero-card'>
            <div class='app-badge'>⚡ MV cable sizing studio</div>
            <div class='hero-title'>Engineering-grade calculations in a modern tool experience.</div>
            <div class='hero-copy'>Configure the cable, installation, soil, and loading on the left. The results area is organized like a polished web dashboard with summary cards, visual feedback, and cleaner engineering detail.</div>
            <div class='pill-row'>
                <div class='pill'>IEC 60287 continuous rating</div>
                <div class='pill'>IEC 60853 cyclic loading</div>
                <div class='pill'>Voltage drop and short-circuit checks</div>
                <div class='pill'>Trench visualization and report export</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    st.markdown(
        "<div class='footer-note'>IEC 60287 and IEC 60853 analytical workflow, presented with a cleaner website-style Streamlit interface for better client-facing usability.</div>",
        unsafe_allow_html=True,
    )
