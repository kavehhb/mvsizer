"""
cable_data.py — Prysmian NA2XS(F)2Y Cable Database + Material Constants
=========================================================================
Sources:
  • Prysmian Group "Cables for Medium Voltage Networks" catalogue (2023)
  • IEC 60228:2004      — Conductor DC resistance (class 2, Al, Table 1)
  • IEC 60502-2:2014    — Insulation thickness (Table 3)
  • IEC 60287-1-1:2014  — Material constants (Table 1, Annex C)
  • VDE 0276-1000 / HD 620 S2

Insulation thickness (IEC 60502-2 Table 3 XLPE):
   6/10 kV  (Uo/U) → 3.4 mm
  12/20 kV  (Uo/U) → 5.5 mm
  18/30 kV  (Uo/U) → 8.0 mm

Cu screen cross-sections (Prysmian standard design):
  conductor ≤185 mm²  → 16 mm²  (R=1.159 Ω/km at 20°C)
  conductor 240–300   → 25 mm²  (R=0.727 Ω/km)
  conductor ≥400      → 35 mm²  (R=0.524 Ω/km)
"""

import math
from typing import Dict, Optional, List

# ─────────────────────────────────────────────────────────────────────────────
#  Material constants   (IEC 60287-1-1)
# ─────────────────────────────────────────────────────────────────────────────
MATERIAL: Dict = {
    # Temperature coefficient of resistance at 20°C  [1/°C]  IEC T1
    "alpha": {"Cu": 3.93e-3, "Al": 4.03e-3},

    # Insulation relative permittivity εr  IEC Annex C
    "permittivity": {"XLPE": 2.5, "EPR": 3.0, "PVC": 8.0},

    # Insulation loss tangent tan δ  IEC Annex C
    "tan_delta": {"XLPE": 4.0e-4, "EPR": 2.0e-3, "PVC": 1.0e-1},

    # Insulation thermal resistivity ρ [K·m/W]  IEC 60287-2-1 Table 1
    "ins_rho": {"XLPE": 3.5, "EPR": 3.5, "PVC": 5.0},

    # Max continuous conductor temperature [°C]  IEC 60502-2
    "T_max": {"XLPE": 90.0, "EPR": 90.0, "PVC": 70.0},

    # Emergency conductor temperature (8 h)  IEC 60853-2
    "T_emerg": {"XLPE": 105.0, "EPR": 105.0, "PVC": 85.0},

    # Outer sheath thermal resistivity [K·m/W]
    "sheath_rho": {"PE": 3.5, "PVC": 5.0, "HDPE": 3.5, "LSOH": 3.5},

    # Volumetric heat capacity [J/(m³·K)]  IEC 60853-2 Annex B
    "Qv": {"Cu": 3.45e6, "Al": 2.50e6,
           "XLPE": 2.4e6, "EPR": 2.4e6, "PVC": 1.7e6,
           "Cu_screen": 3.45e6},

    # Skin / proximity effect factors (ks, kp)  IEC 60287-1-1 Table 2
    "skin_prox": {
        "stranded":    {"ks": 1.0,   "kp": 0.8},
        "solid":       {"ks": 1.0,   "kp": 1.0},
        "milliken_al": {"ks": 1.0,   "kp": 0.56},
        "milliken_cu": {"ks": 0.435, "kp": 0.37},
        "sector":      {"ks": 1.0,   "kp": 0.8},
    },

    # Short-circuit k-factor [A·s^0.5/mm²]  IEC 60949
    "sc_k": {
        "XLPE_Al": 94.0,  "XLPE_Cu": 143.0,
        "EPR_Al":  94.0,  "EPR_Cu":  143.0,
        "screen_Cu": 135.0,  # wire screen: 135 per VDE helical-tape unequal distribution
    },
}


# ─────────────────────────────────────────────────────────────────────────────
#  Cable entry builder
# ─────────────────────────────────────────────────────────────────────────────
def _c(Uo, U, cs, dc, ti, ts, dsm, As, Rs, tj, OD, Rdc, strand="stranded"):
    """Build one cable dict.
    Uo/U kV  cs mm²  dc conductor-diam(mm)  ti ins-thick(mm)
    ts screen-thick(mm)  dsm screen-mean-diam(mm)
    As screen-area(mm²)  Rs screen-R(Ω/km@20°C)
    tj jacket-thick(mm)  OD cable-OD(mm)  Rdc conductor-R(Ω/km@20°C)
    """
    label = "16" if As == 16 else str(As)
    return dict(
        name=f"NA2XS(F)2Y {Uo:.0f}/{U:.0f}kV 1×{cs} AL/{label}",
        Uo_kV=float(Uo), U_kV=float(U),
        cond_mat="Al", cond_cs=cs,
        dc_mm=float(dc), strand=strand,
        Rdc20=float(Rdc),              # Ω/km @ 20 °C
        ins_mat="XLPE", t_ins=float(ti),
        di_mm=round(dc + 2*ti, 2),    # insulation OD
        t_screen=float(ts),
        d_screen_mean=float(dsm),
        A_screen=int(As),
        R_screen=float(Rs),            # Ω/km @ 20 °C
        screen_mat="Cu",
        jacket_mat="PE", t_jacket=float(tj),
        OD_mm=float(OD),
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Prysmian NA2XS(F)2Y catalogue
# ─────────────────────────────────────────────────────────────────────────────
CABLE_LIBRARY: Dict[str, dict] = {}

# ── 6/10 kV  (t_ins = 3.4 mm) ────────────────────────────────────────────────
for _r in [
    #  cs   dc    ti   ts  dsm   As    Rs     tj    OD     Rdc       strand
    (  50, 7.9, 3.4, 0.5, 17.2, 16, 1.159, 2.4, 24.9, 0.6410, "stranded"),
    (  70, 9.4, 3.4, 0.5, 18.7, 16, 1.159, 2.5, 26.4, 0.4430, "stranded"),
    (  95,10.8, 3.4, 0.5, 20.1, 16, 1.159, 2.6, 27.9, 0.3200, "stranded"),
    ( 120,12.4, 3.4, 0.5, 21.7, 16, 1.159, 2.6, 29.5, 0.2530, "stranded"),
    ( 150,13.4, 3.4, 0.5, 22.7, 16, 1.159, 2.7, 30.5, 0.2060, "stranded"),
    ( 185,14.8, 3.4, 0.5, 24.1, 16, 1.159, 2.8, 32.0, 0.1640, "stranded"),
    ( 240,17.0, 3.4, 0.7, 26.6, 25, 0.727, 2.9, 34.7, 0.1250, "stranded"),
    ( 300,19.0, 3.4, 0.7, 28.6, 25, 0.727, 3.0, 36.9, 0.1000, "stranded"),
    ( 400,21.4, 3.4, 0.8, 31.2, 35, 0.524, 3.1, 39.8, 0.0778, "stranded"),
    ( 500,24.2, 3.4, 0.8, 34.0, 35, 0.524, 3.2, 43.0, 0.0605, "stranded"),
    ( 630,27.6, 3.4, 0.9, 37.5, 35, 0.524, 3.3, 46.9, 0.0469, "stranded"),
    ( 800,31.2, 3.4, 1.0, 41.3, 35, 0.524, 3.4, 51.1, 0.0367, "milliken_al"),
    (1000,35.2, 3.4, 1.1, 45.5, 35, 0.524, 3.6, 55.9, 0.0291, "milliken_al"),
]:
    CABLE_LIBRARY[f"AL{_r[0]}_6_10kV"] = _c(6, 10, *_r)

# ── 12/20 kV  (t_ins = 5.5 mm) ───────────────────────────────────────────────
for _r in [
    (  50, 7.9, 5.5, 0.5, 19.9, 16, 1.159, 2.6, 27.6, 0.6410, "stranded"),
    (  70, 9.4, 5.5, 0.5, 21.4, 16, 1.159, 2.7, 29.1, 0.4430, "stranded"),
    (  95,10.8, 5.5, 0.5, 22.8, 16, 1.159, 2.8, 30.6, 0.3200, "stranded"),
    ( 120,12.4, 5.5, 0.5, 24.4, 16, 1.159, 2.8, 32.2, 0.2530, "stranded"),
    ( 150,13.4, 5.5, 0.5, 25.4, 16, 1.159, 2.9, 33.3, 0.2060, "stranded"),
    ( 185,14.8, 5.5, 0.5, 26.8, 16, 1.159, 2.9, 34.8, 0.1640, "stranded"),
    ( 240,17.0, 5.5, 0.7, 29.4, 25, 0.727, 3.1, 37.9, 0.1250, "stranded"),
    ( 300,19.0, 5.5, 0.7, 31.4, 25, 0.727, 3.2, 40.1, 0.1000, "stranded"),
    ( 400,21.4, 5.5, 0.8, 34.0, 35, 0.524, 3.3, 43.1, 0.0778, "stranded"),
    ( 500,24.2, 5.5, 0.8, 36.8, 35, 0.524, 3.4, 46.3, 0.0605, "stranded"),
    ( 630,27.6, 5.5, 0.9, 40.3, 35, 0.524, 3.5, 50.3, 0.0469, "stranded"),
    ( 800,31.2, 5.5, 1.0, 44.1, 35, 0.524, 3.6, 54.7, 0.0367, "milliken_al"),
    (1000,35.2, 5.5, 1.1, 48.3, 35, 0.524, 3.8, 59.6, 0.0291, "milliken_al"),
]:
    CABLE_LIBRARY[f"AL{_r[0]}_12_20kV"] = _c(12, 20, *_r)

# ── 18/30 kV  (t_ins = 8.0 mm) ───────────────────────────────────────────────
for _r in [
    (  50, 7.9, 8.0, 0.5, 24.9, 16, 1.159, 2.8, 33.3, 0.6410, "stranded"),
    (  70, 9.4, 8.0, 0.5, 26.4, 16, 1.159, 2.9, 34.8, 0.4430, "stranded"),
    (  95,10.8, 8.0, 0.5, 27.8, 16, 1.159, 2.9, 36.3, 0.3200, "stranded"),
    ( 120,12.4, 8.0, 0.5, 29.4, 16, 1.159, 3.0, 38.0, 0.2530, "stranded"),
    ( 150,13.4, 8.0, 0.5, 30.4, 16, 1.159, 3.0, 39.1, 0.2060, "stranded"),
    ( 185,14.8, 8.0, 0.5, 31.8, 16, 1.159, 3.1, 40.7, 0.1640, "stranded"),
    ( 240,17.0, 8.0, 0.7, 34.4, 25, 0.727, 3.2, 44.1, 0.1250, "stranded"),
    ( 300,19.0, 8.0, 0.7, 36.4, 25, 0.727, 3.3, 46.4, 0.1000, "stranded"),
    ( 400,21.4, 8.0, 0.8, 39.0, 35, 0.524, 3.4, 49.5, 0.0778, "stranded"),
    ( 500,24.2, 8.0, 0.8, 41.8, 35, 0.524, 3.5, 52.8, 0.0605, "stranded"),
    ( 630,27.6, 8.0, 0.9, 45.3, 35, 0.524, 3.6, 56.8, 0.0469, "stranded"),
    ( 800,31.2, 8.0, 1.0, 49.1, 35, 0.524, 3.7, 61.3, 0.0367, "milliken_al"),
    (1000,35.2, 8.0, 1.1, 53.3, 35, 0.524, 3.9, 66.3, 0.0291, "milliken_al"),
]:
    CABLE_LIBRARY[f"AL{_r[0]}_18_30kV"] = _c(18, 30, *_r)


def list_cables(U_kV: Optional[int] = None) -> Dict[str, str]:
    return {k: v["name"] for k, v in CABLE_LIBRARY.items()
            if U_kV is None or v["U_kV"] == U_kV}


# ─────────────────────────────────────────────────────────────────────────────
#  Normalised 24-hour load profiles  (peak = 1.0)
#  μ = loss-load-factor = Σ(p/pmax)² / N  (IEC 60853-2 §2.1)
# ─────────────────────────────────────────────────────────────────────────────

def _mu(p: list) -> float:
    pmax = max(p)
    return sum((v/pmax)**2 for v in p) / len(p) if pmax > 0 else 1.0

LOAD_PROFILES: Dict[str, List[float]] = {
    # Flat (continuous)  μ=1.000
    "flat": [1.0] * 24,

    # ENTSO-E residential weekday, Central Europe
    "residential": [
        0.42,0.38,0.36,0.36,0.38,0.50,
        0.68,0.84,0.78,0.70,0.64,0.63,
        0.68,0.65,0.63,0.67,0.79,0.96,
        1.00,0.97,0.88,0.76,0.63,0.51],

    # ENTSO-E industrial weekday
    "industrial": [
        0.44,0.41,0.39,0.39,0.41,0.49,
        0.74,0.95,1.00,0.98,0.97,0.94,
        0.88,0.94,0.97,0.98,0.94,0.86,
        0.73,0.60,0.53,0.50,0.47,0.45],

    # Solar PV — PVGIS clear-sky, 52°N, June (worst thermal day)
    # IEC 60853-2: use peak-irradiance day as design case
    # μ ≈ 0.261 — DO NOT increase: this conservative μ is the reason
    # CYMCAP/ELEK give M ≈ 1.30–1.40 for solar (not 1.82)
    "solar_pv": [
        0.00,0.00,0.00,0.00,0.00,0.01,
        0.07,0.21,0.44,0.66,0.84,0.95,
        1.00,0.95,0.84,0.66,0.44,0.21,
        0.07,0.01,0.00,0.00,0.00,0.00],

    # Wind onshore — ERA5/Staffell&Pfenninger 90th-percentile production day
    # μ ≈ 0.430
    "wind_onshore": [
        0.55,0.58,0.62,0.67,0.72,0.76,
        0.79,0.80,0.79,0.76,0.70,0.64,
        0.58,0.54,0.52,0.55,0.62,0.70,
        0.80,0.90,0.98,1.00,0.88,0.72],

    # Wind offshore — ERA5 North Sea 90th pct.  μ ≈ 0.550
    "wind_offshore": [
        0.70,0.72,0.74,0.77,0.80,0.83,
        0.86,0.88,0.90,0.91,0.92,0.93,
        0.94,0.95,0.95,0.94,0.95,0.96,
        0.98,1.00,0.99,0.97,0.93,0.82],
}

PROFILE_LABELS = {
    "flat":          "Flat / Continuous  (μ=1.000)",
    "residential":   "Residential demand — ENTSO-E",
    "industrial":    "Industrial demand — ENTSO-E",
    "solar_pv":      "Solar PV — PVGIS clear-sky 52°N June",
    "wind_onshore":  "Wind onshore — ERA5 90th percentile",
    "wind_offshore": "Wind offshore — ERA5 North Sea 90th pct.",
}

PROFILE_MU = {k: round(_mu(v), 4) for k, v in LOAD_PROFILES.items()}
