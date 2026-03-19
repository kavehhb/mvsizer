"""Theme tokens and CSS injection for the Streamlit frontend."""
import streamlit as st


DARK = {
    "bg": "#07111f",
    "bg_soft": "#0c1728",
    "panel": "#101c31",
    "panel_2": "#15243d",
    "card": "rgba(16, 28, 49, 0.84)",
    "card_2": "rgba(21, 36, 61, 0.92)",
    "line": "#223858",
    "line_soft": "rgba(124, 156, 196, 0.18)",
    "text": "#e9f1ff",
    "muted": "#9db2d1",
    "subtle": "#6f86a9",
    "accent": "#27d7b7",
    "accent_2": "#5da8ff",
    "accent_3": "#8b6dff",
    "good": "#2ed47a",
    "warn": "#ffaf45",
    "bad": "#ff627d",
    "shadow": "0 24px 60px rgba(0,0,0,0.38)",
    "hero": "radial-gradient(circle at top left, rgba(39,215,183,0.20), transparent 35%), radial-gradient(circle at top right, rgba(93,168,255,0.18), transparent 28%), linear-gradient(135deg, #0c1728 0%, #0f2039 54%, #142946 100%)",
    "glow": "39,215,183",
}

LIGHT = {
    "bg": "#f3f7fd",
    "bg_soft": "#eaf0fa",
    "panel": "#ffffff",
    "panel_2": "#f9fbff",
    "card": "rgba(255,255,255,0.88)",
    "card_2": "rgba(255,255,255,0.96)",
    "line": "#d6e0ef",
    "line_soft": "rgba(79, 112, 164, 0.16)",
    "text": "#14233a",
    "muted": "#4f6789",
    "subtle": "#7f93b0",
    "accent": "#0ea58a",
    "accent_2": "#2f7cf7",
    "accent_3": "#7b61ff",
    "good": "#1d9c58",
    "warn": "#d88300",
    "bad": "#d92d57",
    "shadow": "0 16px 40px rgba(20,35,58,0.10)",
    "hero": "radial-gradient(circle at top left, rgba(14,165,138,0.16), transparent 35%), radial-gradient(circle at top right, rgba(47,124,247,0.14), transparent 28%), linear-gradient(135deg, #ffffff 0%, #f7faff 54%, #eef5ff 100%)",
    "glow": "14,165,138",
}


def inject_css(dark: bool = True) -> dict:
    t = DARK if dark else LIGHT
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');
        :root {{
            --bg: {t['bg']};
            --bg-soft: {t['bg_soft']};
            --panel: {t['panel']};
            --panel-2: {t['panel_2']};
            --card: {t['card']};
            --card-2: {t['card_2']};
            --line: {t['line']};
            --line-soft: {t['line_soft']};
            --text: {t['text']};
            --muted: {t['muted']};
            --subtle: {t['subtle']};
            --accent: {t['accent']};
            --accent-2: {t['accent_2']};
            --accent-3: {t['accent_3']};
            --good: {t['good']};
            --warn: {t['warn']};
            --bad: {t['bad']};
            --shadow: {t['shadow']};
            --hero: {t['hero']};
            --glow: {t['glow']};
        }}
        html, body, [class*="css"] {{font-family:'Inter', sans-serif;color:var(--text);}}
        .stApp {{
            background: radial-gradient(circle at 0% 0%, rgba(var(--glow), 0.10), transparent 20%), radial-gradient(circle at 100% 0%, rgba(93,168,255,0.08), transparent 20%), linear-gradient(180deg, var(--bg) 0%, var(--bg-soft) 100%);
        }}
        .block-container {{max-width:1500px;padding-top:1rem;padding-bottom:2.5rem;}}
        [data-testid="stSidebar"] {{background: linear-gradient(180deg, var(--panel) 0%, var(--panel-2) 100%);border-right:1px solid var(--line);}}
        [data-testid="stSidebar"] .block-container {{padding-top:1rem;padding-bottom:1rem;}}
        [data-testid="stHeader"] {{background: rgba(0,0,0,0);}}
        #MainMenu, footer {{visibility:hidden;}}
        .hero-card, .surface-card, .empty-card, .info-card, .status-card, .toolbar-card {{border:1px solid var(--line-soft);border-radius:24px;background:var(--card);box-shadow:var(--shadow);backdrop-filter:blur(18px);}}
        .hero-card {{background:var(--hero);padding:1.4rem 1.5rem;margin-bottom:1rem;}}
        .toolbar-card {{padding:1rem 1.15rem;margin-bottom:1rem;}}
        .surface-card {{padding:1rem 1.1rem;margin:0.35rem 0 0.75rem 0;}}
        .empty-card {{padding:1.3rem 1.4rem;min-height:240px;}}
        .info-card, .status-card {{padding:0.95rem 1rem;min-height:138px;}}
        .app-badge {{display:inline-flex;align-items:center;gap:0.45rem;padding:0.35rem 0.7rem;border-radius:999px;font-size:0.72rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;background: rgba(var(--glow), 0.12);color: var(--accent);border:1px solid rgba(var(--glow), 0.26);}}
        .hero-title {{margin-top:0.8rem;font-size:2.15rem;font-weight:800;line-height:1.05;letter-spacing:-0.03em;color:var(--text);}}
        .hero-copy {{margin-top:0.6rem;max-width:760px;font-size:1rem;line-height:1.7;color:var(--muted);}}
        .pill-row {{display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:1rem;}}
        .pill {{display:inline-flex;align-items:center;gap:0.4rem;background: rgba(255,255,255,0.08);border:1px solid var(--line-soft);color:var(--text);border-radius:999px;padding:0.45rem 0.8rem;font-size:0.8rem;font-weight:600;}}
        .section-title {{display:flex;align-items:center;justify-content:space-between;gap:0.75rem;margin:0.2rem 0 0.75rem 0;}}
        .section-title h3 {{margin:0;font-size:0.82rem;letter-spacing:0.12em;text-transform:uppercase;color:var(--subtle);font-weight:800;}}
        .section-title span {{font-size:0.75rem;color:var(--muted);}}
        .mini-label {{font-size:0.72rem;letter-spacing:0.08em;text-transform:uppercase;color:var(--subtle);font-weight:700;}}
        .metric-big {{font-family:'JetBrains Mono', monospace;font-size:1.55rem;font-weight:700;color:var(--accent);margin-top:0.4rem;}}
        .metric-sub {{color:var(--muted);font-size:0.84rem;margin-top:0.3rem;line-height:1.5;}}
        .kv {{display:flex;justify-content:space-between;gap:1rem;padding:0.48rem 0;border-bottom:1px dashed var(--line-soft);}}
        .kv:last-child {{border-bottom:none;}}
        .kv .k {{color:var(--muted);font-size:0.86rem;}}
        .kv .v {{font-family:'JetBrains Mono', monospace;font-size:0.87rem;font-weight:700;color:var(--text);text-align:right;}}
        .sidebar-brand {{padding:1rem 1rem 0.9rem 1rem;border-radius:22px;background: var(--hero);border:1px solid var(--line-soft);box-shadow: var(--shadow);margin-bottom:0.8rem;}}
        .sidebar-brand h1 {{margin:0.55rem 0 0.2rem 0;font-size:1.1rem;font-weight:800;color:var(--text);}}
        .sidebar-brand p {{margin:0;color:var(--muted);line-height:1.55;font-size:0.84rem;}}
        .sidebar-note {{margin-top:0.7rem;padding-top:0.7rem;border-top:1px solid var(--line-soft);color:var(--subtle);font-size:0.76rem;}}
        .status-good, .status-warn, .status-bad {{display:inline-flex;align-items:center;gap:0.4rem;padding:0.32rem 0.65rem;border-radius:999px;font-size:0.72rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;}}
        .status-good {{background: rgba(46,212,122,0.14); color: var(--good); border:1px solid rgba(46,212,122,0.28);}}
        .status-warn {{background: rgba(255,175,69,0.14); color: var(--warn); border:1px solid rgba(255,175,69,0.30);}}
        .status-bad {{background: rgba(255,98,125,0.14); color: var(--bad); border:1px solid rgba(255,98,125,0.30);}}
        .stSelectbox > div > div, .stNumberInput input, .stTextInput input, .stTextArea textarea, .stMultiSelect div[data-baseweb="select"], .stDateInput input {{background: rgba(255,255,255,0.04) !important;border:1px solid var(--line) !important;color:var(--text) !important;border-radius:14px !important;min-height:44px !important;}}
        div[data-baseweb="select"] > div {{background: rgba(255,255,255,0.04) !important;border:none !important;}}
        .stSlider [data-baseweb="slider"] > div > div {{background: var(--accent) !important;}}
        .stCheckbox label, .stRadio label, .stMarkdown, p, li {{color: var(--text);}}
        .stButton > button, .stDownloadButton > button {{width:100%;min-height:46px;border:none;border-radius:14px;background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 100%);color:white;font-weight:800;letter-spacing:0.04em;box-shadow: 0 16px 28px rgba(var(--glow), 0.22);}}
        .stButton > button:hover, .stDownloadButton > button:hover {{filter:brightness(1.02);transform: translateY(-1px);}}
        .stTabs [data-baseweb="tab-list"] {{gap:0.4rem;border-bottom:none;margin-bottom:0.65rem;}}
        .stTabs [data-baseweb="tab"] {{border-radius:999px;padding:0.55rem 0.95rem;background: rgba(255,255,255,0.04);border:1px solid var(--line-soft);color:var(--muted);font-weight:700;}}
        .stTabs [aria-selected="true"] {{color:var(--text) !important;background: rgba(var(--glow), 0.12) !important;border-color: rgba(var(--glow), 0.28) !important;}}
        div[data-testid="metric-container"] {{background: var(--card);border:1px solid var(--line-soft);padding:1rem 1rem 0.9rem 1rem;border-radius:20px;box-shadow: var(--shadow);}}
        div[data-testid="metric-container"] label {{color:var(--subtle) !important;text-transform:uppercase;font-size:0.68rem !important;letter-spacing:0.10em;font-weight:800 !important;}}
        div[data-testid="metric-container"] [data-testid="stMetricValue"] {{font-family:'JetBrains Mono', monospace;color:var(--text);font-size:1.45rem;font-weight:700;}}
        div[data-testid="metric-container"] [data-testid="stMetricDelta"] {{font-family:'JetBrains Mono', monospace;font-size:0.74rem;}}
        .streamlit-expanderHeader {{background: rgba(255,255,255,0.04);border:1px solid var(--line-soft);border-radius:16px;min-height:50px;font-weight:700;color:var(--text);}}
        .stAlert {{border-radius:16px;border:1px solid var(--line-soft);}}
        .footer-note {{color:var(--subtle);font-size:0.78rem;line-height:1.7;text-align:center;padding:0.7rem 0 0.2rem 0;}}
        </style>
        """,
        unsafe_allow_html=True,
    )
    return t
