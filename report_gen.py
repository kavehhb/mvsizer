"""
report_gen.py — PDF Engineering Report  (ReportLab)
"""
import io, math, datetime
from typing import Optional

try:
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, Image as RLImage, KeepTogether
    )
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    RL = True
except ImportError:
    RL = False

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_pdf(engine, res, ar, load, profile_name,
                 proj="MV Cable Study", eng_name="", ref="") -> bytes:
    if not RL:
        return _fallback(engine, res, ar)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
        title=f"MV Cable Report — {proj}")

    NAVY  = colors.HexColor("#0a2040")
    BLUE  = colors.HexColor("#1a4080")
    LBLUE = colors.HexColor("#d8e8f4")
    LGREY = colors.HexColor("#f2f5f8")
    WHITE = colors.white
    GREEN = colors.HexColor("#1a6030")
    RED   = colors.HexColor("#b01818")
    ORNG  = colors.HexColor("#b04010")

    S = getSampleStyleSheet()
    def sty(name, **kw):
        return ParagraphStyle(name, parent=S["Normal"], **kw)

    sTITLE = sty("tit", fontName="Helvetica-Bold", fontSize=18,
                 textColor=NAVY, spaceAfter=3*mm, leading=22)
    sSUB   = sty("sub", fontName="Helvetica", fontSize=10,
                 textColor=colors.HexColor("#3050a0"), spaceAfter=4*mm)
    sH1    = sty("h1",  fontName="Helvetica-Bold", fontSize=11,
                 textColor=NAVY, spaceBefore=5*mm, spaceAfter=2*mm,
                 backColor=LBLUE, borderPad=3)
    sH2    = sty("h2",  fontName="Helvetica-Bold", fontSize=9,
                 textColor=BLUE, spaceBefore=2*mm, spaceAfter=1*mm)
    sBODY  = sty("bod", fontName="Helvetica", fontSize=8.5,
                 textColor=colors.HexColor("#202030"), spaceAfter=1*mm, leading=12)
    sSM    = sty("sm",  fontName="Helvetica", fontSize=7,
                 textColor=colors.HexColor("#505060"), spaceAfter=1*mm, leading=10)
    sWARN  = sty("wn",  fontName="Helvetica-Bold", fontSize=8.5,
                 textColor=colors.HexColor("#903010"), spaceAfter=1*mm)
    sPASS  = sty("ps",  fontName="Helvetica-Bold", fontSize=8.5,
                 textColor=GREEN, spaceAfter=1*mm)

    def base_ts(data, hdr=True):
        ts = [
            ("FONTNAME",  (0,0),(-1,-1), "Helvetica"),
            ("FONTSIZE",  (0,0),(-1,-1), 8),
            ("GRID",      (0,0),(-1,-1), 0.3, colors.HexColor("#c8d4e0")),
            ("ROWBACKGROUNDS",(0,0),(-1,-1), [LGREY, WHITE]),
            ("VALIGN",    (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1), 2.5),
            ("BOTTOMPADDING",(0,0),(-1,-1), 2.5),
            ("LEFTPADDING",(0,0),(-1,-1), 4),
        ]
        if hdr:
            ts += [("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                   ("BACKGROUND",(0,0),(-1,0),BLUE),
                   ("TEXTCOLOR",(0,0),(-1,0),WHITE)]
        return TableStyle(ts)

    story = []

    # ── Cover ─────────────────────────────────────────────────────────────────
    story += [
        Spacer(1,8*mm),
        HRFlowable("100%", thickness=3, color=BLUE),
        Spacer(1,3*mm),
        Paragraph("MV CABLE THERMAL RATING REPORT", sTITLE),
        Paragraph("IEC 60287 · IEC 60853 · VDE 0276-1000  |  Prysmian NA2XS(F)2Y", sSUB),
        HRFlowable("100%", thickness=0.8, color=LBLUE),
        Spacer(1,3*mm),
    ]
    meta = [["Project", proj], ["Engineer", eng_name or "—"],
            ["Reference", ref or "—"],
            ["Cable", engine.cd["name"]],
            ["Calculated", datetime.datetime.now().strftime("%Y-%m-%d  %H:%M")]]
    mt = Table(meta, colWidths=[38*mm,132*mm])
    mt.setStyle(base_ts(meta, hdr=False))
    story.append(mt)
    story.append(Spacer(1,4*mm))

    ok = ar.all_pass if ar else True
    col = GREEN if ok else RED
    txt = "✔  ALL DESIGN CHECKS PASSED" if ok else "✘  ONE OR MORE CHECKS FAILED — SEE SECTION 4"
    story.append(Table([[txt]], colWidths=[170*mm],
        style=TableStyle([("BACKGROUND",(0,0),(-1,-1),col),
                          ("TEXTCOLOR",(0,0),(-1,-1),WHITE),
                          ("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),
                          ("FONTSIZE",(0,0),(-1,-1),11),
                          ("ALIGN",(0,0),(-1,-1),"CENTER"),
                          ("TOPPADDING",(0,0),(-1,-1),5),
                          ("BOTTOMPADDING",(0,0),(-1,-1),5)])))
    story.append(Spacer(1,6*mm))

    # ── 1. Cable & Installation ────────────────────────────────────────────────
    story.append(Paragraph("1.  Cable & Installation Parameters", sH1))
    cd = engine.cd
    inst = engine.inst
    soil = engine.soil

    cable_rows = [
        ["Parameter","Value","Source"],
        ["Designation", cd["name"], "Prysmian 2023"],
        ["Conductor", f"{cd['cond_mat']} {cd['cond_cs']} mm² ({cd['strand']})", "IEC 60228"],
        ["Conductor diameter", f"{cd['dc_mm']:.1f} mm", "—"],
        ["DC resistance (20°C)", f"{cd['Rdc20']:.4f} Ω/km", "IEC 60228 T1"],
        ["Insulation", f"{cd['ins_mat']}  {cd['t_ins']:.1f} mm", "IEC 60502-2 T3"],
        ["Screen", f"{cd['A_screen']} mm² Cu,  R={cd['R_screen']:.3f} Ω/km", "Prysmian"],
        ["Screen bonding", engine.bonding.replace("_"," ").title(), "IEC 60287-1-1 §2.3"],
        ["Cable OD", f"{cd['OD_mm']:.1f} mm", "—"],
    ]
    inst_rows = [
        ["Parameter","Value","Reference"],
        ["Burial depth", f"{inst.depth:.2f} m", "IEC 60287-2-1 §2.2"],
        ["Formation", inst.formation.title(), "—"],
        ["Phase spacing (s)", f"{inst.phase_spacing*1000:.0f} mm", "—"],
        ["No. circuits", str(inst.num_circuits), "—"],
        ["In duct", "Yes" if inst.in_duct else "No", "IEC 60287-2-1 §2.2.2"],
        ["Ambient temperature", f"{soil.T_amb:.1f} °C", "IEC 60287"],
        ["Soil ρ (wet/dry)", f"{soil.rho_wet:.2f} / {soil.rho_dry:.2f} K·m/W", "IEC 60287-2-1"],
        ["Dry-out threshold", f"{soil.T_crit:.0f} °C", "IEC 60287-2-1 §2.2.3"],
        ["System voltage", f"{cd['U_kV']:.0f} kV  (U0={cd['Uo_kV']:.0f} kV)", "—"],
    ]
    for rows, cap in [(cable_rows,"Cable parameters"),(inst_rows,"Installation parameters")]:
        story.append(Paragraph(cap, sH2))
        t = Table(rows, colWidths=[70*mm,65*mm,35*mm])
        t.setStyle(base_ts(rows))
        story.append(t); story.append(Spacer(1,2*mm))

    # ── 2. Thermal resistance circuit ──────────────────────────────────────────
    story.append(Paragraph("2.  Thermal Resistance Circuit  [IEC 60287-2-1]", sH1))
    tr = [["Component","Symbol","Value (K·m/W)","Clause"],
          ["XLPE Insulation","T₁",f"{res.T1:.5f}","§2.1 eq.(1)"],
          ["Metallic screen","T₂",f"{res.T2:.5f}","§2.1 eq.(2)"],
          ["PE outer jacket","T₃",f"{res.T3:.5f}","§2.1 eq.(3)"],
          ["Soil self-heating"+(", dry zone" if res.dry_zone else ""),
           "T₄s",f"{res.T4_self:.5f}","§2.2.1 eq.(6)"],
          ["Dry-zone component","T₄d",f"{res.T4_dry:.5f}","§2.2.3 eq.(7)"],
          ["Mutual heating","T₄m",f"{res.T4_mutual:.5f}","§2.2.2"],
          ["Duct","T₄duct",f"{res.T4_duct:.5f}","§2.2.2 eq.(19)"],
          ["TOTAL soil","T₄",f"{res.T4_soil:.5f}","—"]]
    tt = Table(tr, colWidths=[65*mm,20*mm,45*mm,40*mm])
    tt.setStyle(base_ts(tr))
    story.append(tt); story.append(Spacer(1,2*mm))

    # ── 3. Rating results ───────────────────────────────────────────────────────
    story.append(Paragraph("3.  Rating Results  [IEC 60287-1-1 eq.(1) / IEC 60853-2]", sH1))
    rr = [["Parameter","Value","Standard"],
          ["Skin effect Ys", f"{res.Ys:.5f}", "IEC 60287-1-1 §2.1.2"],
          ["Proximity effect Yp", f"{res.Yp:.5f}", "IEC 60287-1-1 §2.1.3"],
          ["AC resistance (at θ_cond)", f"{res.Rac*1e3:.4f} mΩ/m", "IEC 60287-1-1 §2.1"],
          ["Conductor I²R losses", f"{res.W_I2R:.3f} W/m", "—"],
          ["Dielectric losses Wd", f"{res.W_d*1e3:.3f} mW/m", "IEC 60287-1-1 §2.2"],
          ["Screen losses", f"{res.W_s:.4f} W/m", "IEC 60287-1-1 §2.3"],
          ["λ₁ (circ + eddy)", f"{res.lambda1:.5f}  ({res.lambda1_circ:.5f}+{res.lambda1_eddy:.5f})", "§2.3"],
          ["Conductor temperature", f"{res.theta_cond:.2f} °C", "—"],
          ["Cable surface temp.", f"{res.theta_surface:.2f} °C", "—"],
          ["Dry-zone active", "YES ⚠" if res.dry_zone else "No", "IEC 60287-2-1 §2.2.3"],
          ["Continuous ampacity", f"{res.I_cont:.1f} A", "IEC 60287-1-1 eq.(1)"],
          ["Emergency ampacity (8h)", f"{res.I_emerg:.1f} A", "IEC 60853-2 §4"],
          ["Loss load factor μ", f"{res.mu:.4f}", "IEC 60853-2 §2.1"],
          ["Cyclic factor M", f"{res.M_cyclic:.4f}", "IEC 60853-2 §3.3"],
          ["Cyclic ampacity", f"{res.I_cyclic:.1f} A", "IEC 60853-2"],
          ["Reactance X₁", f"{res.X_ohm_km:.4f} Ω/km", "IEC 60287-1-1 §3.2"],
          ["Capacitance C", f"{res.C_nF_km:.2f} nF/km", "IEC 60287-1-1 eq.(11)"],
          ["Charging current Ic", f"{res.Ic_A:.2f} A/km", "—"],
          ["Voltage drop (at Ic)", f"{res.dU_pct:.3f}%  ({res.dU_V:.0f} V)", "Temp-corrected R"]]
    rt = Table(rr, colWidths=[80*mm,55*mm,35*mm])
    rt.setStyle(base_ts(rr))
    story.append(rt)
    for w in res.warnings:
        story.append(Paragraph(f"⚠  {w}", sWARN))
    story.append(Spacer(1,2*mm))

    # ── 4. Load analysis ────────────────────────────────────────────────────────
    if ar:
        story.append(Paragraph("4.  Load Analysis & Design Checks", sH1))
        la = [["Load Parameter","Value"],
              ["Apparent power S", f"{load.S_MVA:.3f} MVA"],
              ["Active power P", f"{ar.P_MW:.3f} MW"],
              ["Reactive power Q", f"{ar.Q_Mvar:.3f} Mvar"],
              ["Power factor", f"{load.pf:.3f}"],
              ["Load current", f"{ar.I_load:.1f} A"],
              ["Cable length", f"{load.L_km:.2f} km"],
              ["Utilisation (continuous)", f"{ar.util_cont_pct:.1f}%"],
              ["Conductor temp. at load", f"{ar.theta_at_load:.2f} °C"],
              ["Voltage drop at load", f"{ar.dU_load_pct:.3f}%  ({ar.dU_load_V:.0f} V)"],
              ["Charging current", f"{ar.Ic_A:.2f} A"],
              ["SC conductor limit", f"{ar.Isc_cond_kA:.2f} kA  ({load.t_fault:.2f}s)"],
              ["SC screen limit", f"{ar.Isc_screen_kA:.2f} kA"]]
        lt = Table(la, colWidths=[90*mm,80*mm])
        lt.setStyle(base_ts(la))
        story.append(lt); story.append(Spacer(1,3*mm))

        story.append(Paragraph("Check Summary:", sH2))
        ch = [["Check","Result","Measured","Limit","Margin"]]
        for c in ar.checks:
            ch.append([c.name, "PASS ✔" if c.passed else "FAIL ✘",
                        c.measured, c.limit, f"{c.margin_pct:+.1f}%"])
        ct = Table(ch, colWidths=[55*mm,22*mm,42*mm,33*mm,18*mm])
        cs_base = base_ts(ch)
        for i, c in enumerate(ar.checks, 1):
            col = colors.HexColor("#d0f0d8") if c.passed else colors.HexColor("#f8d0d0")
            cs_base.add("BACKGROUND",(0,i),(-1,i), col)
        ct.setStyle(cs_base)
        story.append(ct); story.append(Spacer(1,2*mm))

        # Recommendations
        if ar.recs:
            story.append(Paragraph("5.  Recommendations", sH1))
            icons = {"critical":"🔴","warning":"🟠","info":"🔵"}
            for rec in ar.recs:
                story.append(Paragraph(
                    f"{icons.get(rec.level,'•')}  {rec.title}", sH2))
                story.append(Paragraph(rec.body, sBODY))
                if rec.action:
                    story.append(Paragraph(f"→ Action: {rec.action}", sBODY))
                story.append(Spacer(1,1*mm))

        # Risks
        if ar.risks:
            story.append(Paragraph("6.  Risk Register", sH1))
            rsk = [["Severity","Title","Description"]]
            for r in ar.risks:
                rsk.append([r["sev"], r["title"], r["desc"]])
            rst = Table(rsk, colWidths=[20*mm,50*mm,100*mm])
            rs_base = base_ts(rsk)
            for i, r in enumerate(ar.risks, 1):
                rs_base.add("BACKGROUND",(0,i),(0,i), colors.HexColor(r["col"]))
                rs_base.add("TEXTCOLOR",(0,i),(0,i), WHITE)
                rs_base.add("FONTNAME",(0,i),(0,i),"Helvetica-Bold")
            rst.setStyle(rs_base)
            story.append(rst); story.append(Spacer(1,2*mm))

    # ── Trench figure ────────────────────────────────────────────────────────────
    story.append(Paragraph("7.  Trench Cross-Section (to scale)", sH1))
    try:
        fig = _trench_fig(engine, res)
        img_buf = io.BytesIO()
        fig.savefig(img_buf, format="png", dpi=180, bbox_inches="tight",
                    facecolor="white")
        plt.close(fig)
        img_buf.seek(0)
        story.append(RLImage(img_buf, width=90*mm, height=105*mm))
    except Exception as e:
        story.append(Paragraph(f"[Figure unavailable: {e}]", sSM))

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story += [Spacer(1,5*mm), HRFlowable("100%",thickness=0.8,color=LBLUE), Spacer(1,2*mm)]
    story.append(Paragraph(
        "This report is produced by an IEC 60287 analytical engine for preliminary design "
        "purposes only. Results must be verified by a qualified engineer against manufacturer "
        "cable datasheets and site-specific geotechnical data before use in a final design. "
        "FEA analysis is required for complex duct-bank crossings, non-uniform soils, or "
        "external heat sources. Not a substitute for CYMCAP or equivalent validated software.",
        sSM))
    story.append(Paragraph(
        "Standards: IEC 60287-1-1:2014 · IEC 60287-2-1:2015 · IEC 60853-2:1989 · "
        "IEC 60502-2:2014 · IEC 60228:2004 · IEC 60949:1988 · VDE 0276-1000", sSM))

    doc.build(story)
    buf.seek(0)
    return buf.read()


def _trench_fig(engine, res):
    fig, ax = plt.subplots(figsize=(4.2, 5.2), facecolor="white")
    ax.set_facecolor("#f6f8fc")
    ax.set_aspect("equal")

    inst  = engine.inst
    depth = inst.depth
    De    = engine.De
    tw    = inst.trench_width

    # Fill
    ax.fill_between([-tw/2, tw/2], -(depth+De*3.2), 0, color="#e8ecd8", alpha=0.9)
    ax.fill_between([-tw/2, tw/2], -(depth+De*1.3), -(depth+De*2.1),
                    color="#f0e8c0", alpha=0.8, label="Sand bedding")
    ax.axhline(0, color="#3a6030", lw=2)

    positions = engine.cable_positions()
    for i, (cx, cy) in enumerate(positions):
        py = -cy
        ax.add_patch(plt.Circle((cx,py), De/2, color="#dde8d0", ec="#4a7050", lw=0.8, zorder=5))
        ax.add_patch(plt.Circle((cx,py), engine.dsc/2, color="#d8e4f0", ec="#3060a0", lw=0.5, zorder=6))
        ax.add_patch(plt.Circle((cx,py), engine.dc/2,
                                 color="#c8a840" if engine.cd["cond_mat"]=="Al" else "#b06820",
                                 zorder=7))
        ax.text(cx, py, "ABC"[i%3], ha="center", va="center",
                fontsize=5.5, fontweight="bold", color="white", zorder=8)
        if res.dry_zone:
            ax.add_patch(plt.Circle((cx,py), res.rx_m,
                                     fill=False, ls="--", ec="#c03020", lw=0.9,
                                     alpha=0.75, zorder=4,
                                     label="Dry zone" if i==0 else ""))

    ax.annotate("", xy=(tw/2+0.18, -depth), xytext=(tw/2+0.18, 0),
                arrowprops=dict(arrowstyle="<->", color="#3a5870", lw=0.9, mutation_scale=8))
    ax.text(tw/2+0.21, -depth/2, f"L={depth:.2f}m",
            fontsize=5.5, color="#3a5870", va="center")
    ax.annotate("", xy=(tw/2, -(depth+De*2.7)),
                xytext=(-tw/2, -(depth+De*2.7)),
                arrowprops=dict(arrowstyle="<->", color="#3a5870", lw=0.9, mutation_scale=8))
    ax.text(0, -(depth+De*2.9), f"W={tw:.2f}m",
            ha="center", fontsize=5.5, color="#3a5870")

    ax.set_xlim(-tw/2-0.3, tw/2+0.4)
    ax.set_ylim(-(depth+De*3.4), 0.35)
    ax.set_xlabel("m", fontsize=6.5); ax.set_ylabel("Depth (m)", fontsize=6.5)
    ytk = ax.get_yticks()
    ax.set_yticklabels([f"{abs(y):.1f}" for y in ytk], fontsize=5.5)
    ax.set_xticklabels([f"{x:.2f}" for x in ax.get_xticks()], fontsize=5.5)
    ax.set_title(f"{inst.formation.title()} · s={inst.phase_spacing*1000:.0f}mm · "
                 f"{inst.num_circuits} cct", fontsize=6.5, pad=3)
    ax.tick_params(length=2)
    if res.dry_zone:
        ax.legend(fontsize=5.5, loc="upper right", framealpha=0.6)
    fig.tight_layout(pad=0.5)
    return fig


def _fallback(engine, res, ar) -> bytes:
    lines = ["MV CABLE RATING REPORT", "="*50,
             f"Cable: {engine.cd['name']}",
             f"Depth: {engine.inst.depth:.2f}m  Formation: {engine.inst.formation}",
             f"Continuous: {res.I_cont:.1f}A  Cyclic: {res.I_cyclic:.1f}A (M={res.M_cyclic:.3f})",
             f"Emergency: {res.I_emerg:.1f}A  θ_cond={res.theta_cond:.2f}°C",
             f"ΔU: {res.dU_pct:.3f}%  Dry-zone: {'YES' if res.dry_zone else 'No'}",
             "", "Install 'reportlab' for full PDF: pip install reportlab"]
    if ar:
        lines += ["", "CHECKS"]
        for c in ar.checks:
            lines.append(f"  {'PASS' if c.passed else 'FAIL'}: {c.name}: {c.measured} / {c.limit}")
    return "\n".join(lines).encode()
