"""
app.py  ·  MV Cable Thermal Rating — Modern UI
Run: streamlit run app.py
"""
import streamlit as st, numpy as np, math, io
import matplotlib, matplotlib.pyplot as plt, matplotlib.patches as mpatches
matplotlib.use("Agg")
from cable_data import CABLE_LIBRARY, LOAD_PROFILES, PROFILE_LABELS, PROFILE_MU, list_cables
from cable_engine import InstallationParams, SoilParams, build_engine
from load_analysis import LoadParams, analyse
from report_gen import generate_pdf
from trench_viz import draw_trench as _draw_trench_viz, draw_load_profile as _draw_profile_viz

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="MV Cable Rating", page_icon="⚡",
                   layout="wide", initial_sidebar_state="expanded")

if "dark" not in st.session_state:
    st.session_state.dark = True

D = st.session_state.dark

# ── Theme tokens ─────────────────────────────────────────────────────────
if D:
    BG        = "#060a10"
    BG2       = "#0a0f18"
    BG3       = "#0e1520"
    CARD      = "#0c1420"
    CARD2     = "#101b2c"
    BORD      = "#1a2840"
    BORD2     = "#223350"
    TX        = "#c8d8f0"
    TX2       = "#5878a0"
    TX3       = "#384868"
    ACC       = "#00d4aa"
    ACC2      = "#00a8ff"
    ACC3      = "#7c5cfc"
    GRN       = "#00e088"
    RED       = "#ff4060"
    ORG       = "#ff8830"
    YEL       = "#ffc040"
    MV_BG     = "#060e18"
    MV_AX     = "#3a5878"
    GLOW      = "0,212,170"
    SHADOW    = "rgba(0,0,0,.5)"
    GLASS     = "rgba(10,20,35,.75)"
    GLASS2    = "rgba(10,20,35,.55)"
else:
    BG        = "#f0f2f8"
    BG2       = "#f5f7fc"
    BG3       = "#e8ecf4"
    CARD      = "#ffffff"
    CARD2     = "#f8faff"
    BORD      = "#d0d8e8"
    BORD2     = "#b8c4d8"
    TX        = "#1a2540"
    TX2       = "#4a6090"
    TX3       = "#8898b0"
    ACC       = "#0088aa"
    ACC2      = "#0066cc"
    ACC3      = "#6040cc"
    GRN       = "#00884c"
    RED       = "#cc2040"
    ORG       = "#cc6600"
    YEL       = "#aa8800"
    MV_BG     = "#f8faff"
    MV_AX     = "#4a6888"
    GLOW      = "0,136,170"
    SHADOW    = "rgba(0,0,0,.08)"
    GLASS     = "rgba(255,255,255,.85)"
    GLASS2    = "rgba(255,255,255,.65)"

# ── Global styles ─────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

:root {{
  --bg: {BG}; --bg2: {BG2}; --bg3: {BG3};
  --card: {CARD}; --card2: {CARD2};
  --bord: {BORD}; --bord2: {BORD2};
  --tx: {TX}; --tx2: {TX2}; --tx3: {TX3};
  --acc: {ACC}; --acc2: {ACC2}; --acc3: {ACC3};
  --grn: {GRN}; --red: {RED}; --org: {ORG}; --yel: {YEL};
}}

html, body, [class*="css"] {{
  font-family: 'DM Sans', -apple-system, sans-serif;
  color: {TX};
}}
.stApp {{ background: {BG}; }}
.block-container {{
  padding-top: 0.5rem; padding-bottom: 2rem; max-width: 1600px;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
  background: {BG2} !important;
  border-right: 1px solid {BORD} !important;
}}
[data-testid="stSidebar"] .block-container {{
  padding: 0.5rem 0.6rem;
}}

/* ── Inputs ── */
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stTextInput > div > div > input,
.stTextArea textarea {{
  background: {BG3} !important;
  color: {TX} !important;
  border: 1px solid {BORD} !important;
  border-radius: 8px !important;
  font-size: 0.82rem !important;
  font-family: 'DM Sans', sans-serif !important;
  transition: border-color 0.2s, box-shadow 0.2s;
}}
.stSelectbox > div > div:focus-within,
.stNumberInput > div > div > input:focus,
.stTextInput > div > div > input:focus {{
  border-color: {ACC} !important;
  box-shadow: 0 0 0 2px rgba({GLOW}, 0.15) !important;
}}

/* ── Metrics ── */
[data-testid="metric-container"] {{
  background: {CARD};
  border: 1px solid {BORD};
  border-radius: 12px;
  padding: 0.75rem 1rem;
  box-shadow: 0 2px 12px {SHADOW};
  transition: transform 0.15s, box-shadow 0.15s;
}}
[data-testid="metric-container"]:hover {{
  transform: translateY(-1px);
  box-shadow: 0 4px 20px {SHADOW};
}}
[data-testid="metric-container"] label {{
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.6rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: {TX2} !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
  font-family: 'Space Mono', monospace !important;
  font-size: 1.3rem !important;
  color: {ACC} !important;
  font-weight: 700 !important;
}}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {{
  font-family: 'Space Mono', monospace !important;
  font-size: 0.65rem !important;
}}

/* ── Headings ── */
h1 {{
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 700 !important;
  font-size: 1.3rem !important;
  color: {ACC} !important;
  border-bottom: none !important;
  padding-bottom: 0 !important;
  margin-bottom: 0.3rem !important;
}}
h2 {{
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.85rem !important;
  color: {TX2} !important;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0.8rem 0 0.3rem !important;
  padding: 0 !important;
  border: none !important;
}}
h3 {{
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.72rem !important;
  color: {TX3} !important;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0.4rem 0 0.15rem !important;
}}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {{
  background: transparent;
  border-bottom: 2px solid {BORD};
  gap: 0;
}}
.stTabs [data-baseweb="tab"] {{
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.72rem !important;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: {TX3} !important;
  padding: 0.55rem 1.1rem;
  border-radius: 8px 8px 0 0;
  border: none !important;
  transition: color 0.15s, background 0.15s;
}}
.stTabs [data-baseweb="tab"]:hover {{
  color: {TX} !important;
  background: {CARD} !important;
}}
.stTabs [aria-selected="true"] {{
  color: {ACC} !important;
  background: {CARD} !important;
  border-bottom: 2px solid {ACC} !important;
}}

/* ── Expanders ── */
.streamlit-expanderHeader {{
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.75rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.05em;
  color: {TX2} !important;
  background: {BG3} !important;
  border: 1px solid {BORD} !important;
  border-radius: 8px !important;
  padding: 0.5rem 0.8rem !important;
}}

/* ── Buttons ── */
.stButton > button {{
  background: linear-gradient(135deg, {ACC}, {ACC2}) !important;
  color: {'#040810' if D else '#fff'} !important;
  border: none !important;
  font-family: 'DM Sans', sans-serif !important;
  font-weight: 700 !important;
  font-size: 0.8rem !important;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  border-radius: 10px !important;
  width: 100%;
  padding: 0.55rem 1rem !important;
  transition: opacity 0.15s, transform 0.1s, box-shadow 0.15s;
  box-shadow: 0 2px 12px rgba({GLOW}, 0.25);
}}
.stButton > button:hover {{
  opacity: 0.9 !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba({GLOW}, 0.35) !important;
}}
.stButton > button:active {{
  transform: translateY(0);
}}

/* ── Download button ── */
.stDownloadButton > button {{
  background: linear-gradient(135deg, {ACC3}, {ACC2}) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  box-shadow: 0 2px 12px rgba(124,92,252,0.2);
}}

/* ── Dividers ── */
hr {{
  border: 0;
  border-top: 1px solid {BORD};
  margin: 0.45rem 0;
}}

/* ── Alerts ── */
.stAlert {{
  background: {CARD} !important;
  border: 1px solid {BORD} !important;
  color: {TX} !important;
  border-radius: 10px !important;
}}

/* ── Radio pills ── */
.stRadio > div {{
  gap: 0.3rem;
}}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: {BG}; }}
::-webkit-scrollbar-thumb {{ background: {BORD}; border-radius: 3px; }}
</style>""", unsafe_allow_html=True)

# ── Helpers ──────────────────────────────────────────────────────────────────

def glass_card(content, accent=None, glow=False):
    bc = accent or BORD
    glow_css = f"box-shadow: 0 0 20px rgba({GLOW}, 0.08);" if glow else ""
    return (f'<div style="background:{CARD};border:1px solid {bc};border-radius:12px;'
            f'padding:0.85rem 1.1rem;margin:0.35rem 0;{glow_css}'
            f'backdrop-filter:blur(10px);">{content}</div>')

def badge(txt, color, size="0.68rem"):
    return (f'<span style="background:{color};color:#fff;border-radius:6px;'
            f'padding:0.15rem 0.55rem;font-size:{size};font-weight:700;'
            f'letter-spacing:0.04em;display:inline-block;">{txt}</span>')

def mono(v):
    return f'<span style="font-family:\'Space Mono\',monospace;color:{ACC};font-weight:700;">{v}</span>'

def section(title, icon=""):
    st.markdown(f'<h2 style="margin-top:0.6rem;margin-bottom:0.25rem;">'
                f'{icon} {title}</h2>', unsafe_allow_html=True)

def stat_row(label, value, unit="", note="", color=None):
    vc = color or ACC
    return (f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:0.3rem 0;border-bottom:1px solid {BORD};">'
            f'<span style="font-size:0.78rem;color:{TX2};">{label}</span>'
            f'<span style="font-family:\'Space Mono\',monospace;font-size:0.82rem;color:{vc};font-weight:600;">'
            f'{value} {unit}'
            f'{"<span style=font-size:0.68rem;color:" + TX3 + ";margin-left:0.5rem;>" + note + "</span>" if note else ""}'
            f'</span></div>')

# ── Sidebar ────────────────────────────────────────────────────────────────
def SH(t, icon=""):
    st.markdown(
        f'<div style="font-family:\'DM Sans\',sans-serif;font-weight:700;font-size:0.65rem;'
        f'letter-spacing:0.12em;text-transform:uppercase;color:{TX3};'
        f'padding:0.35rem 0 0.2rem;margin:0.5rem 0 0.25rem;'
        f'border-bottom:1px solid {BORD};">{icon} {t}</div>',
        unsafe_allow_html=True)

with st.sidebar:
    # Header
    c1, c2 = st.columns([3.5, 1])
    with c1:
        st.markdown(f"""
<div style="display:flex;align-items:center;gap:0.45rem;">
  <div style="width:28px;height:28px;border-radius:8px;
    background:linear-gradient(135deg,{ACC},{ACC2});
    display:flex;align-items:center;justify-content:center;
    font-size:14px;box-shadow:0 2px 8px rgba({GLOW},0.3);">⚡</div>
  <div>
    <div style="font-family:'DM Sans';font-weight:700;font-size:0.85rem;color:{TX};line-height:1.1;">
      MV Cable Tool</div>
    <div style="font-family:'Space Mono';font-size:0.55rem;color:{TX3};letter-spacing:0.05em;">
      IEC 60287 · 60853</div>
  </div>
</div>""", unsafe_allow_html=True)
    with c2:
        if st.button("🌙" if not D else "☀️", key="theme_toggle"):
            st.session_state.dark = not D; st.rerun()

    st.divider()

    # ── 1 · Cable ──
    SH("Cable Selection", "①")
    Usys_kV = st.number_input(
        "System voltage (kV)", 1.0, 150.0, 20.0, 0.5, format="%.1f",
        help="Network voltage for current calculation: I = S / (√3 × U_sys)")
    v_sel = st.selectbox(
        "Insulation class (Uo/U)",
        {10: "6/10 kV", 20: "12/20 kV", 30: "18/30 kV"}.keys(),
        index=1,
        format_func=lambda v: {10: "6/10 kV", 20: "12/20 kV", 30: "18/30 kV"}[v],
        help="Cable voltage class. Determines insulation thickness and dielectric losses.")
    cables = list_cables(v_sel)
    def_i = next((i for i, k in enumerate(cables) if "240" in k), 5)
    cable_id = st.selectbox("Cross-section",
                             list(cables.keys()), index=def_i,
                             format_func=lambda k: cables[k])
    cd_sel = CABLE_LIBRARY[cable_id]
    bonding = st.selectbox("Screen bonding",
                ["single_point", "both_ends", "cross_bonded"],
                format_func=lambda x: x.replace("_", " ").title(),
                help="Single-point: best ampacity. Both-ends: circulating currents. Cross-bonded: best for long routes.")
    freq = st.selectbox("Frequency", [50, 60], 0,
                format_func=lambda f: f"{f} Hz",
                help="50 Hz (Europe/Asia) or 60 Hz (Americas)")

    with st.expander("📐 Cable Geometry"):
        st.markdown(f"""
<div style="font-family:'Space Mono',monospace;font-size:0.72rem;color:{TX2};line-height:1.8;">
  Conductor: {cd_sel['cond_mat']} {cd_sel['cond_cs']} mm² — ⌀ {cd_sel['dc_mm']:.1f} mm<br>
  Insulation OD: {cd_sel['di_mm']:.1f} mm<br>
  Cable OD: {cd_sel['OD_mm']:.1f} mm<br>
  R<sub>dc</sub> 20°C: {cd_sel['Rdc20']:.4f} Ω/km<br>
  R<sub>screen</sub>: {cd_sel['R_screen']:.3f} Ω/km ({cd_sel['A_screen']} mm² Cu)
</div>""", unsafe_allow_html=True)

    st.divider()

    # ── 2 · Installation ──
    SH("Installation", "②")
    formation = st.selectbox("Formation", ["trefoil", "flat"],
                format_func=str.title,
                help="Trefoil: cables touching in triangle. Flat: horizontal line.")
    depth_m = st.slider("Burial depth (m)", 0.4, 3.0, 0.9, 0.05, format="%.2f m",
                help="Depth to centroid. Typical: 0.8–1.2 m")
    spacing_mm = 0
    n_circ = st.number_input("Circuits", 1, 8, 1, step=1,
                help="Parallel three-phase circuits in trench")
    _nc = int(n_circ)
    if _nc > 1:
        _cct_sep_min = int(cd_sel["OD_mm"]) + 10
        cct_sep_mm = st.slider("Circuit gap (mm)",
            _cct_sep_min, 3000, 250, 10, format="%d mm",
            help="Clear gap between adjacent circuits")
    else:
        cct_sep_mm = 0
    trench_w = st.slider("Trench width (m)", 0.3, 3.0, 0.6, 0.05, format="%.2f m")
    rho_backfill = st.number_input(
        "Backfill ρ (K·m/W)", min_value=0.0, max_value=5.0, value=0.0,
        step=0.05, format="%.2f",
        help="FTB: 0.8–1.0. Sand: 1.0–1.2. Set 0 to disable.")
    in_duct = st.checkbox("In duct",
                help="Add duct thermal resistance (T4_duct)")
    ddi = ddo = 0.0
    if in_duct:
        ddi = st.number_input("Duct inner ⌀ (mm)", 60, 300, 110, 5)
        ddo = st.number_input("Duct outer ⌀ (mm)", 75, 330, 125, 5)

    st.divider()

    # ── 3 · Soil ──
    SH("Soil & Environment", "③")
    T_amb = st.slider("Ambient temp (°C)", 5, 50, 20, 1,
                help="Undisturbed soil temp. Every +1°C ≈ -1% ampacity.")
    rho_wet = st.slider("Wet soil ρ (K·m/W)", 0.5, 3.0, 1.0, 0.05, format="%.2f",
                help="Moist soil. 0.7–1.2 (clay), 1.0–1.5 (sand)")
    rho_dry = st.slider("Dry soil ρ (K·m/W)", 1.0, 5.0, 2.5, 0.1, format="%.1f",
                help="Desiccated soil. 2.0–3.5 typical")
    T_crit = st.slider("Dry-out threshold (°C)", 35, 70, 50, 1,
                help="Surface temp for moisture migration (50–60°C)")
    two_zone = st.checkbox("Two-zone drying model", True,
                help="IEC 60287-2-1 §2.2.3 two-zone soil model")

    st.divider()

    # ── 4 · Load Profile ──
    SH("Load Profile", "④")
    p_src = st.radio("Source", ["Standard", "Custom"], horizontal=True)
    if p_src == "Standard":
        pk = st.selectbox("Profile", list(PROFILE_LABELS.keys()),
                          format_func=lambda k: PROFILE_LABELS[k])
        load_profile = LOAD_PROFILES[pk]
    else:
        raw = st.text_area("24 values (0–1), comma-separated",
                           ",".join(f"{v:.2f}" for v in LOAD_PROFILES["residential"]), height=68)
        try:
            vals = [float(x.strip()) for x in raw.split(",")]
            load_profile = vals if len(vals) == 24 else LOAD_PROFILES["flat"]
        except:
            load_profile = LOAD_PROFILES["flat"]
    mu_prev = PROFILE_MU.get(pk if p_src == "Standard" else "custom",
                              sum((v / max(load_profile))**2 for v in load_profile) / 24)
    st.markdown(f'<div style="font-family:\'Space Mono\',monospace;font-size:0.68rem;color:{TX3};">'
                f'μ = {mu_prev:.4f}</div>', unsafe_allow_html=True)

    st.divider()

    # ── 5 · Load Parameters ──
    SH("Load Parameters", "⑤")
    S_MVA = st.number_input("Apparent power S (MVA)", 0.05, 500.0, 5.0, 0.1, format="%.2f")
    pf_load = st.slider("Power factor", 0.70, 1.00, 0.95, 0.01, format="%.2f")
    L_km = st.number_input("Route length (km)", 0.05, 200.0, 2.0, 0.1, format="%.2f")
    Isc_kA = st.number_input("Fault current (kA)", 0.5, 63.0, 10.0, 0.5, format="%.1f")
    t_fault = st.slider("Fault clearance (s)", 0.05, 3.0, 0.5, 0.05, format="%.2f s")
    dU_lim = st.slider("ΔU limit (%)", 1.0, 15.0, 5.0, 0.5, format="%.1f%%")

    st.divider()

    # ── 6 · Report ──
    SH("Report Details", "⑥")
    proj_n = st.text_input("Project name", "MV Cable Study")
    eng_n = st.text_input("Engineer", "")
    proj_r = st.text_input("Reference", "")

    st.divider()
    run_btn = st.button("▶  CALCULATE", type="primary")

# ── Build engine objects ──────────────────────────────────────────────────────
inst_p = InstallationParams(
    depth=depth_m, formation=formation,
    phase_spacing=spacing_mm * 1e-3, num_circuits=int(n_circ),
    circuit_separation=cct_sep_mm * 1e-3,
    in_duct=in_duct, duct_di_mm=ddi, duct_do_mm=ddo,
    trench_width=trench_w,
    rho_backfill=float(rho_backfill))
soil_p = SoilParams(rho_wet=rho_wet, rho_dry=rho_dry,
                    T_amb=T_amb, T_crit=T_crit, two_zone=two_zone)
load_p = LoadParams(S_MVA=S_MVA, pf=pf_load, L_km=L_km,
                    Isc_kA=Isc_kA, t_fault=t_fault, dU_limit_pct=dU_lim,
                    system_voltage_kV=float(Usys_kV))

engine = build_engine(cd_sel, inst_p, soil_p, float(freq), bonding)

# ── Run / cache ───────────────────────────────────────────────────────────────
if run_btn:
    with st.spinner("Running IEC 60287 / IEC 60853 calculation…"):
        try:
            res = engine.calculate(load_profile=load_profile,
                                   L_km=L_km, pf=pf_load)
            ar = analyse(engine, res, load_p, cable_id, load_profile)
            st.session_state.update({"res": res, "ar": ar, "eng": engine, "cd_id": cable_id})
        except Exception as exc:
            st.error(f"Calculation error: {exc}")
            import traceback; st.text(traceback.format_exc()); res = ar = None
else:
    res = st.session_state.get("res")
    ar = st.session_state.get("ar")
    engine = st.session_state.get("eng", engine)

# ── Drawing wrappers ──────────────────────────────────────────────────────────
def draw_trench(eng, result, figsize=(12.0, 8.5)):
    return _draw_trench_viz(eng, result, dark=D, figsize=figsize)

def draw_profile(profile, mu, label=""):
    return _draw_profile_viz(profile, mu, label=label, dark=D)


# ── Main layout ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;align-items:center;gap:0.8rem;margin-bottom:0.1rem;padding:0.3rem 0;">
  <div style="width:40px;height:40px;border-radius:12px;
    background:linear-gradient(135deg,{ACC},{ACC2});
    display:flex;align-items:center;justify-content:center;
    font-size:20px;box-shadow:0 3px 15px rgba({GLOW},0.3);flex-shrink:0;">⚡</div>
  <div>
    <div style="font-family:'DM Sans',sans-serif;font-size:1.4rem;font-weight:700;color:{TX};line-height:1.15;">
      MV Cable Thermal Rating</div>
    <div style="font-family:'Space Mono',monospace;font-size:0.6rem;color:{TX3};letter-spacing:0.04em;">
      IEC 60287 · IEC 60853 · VDE 0276-1000 · Prysmian NA2XS(F)2Y · 10 / 20 / 30 kV · 50–1000 mm²</div>
  </div>
</div>
""", unsafe_allow_html=True)

col_main, = [st.container()]
with col_main:
    if res is None:
        # ── Welcome state ──
        st.markdown(f"""
<div style="background:linear-gradient(135deg,{CARD},{CARD2});
     border:1px solid {BORD};border-radius:16px;
     padding:1.8rem 2.2rem;margin:0.8rem 0;">
  <div style="font-family:'DM Sans',sans-serif;font-weight:700;font-size:1.0rem;
       color:{ACC};margin-bottom:1rem;display:flex;align-items:center;gap:0.5rem;">
    <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{ACC};
      box-shadow:0 0 8px rgba({GLOW},0.5);"></span>
    Getting Started
  </div>
  <div style="font-family:'DM Sans',sans-serif;font-size:0.82rem;color:{TX2};line-height:1.9;">
    <div style="display:grid;grid-template-columns:24px 1fr;gap:0.3rem 0.6rem;align-items:start;">
      <span style="color:{ACC};font-family:'Space Mono';font-size:0.7rem;text-align:right;">01</span>
      <span>Select a Prysmian NA2XS(F)2Y cable from the sidebar</span>
      <span style="color:{ACC};font-family:'Space Mono';font-size:0.7rem;text-align:right;">02</span>
      <span>Configure installation: depth, formation, circuits</span>
      <span style="color:{ACC};font-family:'Space Mono';font-size:0.7rem;text-align:right;">03</span>
      <span>Set soil thermal properties and ambient temperature</span>
      <span style="color:{ACC};font-family:'Space Mono';font-size:0.7rem;text-align:right;">04</span>
      <span>Choose a daily load profile for cyclic rating (IEC 60853-2)</span>
      <span style="color:{ACC};font-family:'Space Mono';font-size:0.7rem;text-align:right;">05</span>
      <span>Enter load parameters: power, fault current, route length</span>
      <span style="color:{ACC};font-family:'Space Mono';font-size:0.7rem;text-align:right;">06</span>
      <span>Click <strong style="color:{ACC};">▶ CALCULATE</strong> to run the IEC analysis</span>
    </div>
  </div>
  <div style="font-family:'Space Mono',monospace;font-size:0.6rem;
       color:{TX3};margin-top:1.2rem;padding-top:0.8rem;border-top:1px solid {BORD};">
    IEC 60287-1-1 (n=1, two-zone soil) · IEC 60853-2 (cyclic M-factor) · IEC 60949 (SC withstand)
  </div>
</div>""", unsafe_allow_html=True)

        # Trench preview
        section("Trench Cross-Section", "📐")
        try:
            fig_tr_prev = draw_trench(engine, None, figsize=(13.0, 9.0))
            st.pyplot(fig_tr_prev, use_container_width=True)
            plt.close(fig_tr_prev)
        except Exception as e:
            st.error(f"Trench render error: {e}")

        # Profile preview
        section("Load Profile Preview", "📊")
        fig_lp = draw_profile(load_profile, PROFILE_MU.get(
            pk if p_src == "Standard" else "custom", mu_prev))
        st.pyplot(fig_lp, use_container_width=True)
        plt.close(fig_lp)

    else:
        # ── Results tabs ──
        tabs = st.tabs(["📊 Thermal Results", "📐 Trench View", "🔌 Load Analysis",
                         "⚠️ Risks & Recs", "📈 Load Profile", "🔬 Detailed"])

        # ── Tab 1: Results ────────────────────────────────────────────────────
        with tabs[0]:
            # Voltage mismatch info
            if abs(Usys_kV - cd_sel["U_kV"]) > 0.5:
                _I_sys = S_MVA * 1e6 / (math.sqrt(3) * Usys_kV * 1e3)
                _I_cab = S_MVA * 1e6 / (math.sqrt(3) * cd_sel["U_kV"] * 1e3)
                st.info(f"System voltage ({Usys_kV:.1f} kV) ≠ cable rated ({cd_sel['U_kV']} kV) → "
                        f"I = {_I_sys:.0f} A (at {Usys_kV:.1f} kV), would be {_I_cab:.0f} A at rated.")

            section("Ampacity Results", "⚡")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Continuous", f"{res.I_cont:.0f} A",
                      delta=f"θ = {res.theta_cond:.1f} °C")
            c2.metric("Cyclic (IEC 60853-2)", f"{res.I_cyclic:.0f} A",
                      delta=f"M = {res.M_cyclic:.3f}  μ = {res.mu:.3f}")
            c3.metric("Emergency (8h)", f"{res.I_emerg:.0f} A",
                      delta="θ_e = 105 °C")
            c4.metric("Surface Temp.", f"{res.theta_surface:.1f} °C",
                      delta="🔴 DRY ZONE" if res.dry_zone else "✅ No drying")

            section("Temperature Distribution", "🌡️")
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Conductor θ", f"{res.theta_cond:.2f} °C",
                      delta=f"max = 90 °C")
            t2.metric("Screen θ", f"{res.theta_screen:.1f} °C")
            t3.metric("Cable Surface", f"{res.theta_surface:.1f} °C",
                      delta=f"crit. = {soil_p.T_crit} °C")
            t4.metric("Ambient θ", f"{soil_p.T_amb} °C")

            section("Thermal Resistance Circuit", "🔗")
            rc1, rc2, rc3, rc4, rc5 = st.columns(5)
            rc1.metric("T₁ Insulation", f"{res.T1:.4f}")
            rc2.metric("T₂ Screen", f"{res.T2:.5f}")
            rc3.metric("T₃ Jacket", f"{res.T3:.4f}")
            rc4.metric("T₄ Soil", f"{res.T4_soil:.4f}")
            rc5.metric("T₄ Mutual", f"{res.T4_mutual:.4f}")

            if res.dry_zone:
                st.markdown(f"""
<div style="background:{'#180808' if D else '#fff0f0'};border:1px solid {RED};
     border-radius:10px;padding:0.7rem 1rem;margin:0.5rem 0;">
  <div style="font-family:'Space Mono',monospace;font-size:0.78rem;color:{RED};font-weight:700;">
    ⚠ DRY-ZONE ACTIVE — IEC 60287-2-1 §2.2.3
  </div>
  <div style="font-family:'Space Mono',monospace;font-size:0.7rem;color:{TX2};margin-top:0.25rem;">
    r<sub>x</sub> = {res.rx_m*100:.1f} cm · T₄_dry = {res.T4_dry:.4f} K·m/W · T₄_moist = {res.T4_self:.4f} K·m/W
  </div>
</div>""", unsafe_allow_html=True)

            section("Losses", "🔥")
            la1, la2, la3, la4 = st.columns(4)
            la1.metric("Rac at θ", f"{res.Rac*1e3:.4f} mΩ/m")
            la2.metric("I²R losses", f"{res.W_I2R:.3f} W/m",
                       delta=f"λ₁={res.lambda1:.4f}")
            la3.metric("Dielectric Wd", f"{res.W_d*1e3:.3f} mW/m")
            la4.metric("Screen losses", f"{res.W_s:.4f} W/m")

            section("Electrical Parameters", "⚙️")
            e1, e2, e3 = st.columns(3)
            e1.metric("Reactance X₁", f"{res.X_ohm_km:.4f} Ω/km")
            e2.metric("Capacitance C", f"{res.C_nF_km:.2f} nF/km")
            e3.metric("Charging Ic", f"{res.Ic_A:.2f} A")

            st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;
     padding:0.5rem 0.9rem;margin-top:0.3rem;font-family:'Space Mono',monospace;
     font-size:0.7rem;color:{TX2};">
  Voltage drop at rated: {res.dU_V:.0f} V · {res.dU_pct:.3f}% (R at θ={res.theta_cond:.1f}°C)
</div>""", unsafe_allow_html=True)

            for w in res.warnings:
                st.warning(w)

        # ── Tab 2: Trench View ──────────────────────────────────────────────
        with tabs[1]:
            try:
                fig_tr = draw_trench(engine, res, figsize=(13.0, 9.0))
                st.pyplot(fig_tr, use_container_width=True)
                plt.close(fig_tr)
            except Exception as e:
                st.error(f"Trench render error: {e}")

            with st.expander("📐 Geometric Parameters"):
                st.markdown(f"""
<div style="font-family:'Space Mono',monospace;font-size:0.72rem;color:{TX2};line-height:1.9;">
  Conductor ⌀: {engine.dc*1000:.2f} mm<br>
  Insulation OD: {engine.di*1000:.2f} mm<br>
  Screen mean ⌀: {engine.ds*1000:.2f} mm<br>
  Cable OD: {engine.De*1000:.2f} mm<br>
  Capacitance: {engine.C*1e12:.2f} pF/m<br>
  Reactance X₁: {engine.X*1e3:.4f} Ω/km
</div>""", unsafe_allow_html=True)

        # ── Tab 3: Load Analysis ──────────────────────────────────────────────
        with tabs[2]:
            if ar:
                section("Load Summary", "📋")
                la1, la2, la3, la4 = st.columns(4)
                la1.metric("Load Current", f"{ar.I_load:.1f} A",
                            delta=f"{ar.util_cont_pct:.1f}% utilisation")
                la2.metric("Active Power P", f"{ar.P_MW:.2f} MW",
                            delta=f"Q = {ar.Q_Mvar:.2f} Mvar")
                la3.metric("θ at Load", f"{ar.theta_at_load:.1f} °C")
                la4.metric("Voltage Drop", f"{ar.dU_load_pct:.3f}%",
                            delta=f"{ar.dU_load_V:.0f} V ({load_p.L_km:.1f} km)")

                section("Design Checks", "✅")
                for c in ar.checks:
                    icon = "✅" if c.passed else "❌"
                    col = GRN if c.passed else RED
                    if D:
                        bg = "#0a1a10" if c.passed else "#1a0a0a"
                    else:
                        bg = "#f0faf2" if c.passed else "#fdf2f2"
                    st.markdown(f"""
<div style="background:{bg};border:1px solid {col}30;border-left:3px solid {col};
     border-radius:0 10px 10px 0;
     padding:0.45rem 0.9rem;margin:0.2rem 0;display:flex;justify-content:space-between;
     align-items:center;transition:transform 0.1s;">
  <span style="font-family:'DM Sans',sans-serif;font-size:0.8rem;font-weight:600;color:{TX};">
    {icon} {c.name}
  </span>
  <span style="font-family:'Space Mono',monospace;font-size:0.72rem;color:{TX2};">
    {c.measured} / {c.limit}
    <span style="color:{col};margin-left:0.5rem;font-weight:700;">
      {f'{c.margin_pct:+.1f}%' if c.margin_pct else ''}
    </span>
  </span>
</div>""", unsafe_allow_html=True)

                section("Short-Circuit Withstand", "⚡")
                s1, s2 = st.columns(2)
                s1.metric("Conductor SC Limit", f"{ar.Isc_cond_kA:.2f} kA",
                           delta=f"at {load_p.t_fault:.2f}s, k={143 if cd_sel['cond_mat']=='Cu' else 94}")
                s2.metric("Screen SC Limit", f"{ar.Isc_screen_kA:.2f} kA",
                           delta=f"{cd_sel['A_screen']} mm² Cu, k=143")

                # Alternatives
                if ar.alt_up_id or ar.alt_down_id:
                    section("Cable Alternatives", "🔄")
                    if ar.alt_up_id:
                        up = CABLE_LIBRARY[ar.alt_up_id]
                        st.markdown(f"""
<div style="background:{CARD};border:1px solid {ORG}40;border-left:3px solid {ORG};
     border-radius:0 10px 10px 0;padding:0.5rem 0.9rem;margin:0.2rem 0;">
  <span style="font-family:'DM Sans';font-size:0.78rem;font-weight:700;color:{ORG};">▲ Upsize:</span>
  <span style="font-family:'Space Mono';font-size:0.72rem;color:{TX2};margin-left:0.4rem;">
    {up['name']}</span>
</div>""", unsafe_allow_html=True)
                    if ar.alt_down_id:
                        dn = CABLE_LIBRARY[ar.alt_down_id]
                        st.markdown(f"""
<div style="background:{CARD};border:1px solid {GRN}40;border-left:3px solid {GRN};
     border-radius:0 10px 10px 0;padding:0.5rem 0.9rem;margin:0.2rem 0;">
  <span style="font-family:'DM Sans';font-size:0.78rem;font-weight:700;color:{GRN};">▼ Downsize:</span>
  <span style="font-family:'Space Mono';font-size:0.72rem;color:{TX2};margin-left:0.4rem;">
    {dn['name']}</span>
</div>""", unsafe_allow_html=True)

        # ── Tab 4: Risks & Recommendations ───────────────────────────────────
        with tabs[3]:
            if ar:
                section("Recommendations", "💡")
                level_icon = {"critical": "🔴", "warning": "🟠", "info": "🔵"}
                level_col = {"critical": RED, "warning": ORG, "info": ACC2}
                for rec in ar.recs:
                    lc = level_col.get(rec.level, BORD)
                    st.markdown(f"""
<div style="background:{CARD};border:1px solid {lc}25;border-left:3px solid {lc};
     border-radius:0 12px 12px 0;padding:0.7rem 1.1rem;margin:0.35rem 0;">
  <div style="font-family:'DM Sans',sans-serif;font-size:0.82rem;font-weight:700;color:{lc};
       margin-bottom:0.25rem;">
    {level_icon.get(rec.level, '•')} {rec.title}
  </div>
  <div style="font-family:'DM Sans',sans-serif;font-size:0.76rem;color:{TX2};line-height:1.6;">
    {rec.body}
  </div>
  {'<div style="font-family:DM Sans,sans-serif;font-size:0.74rem;color:'+ACC+';margin-top:0.3rem;font-weight:600;">→ '+rec.action+'</div>' if rec.action else ''}
</div>""", unsafe_allow_html=True)

                section("Risk Register", "🛡️")
                sev_order = {"HIGH": 0, "MED": 1, "LOW": 2, "OK": 3}
                risks_sorted = sorted(ar.risks, key=lambda r: sev_order.get(r["sev"], 9))
                for rk in risks_sorted:
                    st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;
     padding:0.55rem 0.9rem;margin:0.25rem 0;display:flex;gap:0.75rem;align-items:flex-start;">
  <div style="background:{rk['col']};color:#fff;border-radius:6px;padding:0.12rem 0.5rem;
       font-family:'Space Mono',monospace;font-size:0.62rem;font-weight:700;
       white-space:nowrap;margin-top:0.08rem;min-width:36px;text-align:center;">{rk['sev']}</div>
  <div>
    <div style="font-family:'DM Sans',sans-serif;font-size:0.8rem;font-weight:600;
         color:{TX};margin-bottom:0.1rem;">{rk['title']}</div>
    <div style="font-family:'DM Sans',sans-serif;font-size:0.72rem;color:{TX2};
         line-height:1.5;">{rk['desc']}</div>
  </div>
</div>""", unsafe_allow_html=True)

        # ── Tab 5: Load Profile ───────────────────────────────────────────────
        with tabs[4]:
            section("24-Hour Load Profile", "📈")
            fig_lp = draw_profile(load_profile, res.mu)
            st.pyplot(fig_lp, use_container_width=True)
            plt.close(fig_lp)
            st.markdown(f"""
<div style="background:{CARD};border:1px solid {BORD};border-radius:10px;
     padding:0.6rem 1rem;margin:0.4rem 0;font-family:'Space Mono',monospace;
     font-size:0.7rem;color:{TX2};line-height:1.7;">
  μ = {res.mu:.4f} · M = {res.M_cyclic:.4f}<br>
  I_cyc = I_cont × M = {res.I_cont:.1f} × {res.M_cyclic:.4f} = {res.I_cyclic:.1f} A<br>
  Method: IEC 60853-2 §3.3 | M² = (T_cable + T₄) / (T_cable + μ·T₄)<br>
  Profile: {PROFILE_LABELS.get(pk if p_src=='Standard' else 'custom', 'Custom')}
</div>""", unsafe_allow_html=True)

        # ── Tab 6: Detailed breakdown ─────────────────────────────────────────
        with tabs[5]:
            section("AC Resistance Breakdown", "🔬")
            d1, d2, d3, d4 = st.columns(4)
            d1.metric("R_dc at θ", f"{res.Rdc*1e3:.4f} mΩ/m")
            d2.metric("Skin Ys", f"{res.Ys:.5f}")
            d3.metric("Proximity Yp", f"{res.Yp:.5f}")
            d4.metric("R_ac", f"{res.Rac*1e3:.4f} mΩ/m")

            section("Screen Loss Detail", "📡")
            sl1, sl2, sl3 = st.columns(3)
            sl1.metric("λ₁ circulating", f"{res.lambda1_circ:.5f}")
            sl2.metric("λ₁ eddy", f"{res.lambda1_eddy:.5f}")
            sl3.metric("λ₁ total", f"{res.lambda1:.5f}")

            with st.expander("Full Thermal Resistance Detail"):
                st.markdown(f"""
| Component | Symbol | Value (K·m/W) | Clause |
|---|---|---|---|
| XLPE Insulation | T₁ | {res.T1:.6f} | IEC 60287-2-1 §2.1 eq.(1) |
| Cu screen | T₂ | {res.T2:.6f} | §2.1 eq.(2) |
| PE jacket | T₃ | {res.T3:.6f} | §2.1 eq.(3) |
| Soil self | T₄s | {res.T4_self:.6f} | §2.2.1 eq.(6) |
| Dry zone | T₄d | {res.T4_dry:.6f} | §2.2.3 eq.(7) |
| Mutual heating | T₄m | {res.T4_mutual:.6f} | §2.2.2 |
| Duct | T₄duct | {res.T4_duct:.6f} | §2.2.2 eq.(19-20) |
| Backfill correction | T₄trench | {res.T4_trench:.6f} | §2.2.4 |
| **TOTAL soil** | **T₄** | **{res.T4_soil:.6f}** | — |
""")

            with st.expander("Cyclic Rating Derivation"):
                T4_cyc = res.T4_self + res.T4_dry
                T4_steady = res.T4_mutual + res.T4_duct + res.T4_trench
                Wd_v = res.W_d
                Wd_term = Wd_v * (res.T1 / 2 + res.T2 + res.T3 + T4_cyc + T4_steady)
                R_eff = res.Rac * (res.T1 + (1 + res.lambda1) * (res.T2 + res.T3)
                                   + (1 + res.lambda1) * res.mu * T4_cyc
                                   + (1 + res.lambda1) * T4_steady)
                st.markdown(f"""
**IEC 60853-2 — Decoupled Cyclic Ampacity**

```
T4_cyc    = T4_self + T4_dry  = {T4_cyc:.5f} K·m/W  (cycles)
T4_steady = T4_mutual + T4_duct + T4_trench = {T4_steady:.5f} K·m/W  (steady)

μ (loss-load factor) = {res.mu:.4f}

R_eff = Rac·[T1 + (1+λ1)·(T2+T3) + (1+λ1)·μ·T4_cyc + (1+λ1)·T4_steady]
      = {R_eff:.6f} K/W per (A²·m)

Wd_term = {Wd_term:.6f} K/m

dT_limit = 90°C − {soil_p.T_amb}°C = {90 - soil_p.T_amb}°C

I_cyc = √( (dT_limit − Wd_term) / R_eff )
      = {res.I_cyclic:.1f} A

M_eff = I_cyc / I_cont = {res.M_cyclic:.4f}
```
""")

        # ── PDF export ────────────────────────────────────────────────────────
        st.divider()
        if st.button("📄  EXPORT PDF REPORT"):
            with st.spinner("Generating report…"):
                try:
                    pdf_bytes = generate_pdf(
                        engine, res, ar, load_p,
                        pk if p_src == "Standard" else "custom",
                        proj=proj_n, eng_name=eng_n, ref=proj_r)
                    st.download_button(
                        "⬇  Download PDF",
                        data=pdf_bytes,
                        file_name=f"MV_Cable_{cd_sel['cond_cs']}mm2_{cd_sel['U_kV']}kV.pdf",
                        mime="application/pdf",
                        type="primary")
                except Exception as ex:
                    st.error(f"PDF error: {ex}")

# ── Footer ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="border-top:1px solid {BORD};padding-top:0.6rem;margin-top:1.5rem;
     text-align:center;">
  <div style="font-family:'Space Mono',monospace;font-size:0.58rem;color:{TX3};letter-spacing:0.03em;">
    IEC 60287-1-1:2014 · IEC 60287-2-1:2015 · IEC 60853-2:1989 · IEC 60502-2:2014 ·
    IEC 60228:2004 · IEC 60949:1988 · VDE 0276-1000
  </div>
  <div style="font-family:'DM Sans',sans-serif;font-size:0.55rem;color:{TX3};margin-top:0.25rem;">
    Analytical engine — not a substitute for FEA on complex installations
  </div>
</div>""", unsafe_allow_html=True)
