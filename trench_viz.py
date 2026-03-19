"""
trench_viz.py  ─  CYMCAP-style cable trench cross-section (enhanced)
=====================================================================

Layout: gridspec two-panel
  ┌──────────────────────────────────┬────────────────────────┐
  │  TRENCH CROSS-SECTION            │  THERMAL RESULTS       │
  │  (equal-aspect, to scale)       │  Cable info + ratings   │
  └──────────────────────────────────┴────────────────────────┘
"""

import math
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
from matplotlib.lines import Line2D

matplotlib.use("Agg")

# ─────────────────────────────────────────────────────────────────────────────
#  Phase colour constants
# ─────────────────────────────────────────────────────────────────────────────
PH_DARK  = ["#ff4060", "#00e088", "#00a8ff"]   # A=red  B=green  C=blue
PH_LIGHT = ["#cc2040", "#00884c", "#0066cc"]

# ─────────────────────────────────────────────────────────────────────────────
#  Palettes — refined for modern look
# ─────────────────────────────────────────────────────────────────────────────
DARK = dict(
    fig="#060a10", ax_bg="#060a10",
    soil_nat="#081208", soil_dot="#142818",
    soil_tr="#0a1608",
    sand="#141408", sand_txt="#605828",
    tw_line="#1e2c18",
    gnd_fill="#143010", gnd_line="#28702c",
    grid="#0c1620",
    jkt_fc="#141c14", jkt_ec="#284820",
    scr_fc="#141828", scr_ec="#284880",
    ins_fc="#182418", ins_ec="#285830",
    con_fc="#c89010", con_ec="#8a6008",
    ann_bg="#007888", ann_fg="#d0f4ff",
    bbox_ec="#ff4060",
    dim="#3870a0", dim_txt="#5890c0",
    dry="#ff4060",
    pan_bg="#060e18", pan_ec="#142438",
    pan_hdr="#00a8aa", pan_txt="#7098b8",
    pan_val="#c8e8f8", pan_ok="#00d088",
    pan_warn="#ff8830",
    ax_txt="#506878",
)

LIGHT = dict(
    fig="#f4f6fb", ax_bg="#f4f6fb",
    soil_nat="#d8e0c8", soil_dot="#a0b080",
    soil_tr="#e4e8d4",
    sand="#e4dca0", sand_txt="#787028",
    tw_line="#607048",
    gnd_fill="#c0d498", gnd_line="#387028",
    grid="#ccd4e0",
    jkt_fc="#243820", jkt_ec="#386030",
    scr_fc="#406898", scr_ec="#284878",
    ins_fc="#60a060", ins_ec="#306838",
    con_fc="#c89010", con_ec="#8a6008",
    ann_bg="#0098b0", ann_fg="#001418",
    bbox_ec="#cc2040",
    dim="#283850", dim_txt="#283850",
    dry="#cc2040",
    pan_bg="#eaf0f8", pan_ec="#88a8c0",
    pan_hdr="#007890", pan_txt="#182c48",
    pan_val="#0a1830", pan_ok="#006028",
    pan_warn="#a04800",
    ax_txt="#385060",
)


# ─────────────────────────────────────────────────────────────────────────────
#  Drawing helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ann(ax, x, y, txt, P, fs=6.2, zo=30):
    ax.text(x, y, txt, ha="center", va="center",
            fontsize=fs, fontweight="bold",
            color=P["ann_fg"], fontfamily="monospace", zorder=zo,
            bbox=dict(boxstyle="round,pad=0.28",
                      facecolor=P["ann_bg"], edgecolor="none", alpha=0.92))


def _dim(ax, x1, y1, x2, y2, lbl, P, fs=5.4, lpos=0.5, off=(0, 0)):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="<->", color=P["dim"],
                                lw=0.85, mutation_scale=7.0), zorder=16)
    tx = x1 + lpos * (x2 - x1) + off[0]
    ty = y1 + lpos * (y2 - y1) + off[1]
    ax.text(tx, ty, lbl, ha="center", va="center",
            fontsize=fs, color=P["dim_txt"],
            fontfamily="monospace", fontweight="bold", zorder=17,
            bbox=dict(facecolor=P["ax_bg"], edgecolor="none", pad=0.8))


def _tick(ax, x, ya, yb, P, lw=0.75):
    ax.plot([x, x], [ya, yb], color=P["dim"], lw=lw, zorder=15)


def _hatch(ax, xlo, xhi, ylo, yhi, col, step=0.065, alpha=0.45):
    if xhi <= xlo or yhi <= ylo:
        return
    xs = np.arange(xlo, xhi + step, step)
    ys = np.arange(ylo, yhi + step, step)
    n = len(xs) * len(ys)
    if n > 8000:
        step = step * math.ceil(math.sqrt(n / 8000))
        xs = np.arange(xlo, xhi + step, step)
        ys = np.arange(ylo, yhi + step, step)
    Xs, Ys = np.meshgrid(xs, ys)
    ax.scatter(Xs.ravel(), Ys.ravel(), s=0.4, c=col,
               alpha=alpha, zorder=2, linewidths=0)


def _cable(ax, cx, cy, dc, di, dsc, De, ph_i, P, dark, cond="Al"):
    """Draw one single-core cable cross-section."""
    ph_col = (PH_DARK if dark else PH_LIGHT)[ph_i % 3]

    # Jacket
    ax.add_patch(Circle((cx, cy), De / 2,
                         fc=P["jkt_fc"], ec=P["jkt_ec"], lw=1.2, zorder=10))
    # Screen
    ax.add_patch(Circle((cx, cy), dsc / 2,
                         fc=P["scr_fc"], ec=P["scr_ec"], lw=0.6, zorder=11))
    # Insulation
    ax.add_patch(Circle((cx, cy), di / 2,
                         fc=P["ins_fc"], ec=P["ins_ec"], lw=0.6, zorder=12))
    # Conductor
    ax.add_patch(Circle((cx, cy), dc / 2,
                         fc=P["con_fc"], ec=P["con_ec"], lw=0.6, zorder=13))
    # Phase ring
    ax.add_patch(Circle((cx, cy), De / 2,
                         fc="none", ec=ph_col, lw=2.8, zorder=9, alpha=0.92))
    # Phase label
    lfs = max(4.0, min(8.5, dc * 120))
    ax.text(cx, cy, "ABC"[ph_i % 3],
            ha="center", va="center",
            fontsize=lfs, fontweight="bold", color="white",
            fontfamily="sans-serif", zorder=16,
            path_effects=[pe.withStroke(linewidth=1.5, foreground="black")])
    # Bounding box
    pad = De * 0.08
    ax.add_patch(Rectangle((cx - De / 2 - pad, cy - De / 2 - pad),
                             De + 2 * pad, De + 2 * pad,
                             fc="none", ec=P["bbox_ec"], lw=1.1, zorder=8,
                             alpha=0.7, ls=(0, (4, 2))))


# ─────────────────────────────────────────────────────────────────────────────
#  Info panel
# ─────────────────────────────────────────────────────────────────────────────

def _info_panel(ax, engine, result, P, dark):
    ax.set_facecolor(P["pan_bg"])
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_edgecolor(P["pan_ec"]); sp.set_linewidth(1.0)

    cd = engine.cd
    inst = engine.inst
    ph = PH_DARK if dark else PH_LIGHT
    res = result
    De = engine.De
    s_eff = engine.s_eff

    t = ax.transAxes
    x0, dx = 0.06, 0.55

    def _row(y, key, val, color=None, bold=False):
        col_k = P["pan_txt"]
        col_v = color if color else P["pan_val"]
        fw = "bold" if bold else "normal"
        ax.text(x0, y, key, transform=t, ha="left", va="center",
                fontsize=6.3, color=col_k, fontfamily="monospace")
        ax.text(x0 + dx, y, val, transform=t, ha="left", va="center",
                fontsize=6.3, color=col_v, fontfamily="monospace", fontweight=fw)

    def _hdr(y, txt):
        ax.text(x0, y, txt, transform=t, ha="left", va="center",
                fontsize=6.6, color=P["pan_hdr"],
                fontfamily="monospace", fontweight="bold")

    def _div(y):
        ax.plot([0.04, 0.96], [y, y], color=P["pan_ec"], lw=0.7,
                transform=t, zorder=4)

    y = 0.97

    # Cable info
    _hdr(y, "▌ CABLE"); y -= 0.045
    _row(y, "Type", cd["name"]); y -= 0.038
    _row(y, "Uo/U", f"{cd['Uo_kV']}/{cd['U_kV']} kV"); y -= 0.038
    _row(y, "Cross-section", f"{cd['cond_cs']} mm²  {cd['cond_mat']}"); y -= 0.038
    _row(y, "Formation",
         f"{inst.formation.title()}  s = {s_eff*1000:.0f} mm"); y -= 0.038
    _row(y, "Depth", f"{inst.depth:.2f} m"); y -= 0.038
    if inst.num_circuits > 1:
        cct_sep = getattr(inst, 'circuit_separation', De)
        _row(y, "Cct gap", f"{cct_sep*1000:.0f} mm  ({inst.num_circuits} circuits)"); y -= 0.038
    _div(y); y -= 0.030

    # Temperature chain
    _hdr(y, "▌ TEMPERATURE CHAIN"); y -= 0.040
    rows_T = [
        ("θ ambient", f"{engine.soil.T_amb:.1f} °C",
         "Undisturbed soil", P["pan_txt"]),
        ("θ surface", f"{res.theta_surface:.1f} °C",
         "Jacket / soil interface", P["pan_val"]),
        ("θ screen", f"{res.theta_screen:.1f} °C",
         "Cu wire screen", P["pan_val"]),
        ("θ conductor", f"{res.theta_cond:.1f} °C",
         "Al conductor [90°C max]",
         P["pan_warn"] if res.theta_cond > 88 else P["pan_val"]),
    ]
    for lbl, val, note, col in rows_T:
        ax.text(x0, y, lbl, transform=t, ha="left", va="center",
                fontsize=6.0, color=P["pan_txt"], fontfamily="monospace")
        ax.text(x0 + dx, y, val, transform=t, ha="left", va="center",
                fontsize=6.3, color=col, fontfamily="monospace", fontweight="bold")
        ax.text(x0 + dx + 0.24, y, note, transform=t, ha="left", va="center",
                fontsize=5.0, color=P["pan_txt"], fontfamily="monospace", alpha=0.75)
        y -= 0.038
    _div(y); y -= 0.030

    # Rating
    _hdr(y, "▌ AMPACITY RATING"); y -= 0.040
    _row(y, "Continuous", f"{res.I_cont:.0f} A"); y -= 0.038
    _row(y, "Emergency 8h", f"{res.I_emerg:.0f} A"); y -= 0.038
    if res.M_cyclic > 1.001:
        _row(y, f"Cyclic (M={res.M_cyclic:.3f})",
             f"{res.I_cyclic:.0f} A  [μ={res.mu:.3f}]"); y -= 0.038
    _div(y); y -= 0.030

    # Thermal resistances
    _hdr(y, "▌ THERMAL RESISTANCES [K·m/W]"); y -= 0.040
    T4tot = res.T4_self + res.T4_mutual + res.T4_dry + res.T4_duct + getattr(res, 'T4_trench', 0.0)
    _row(y, "T1  XLPE insulation", f"{res.T1:.4f}"); y -= 0.036
    _row(y, "T2  Cu screen", f"{res.T2:.5f}  (≈0)"); y -= 0.036
    _row(y, "T3  PE jacket", f"{res.T3:.4f}"); y -= 0.036
    _row(y, "T4  self (soil)", f"{res.T4_self:.4f}"); y -= 0.036
    if res.T4_mutual > 0.001:
        _row(y, "T4  mutual", f"{res.T4_mutual:.4f}"); y -= 0.036
    if res.T4_dry > 0.001:
        _row(y, "T4  dry zone", f"{res.T4_dry:.4f}"); y -= 0.036
    T4tr = getattr(res, 'T4_trench', 0.0)
    if abs(T4tr) > 0.001:
        lbl = "T4  backfill (+)" if T4tr > 0 else "T4  backfill (-)"
        _row(y, lbl, f"{T4tr:.4f}"); y -= 0.036
    _row(y, "T4  total", f"{T4tot:.4f}",
         color=P["pan_warn"] if res.dry_zone else P["pan_val"], bold=True)
    y -= 0.036

    # Electrical
    _hdr(y, "▌ ELECTRICAL"); y -= 0.040
    _row(y, "Rdc 20°C", f"{res.Rdc*1e3:.4f} Ω/km"); y -= 0.036
    _row(y, "Rac @θ", f"{res.Rac*1e3:.4f} Ω/km  (λ1={res.lambda1:.4f})"); y -= 0.036
    _row(y, "X", f"{res.X_ohm_km:.4f} Ω/km"); y -= 0.036
    _row(y, "C", f"{res.C_nF_km:.1f} nF/km"); y -= 0.036
    if res.dU_pct > 0:
        _row(y, "Voltage drop", f"{res.dU_pct:.2f}%  ({res.dU_V:.0f} V)"); y -= 0.036
    _div(y); y -= 0.030

    # Legend: cable layers
    _hdr(y, "▌ LAYERS"); y -= 0.040
    layers = [
        (P["jkt_fc"], P["jkt_ec"], "PE outer jacket"),
        (P["scr_fc"], P["scr_ec"], "Cu wire screen"),
        (P["ins_fc"], P["ins_ec"], "XLPE insulation"),
        (P["con_fc"], P["con_ec"], "Al conductor"),
    ]
    for fc, ec, lbl in layers:
        rect = matplotlib.patches.FancyBboxPatch(
            (x0, y - 0.012), 0.055, 0.024, transform=t,
            boxstyle="round,pad=0.002",
            fc=fc, ec=ec, lw=0.8, zorder=5)
        ax.add_patch(rect)
        ax.text(x0 + 0.075, y, lbl, transform=t, ha="left", va="center",
                fontsize=5.8, color=P["pan_txt"], fontfamily="monospace")
        y -= 0.034

    _div(y); y -= 0.028

    # Legend: phases
    _hdr(y, "▌ PHASES"); y -= 0.040
    for i, lbl in enumerate(["Phase A", "Phase B", "Phase C"]):
        ax.add_patch(matplotlib.patches.FancyBboxPatch(
            (x0, y - 0.012), 0.055, 0.024, transform=t,
            boxstyle="round,pad=0.002",
            fc=ph[i], ec=ph[i], lw=0.5, zorder=5))
        ax.text(x0 + 0.075, y, lbl, transform=t, ha="left", va="center",
                fontsize=5.8, color=P["pan_txt"], fontfamily="monospace")
        y -= 0.034

    if res.dry_zone:
        _div(y); y -= 0.025
        _row(y, "⚠ Dry zone", f"r = {res.rx_m*100:.1f} cm",
             color=P["pan_warn"], bold=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Main figure
# ─────────────────────────────────────────────────────────────────────────────

def draw_trench(engine, result=None,
                dark: bool = True,
                figsize=(12.0, 9.2),
                show_labels: bool = True) -> plt.Figure:
    P = DARK if dark else LIGHT
    ph = PH_DARK if dark else PH_LIGHT
    cd = engine.cd
    inst = engine.inst
    s = engine.s_eff
    L = inst.depth
    De = engine.De
    dc = engine.dc
    di = engine.di
    dsc = engine.dsc
    tw = inst.trench_width
    nc = inst.num_circuits
    cct_sep = getattr(inst, 'circuit_separation', De)

    pos = engine.cable_positions()
    all_x = [p[0] for p in pos]
    all_y = [p[1] for p in pos]
    y_deep = min(all_y)
    y_shallow = max(all_y)

    # Figure & gridspec
    fig = plt.figure(figsize=figsize, facecolor=P["fig"])
    gs = gridspec.GridSpec(1, 2, width_ratios=[1.55, 1.0],
                            left=0.04, right=0.98,
                            bottom=0.05, top=0.93, wspace=0.04)
    ax = fig.add_subplot(gs[0, 0])
    axp = fig.add_subplot(gs[0, 1])

    ax.set_facecolor(P["ax_bg"])
    ax.set_aspect("equal")

    # Axis limits
    row_A = y_deep - De / 2 - De * 1.05
    row_B = row_A - De * 1.85
    row_C = row_B - De * 1.55
    y_bot = row_C - De * 1.30

    x_ext = max(tw / 2 + De * 2.5,
                max(abs(x) for x in all_x) + De + 0.40)
    ax.set_xlim(-x_ext, x_ext + 0.50)
    ax.set_ylim(y_bot, 0.48)

    # Soil
    ax.fill_between([-x_ext * 4, x_ext * 4], y_bot * 2, 0,
                    color=P["soil_nat"], zorder=0)
    _hatch(ax, -x_ext * 1.1, -tw / 2, y_bot * 1.05, 0, P["soil_dot"])
    _hatch(ax, tw / 2, x_ext * 1.1, y_bot * 1.05, 0, P["soil_dot"])
    ax.fill_between([-tw / 2, tw / 2], y_bot * 2, 0,
                    color=P["soil_tr"], zorder=1)

    # Sand bedding
    y_st = y_shallow + De / 2 + 0.10
    y_sb = y_deep - De / 2 - 0.10
    ax.fill_between([-tw / 2 * 0.97, tw / 2 * 0.97], y_sb, y_st,
                    color=P["sand"], alpha=0.88, zorder=2)
    ax.text(0, (y_sb + y_st) * 0.5, "FINE SAND BEDDING",
            ha="center", va="center", fontsize=4.6,
            color=P["sand_txt"], fontfamily="monospace", alpha=0.80, zorder=3)

    # Trench walls
    for xw in [-tw / 2, tw / 2]:
        ax.plot([xw, xw], [y_bot * 1.5, 0.0],
                color=P["tw_line"], lw=2.2, zorder=4)

    # Ground surface
    ax.fill_between([-x_ext * 4, x_ext * 4], 0, 0.48,
                    color=P["gnd_fill"], alpha=0.28, zorder=5)
    ax.axhline(0, color=P["gnd_line"], lw=2.8, zorder=6)
    ax.text(-x_ext + 0.05, 0.26, "GROUND LEVEL",
            fontsize=5.4, color=P["gnd_line"],
            fontfamily="monospace", fontweight="bold", alpha=0.90, zorder=7)

    # Subtle grid
    for gx in np.arange(-x_ext, x_ext + 0.01, 0.20):
        ax.axvline(gx, color=P["grid"], lw=0.35, alpha=0.40, zorder=1)

    # Dry-zone circles
    if result and getattr(result, "dry_zone", False) and result.rx_m > De / 2:
        dry_fc = "#200808" if dark else "#fff0ee"
        for px, py in pos:
            ax.add_patch(Circle((px, py), result.rx_m,
                                 fc=dry_fc, ec=P["dry"],
                                 ls=(0, (5, 3)), lw=1.5, alpha=0.25, zorder=3))
            ax.add_patch(Circle((px, py), result.rx_m,
                                 fc="none", ec=P["dry"],
                                 ls=(0, (5, 3)), lw=1.5, alpha=0.80, zorder=9))

    # Cable cross-sections
    for i, (px, py) in enumerate(pos):
        _cable(ax, px, py, dc, di, dsc, De,
               ph_i=i % 3, P=P, dark=dark, cond=cd.get("cond_mat", "Al"))

    # Per-circuit annotation boxes
    if show_labels and result:
        for ci in range(nc):
            grp = pos[ci * 3: ci * 3 + 3]
            gx_c = (max(p[0] for p in grp) + min(p[0] for p in grp)) / 2
            gy_b = min(p[1] for p in grp)
            ax.plot([gx_c, gx_c], [gy_b - De / 2, row_A + De * 0.45],
                    color=P["dim"], lw=0.8, zorder=14)
            if getattr(result, "M_cyclic", 1.0) > 1.001:
                lbl = f"{result.I_cont:.0f}A  /  {result.I_cyclic:.0f}A cyc"
            else:
                lbl = f"{result.I_cont:.0f} A  @  {result.theta_cond:.0f}°C"
            _ann(ax, gx_c, row_A, lbl, P, fs=5.8)

    # Phase spacing dimensions
    if inst.formation == "trefoil":
        p0, p1 = pos[0], pos[1]
    else:
        p0, p1 = pos[0], pos[1]

    _tick(ax, p0[0], min(p0[1], p1[1]) - De / 2, row_B, P)
    _tick(ax, p1[0], min(p0[1], p1[1]) - De / 2, row_B, P)
    _dim(ax, p0[0], row_B, p1[0], row_B,
         f" s={s*1000:.0f}mm ", P, fs=5.6)

    # Circuit gap
    if nc > 1 and len(pos) >= 6:
        r_g1 = max(p[0] for p in pos[:3]) + De / 2
        l_g2 = min(p[0] for p in pos[3:]) - De / 2
        gap_cc = l_g2 - r_g1
        _tick(ax, r_g1, y_deep - De / 2, row_B, P)
        _tick(ax, l_g2, y_deep - De / 2, row_B, P)
        _dim(ax, r_g1, row_B, l_g2, row_B,
             f" {gap_cc*1000:.0f}mm gap ", P, fs=5.6)
        p3, p4 = pos[3], pos[4]
        _tick(ax, p3[0], min(p3[1], p4[1]) - De / 2, row_B, P)
        _tick(ax, p4[0], min(p3[1], p4[1]) - De / 2, row_B, P)
        _dim(ax, p3[0], row_B, p4[0], row_B,
             f" s={s*1000:.0f}mm ", P, fs=5.6)

    # Trench width
    _tick(ax, -tw / 2, row_C + De * 0.22, row_C, P)
    _tick(ax, tw / 2, row_C + De * 0.22, row_C, P)
    _dim(ax, -tw / 2, row_C, tw / 2, row_C, f" W = {tw:.2f} m ", P, fs=5.8)

    # Burial depth
    x_da = x_ext + 0.22
    _tick(ax, x_da - 0.06, 0.0, 0.15, P)
    _tick(ax, x_da - 0.06, y_deep, y_deep - De * 0.4, P)
    _dim(ax, x_da, y_deep, x_da, 0.0,
         f" L={L:.2f}m ", P, fs=5.8, off=(0.11, 0))

    # Depth to top cable
    if inst.formation == "trefoil" and len(pos) >= 3:
        y_tc = pos[2][1]
        x_dt = x_da + 0.28
        _tick(ax, x_dt - 0.06, 0.0, 0.15, P)
        _tick(ax, x_dt - 0.06, y_tc, y_tc - De * 0.4, P)
        _dim(ax, x_dt, y_tc, x_dt, 0.0,
             f" L_top={(-y_tc):.2f}m ", P, fs=5.2, off=(0.12, 0))

    # Cable OD reference
    x_od = -x_ext + 0.04
    _tick(ax, x_od + 0.05, y_deep - De / 2, y_deep - De / 2 - De * 0.35, P)
    _tick(ax, x_od + 0.05, y_deep + De / 2, y_deep + De / 2 + De * 0.35, P)
    _dim(ax, x_od, y_deep - De / 2, x_od, y_deep + De / 2,
         f" Ø{De*1000:.0f}mm ", P, fs=5.2, off=(-0.08, 0))

    # Axes formatting
    ax.set_xlabel("Horizontal offset  (m)", fontsize=6.5,
                  color=P["ax_txt"], labelpad=3)
    ax.set_ylabel("Depth  (m)", fontsize=6.5,
                  color=P["ax_txt"], labelpad=3)

    ytks = [round(y, 1) for y in np.arange(round(y_bot, 1), 0.5, 0.2)
            if y_bot <= y <= 0.45]
    ax.set_yticks(ytks)
    ax.set_yticklabels([f"{abs(y):.1f}" for y in ytks],
                        fontsize=5.0, color=P["ax_txt"])
    ax.xaxis.set_tick_params(labelsize=5.0, colors=P["ax_txt"])
    ax.tick_params(colors=P["ax_txt"], length=2.5, width=0.6)
    for sp in ax.spines.values():
        sp.set_edgecolor(P["grid"]); sp.set_linewidth(0.8)

    # Info panel
    if result:
        _info_panel(axp, engine, result, P, dark)
    else:
        axp.set_facecolor(P["pan_bg"])
        axp.set_xticks([]); axp.set_yticks([])
        for sp in axp.spines.values():
            sp.set_edgecolor(P["pan_ec"])
        axp.text(0.5, 0.5, "Run calculation\nto see results",
                 transform=axp.transAxes, ha="center", va="center",
                 fontsize=7, color=P["pan_txt"], fontfamily="monospace")

    # Title
    nc_pfx = f"{nc}×" if nc > 1 else ""
    cct_str = (f"  ·  cct sep = {cct_sep*1000:.0f} mm" if nc > 1 else "")
    fig.suptitle(
        f"{nc_pfx} {cd['name']}  ·  {inst.formation.title()}  ·  "
        f"s = {s*1000:.0f} mm  ·  depth = {L:.2f} m  ·  W = {tw:.2f} m{cct_str}",
        fontsize=7.2, color=P["ax_txt"], fontfamily="monospace", y=0.985)

    return fig


# ─────────────────────────────────────────────────────────────────────────────
#  Load profile chart
# ─────────────────────────────────────────────────────────────────────────────

def draw_load_profile(profile: list, mu: float,
                      label: str = "",
                      dark: bool = True,
                      figsize=(7.4, 2.6)) -> plt.Figure:
    P = DARK if dark else LIGHT
    ACC = "#00d4aa" if dark else "#0088aa"
    GRN = "#00e088" if dark else "#00884c"
    ORG = "#ff8830" if dark else "#cc6600"
    TX2 = P["ax_txt"]
    BORD = P["grid"]

    fig, ax = plt.subplots(figsize=figsize, facecolor=P["fig"])
    ax.set_facecolor(P["ax_bg"])
    pmax = max(profile) if max(profile) > 0 else 1.0
    norm = [v / pmax for v in profile]
    h_ext = list(range(24)) + [24]
    n_ext = norm + [norm[-1]]

    ax.fill_between(h_ext, 0, n_ext, color=ACC, alpha=0.15, step="post")
    ax.step(h_ext, n_ext, color=ACC, lw=1.8, where="post",
            label="Load (p.u.)", zorder=5)
    ax.axhline(mu, color=GRN, lw=1.2, ls="--",
               label=f"μ = {mu:.4f}", zorder=6)
    peak_h = int(np.argmax(profile))
    ax.axvline(peak_h + 0.5, color=ORG, lw=0.9, ls=":",
               alpha=0.75, label=f"Peak @ {peak_h:02d}:00", zorder=4)
    for hh, v in enumerate(norm):
        if v < mu:
            ax.axvspan(hh, hh + 1, color=BORD, alpha=0.25, zorder=1)

    ax.set_xlim(0, 24); ax.set_ylim(0, 1.12)
    ax.set_xticks(range(0, 25, 3))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 25, 3)],
                        fontsize=6.0, color=TX2)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.0", "0.2", "0.4", "0.6", "0.8", "1.0"],
                        fontsize=6.0, color=TX2)
    ax.set_xlabel("Hour of day", fontsize=6.5, color=TX2)
    ax.set_ylabel("Normalised load", fontsize=6.5, color=TX2)
    ax.tick_params(colors=TX2, length=2.5, width=0.6)
    for sp in ax.spines.values():
        sp.set_edgecolor(BORD); sp.set_linewidth(0.7)
    ax.legend(fontsize=6.0, framealpha=0.90, facecolor=P["pan_bg"],
              edgecolor=BORD, labelcolor=P["pan_txt"], loc="upper right",
              borderpad=0.5, handlelength=1.5)
    if label:
        ax.set_title(label, fontsize=6.5, color=P["ax_txt"],
                     fontfamily="monospace", pad=4)
    fig.tight_layout(pad=0.5)
    return fig
