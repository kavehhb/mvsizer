"""
load_analysis.py — Load Adequacy, Recommendations & Risk Engine
"""
import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from cable_data import CABLE_LIBRARY, MATERIAL
from cable_engine import CableRatingEngine, InstallationParams, SoilParams, RatingResults, build_engine


@dataclass
class LoadParams:
    S_MVA: float              # Apparent power [MVA]
    pf: float = 0.95          # Power factor
    L_km: float = 1.0         # Route length [km]
    Isc_kA: float = 10.0      # Prospective 3-phase fault current [kA]
    t_fault: float = 0.5      # Fault clearance time [s]
    dU_limit_pct: float = 5.0 # Voltage-drop limit [%]
    system_voltage_kV: float = 0.0  # System operating voltage [kV]; 0 = use cable rated voltage U


@dataclass
class Check:
    name: str
    passed: bool
    measured: str
    limit: str
    margin_pct: float = 0.0
    note: str = ""


@dataclass
class Rec:
    level: str   # 'critical' | 'warning' | 'info'
    title: str
    body: str
    action: str = ""


@dataclass
class AnalysisResult:
    I_load: float = 0.0
    Usys_kV: float = 0.0
    P_MW:   float = 0.0
    Q_Mvar: float = 0.0
    util_cont_pct: float = 0.0
    util_cyc_pct:  float = 0.0
    theta_at_load: float = 0.0
    dU_load_V:     float = 0.0
    dU_load_pct:   float = 0.0
    Ic_A:          float = 0.0
    Isc_cond_kA:   float = 0.0
    Isc_screen_kA: float = 0.0

    checks:  List[Check] = field(default_factory=list)
    recs:    List[Rec]   = field(default_factory=list)
    risks:   List[dict]  = field(default_factory=list)

    alt_up_id:   Optional[str] = None
    alt_down_id: Optional[str] = None

    @property
    def all_pass(self): return all(c.passed for c in self.checks)


def analyse(engine: CableRatingEngine, res: RatingResults,
            load: LoadParams, cable_id: str,
            load_profile: Optional[List[float]] = None) -> AnalysisResult:
    ar = AnalysisResult()
    cd = engine.cd
    # Use the actual system operating voltage for current calculation.
    # The system voltage may differ from the cable rated voltage, e.g. a 20kV cable
    # may operate on a 22kV or 11kV network. If system_voltage_kV=0, fall back to
    # the cable rated voltage U_kV.
    Usys_kV = load.system_voltage_kV if load.system_voltage_kV > 0.0 else cd["U_kV"]
    Un = Usys_kV * 1e3
    ar.Usys_kV = round(Usys_kV, 1)

    # Load quantities
    I_load = load.S_MVA * 1e6 / (math.sqrt(3)*Un)
    ar.I_load = round(I_load, 1)
    ar.P_MW   = round(load.S_MVA * load.pf, 3)
    ar.Q_Mvar = round(load.S_MVA * math.sqrt(max(0,1-load.pf**2)), 3)

    ar.util_cont_pct = round(I_load / max(res.I_cont, 1) * 100, 1)
    ar.util_cyc_pct  = round(I_load / max(res.I_cyclic, 1) * 100, 1)

    # Voltage drop at actual load current + conductor temperature at that current
    theta_load = engine.temperature_at_current(I_load)
    ar.theta_at_load = round(theta_load, 2)
    dU, dU_pct, Ic = engine.voltage_drop(I_load, load.L_km, load.pf, theta_load)
    ar.dU_load_V   = round(dU, 1)
    ar.dU_load_pct = round(dU_pct, 3)
    ar.Ic_A        = round(Ic, 2)

    # SC
    sc = engine.short_circuit_rating(load.t_fault)
    ar.Isc_cond_kA   = sc["Isc_cond_kA"]
    ar.Isc_screen_kA = sc["Isc_screen_kA"]

    # ── Checks ────────────────────────────────────────────────────────────────
    # 1 Continuous thermal
    ok = I_load <= res.I_cont
    ar.checks.append(Check(
        "Continuous thermal rating", ok,
        f"{I_load:.0f} A", f"{res.I_cont:.0f} A",
        round((res.I_cont/max(I_load,1)-1)*100,1),
        "IEC 60287-1-1 eq.(1)"))

    # 2 Cyclic thermal
    if res.M_cyclic > 1.001:
        ok2 = I_load <= res.I_cyclic
        ar.checks.append(Check(
            "Cyclic thermal rating", ok2,
            f"{I_load:.0f} A", f"{res.I_cyclic:.0f} A",
            round((res.I_cyclic/max(I_load,1)-1)*100,1),
            f"IEC 60853-2, M={res.M_cyclic:.3f}, μ={res.mu:.3f}"))

    # 3 Voltage drop
    ok3 = dU_pct <= load.dU_limit_pct
    ar.checks.append(Check(
        "Voltage drop", ok3,
        f"{dU_pct:.3f}% ({dU:.0f} V)",
        f"{load.dU_limit_pct:.1f}%",
        round((load.dU_limit_pct/max(dU_pct,0.001)-1)*100,1),
        f"R corrected at θ={theta_load:.1f}°C"))

    # 4 Conductor SC
    ok4 = load.Isc_kA <= sc["Isc_cond_kA"]
    ar.checks.append(Check(
        "Conductor SC withstand", ok4,
        f"{load.Isc_kA:.1f} kA",
        f"{sc['Isc_cond_kA']:.1f} kA ({load.t_fault:.2f}s)",
        round((sc["Isc_cond_kA"]/max(load.Isc_kA,0.001)-1)*100,1),
        "IEC 60949 adiabatic"))

    # 5 Screen SC
    ok5 = load.Isc_kA <= sc["Isc_screen_kA"]
    ar.checks.append(Check(
        "Screen SC withstand", ok5,
        f"{load.Isc_kA:.1f} kA",
        f"{sc['Isc_screen_kA']:.1f} kA",
        round((sc["Isc_screen_kA"]/max(load.Isc_kA,0.001)-1)*100,1),
        "IEC 60949 (Cu screen, k=143)"))

    # 6 Dry-zone
    if res.dry_zone:
        ar.checks.append(Check(
            "Soil moisture stability", False,
            f"Surface {res.theta_surface:.1f}°C",
            f"Critical {engine.soil.T_crit}°C",
            round((engine.soil.T_crit/max(res.theta_surface,1)-1)*100,1),
            "IEC 60287-2-1 §2.2.3 two-zone model active"))

    # ── Find alternatives ─────────────────────────────────────────────────────
    ar.alt_up_id   = _find_cable(cable_id, engine, load, I_load, go="up")
    ar.alt_down_id = _find_cable(cable_id, engine, load, I_load, go="down")

    # ── Recommendations ───────────────────────────────────────────────────────
    _make_recs(ar, res, load, engine, cable_id, I_load, dU_pct, sc, theta_load)

    # ── Risk register ─────────────────────────────────────────────────────────
    ar.risks = _risks(ar, res, engine, load, I_load)

    return ar


def _find_cable(cable_id, engine, load, I_load, go="up"):
    cd = engine.cd
    Uo, U = cd["Uo_kV"], cd["U_kV"]
    vkey = f"_{Uo:.0f}_{U:.0f}kV"
    cs_curr = cd["cond_cs"]
    sizes = [50,70,95,120,150,185,240,300,400,500,630,800,1000]
    candidates = [s for s in sizes if (s > cs_curr if go == "up" else s < cs_curr)]
    if go == "down": candidates = list(reversed(candidates))
    for cs in candidates:
        cid = f"AL{cs}{vkey}"
        if cid not in CABLE_LIBRARY: continue
        ne = build_engine(CABLE_LIBRARY[cid], engine.inst, engine.soil, engine.f, engine.bonding)
        nr = ne.calculate()
        rated = nr.I_cyclic if nr.M_cyclic > 1.001 else nr.I_cont
        margin = rated / max(I_load, 1)
        if go == "up"   and margin >= 1.10: return cid
        if go == "down" and margin >= 1.15: return cid
    return None


def _make_recs(ar, res, load, engine, cable_id, I_load, dU_pct, sc, theta_load):
    r = ar.recs
    T_max = MATERIAL["T_max"].get(engine.cd["ins_mat"], 90.0)

    if ar.util_cont_pct > 100:
        up = ar.alt_up_id
        r.append(Rec("critical", "Cable thermally overloaded",
            f"Load {I_load:.0f} A exceeds continuous rating {res.I_cont:.0f} A "
            f"({ar.util_cont_pct:.1f}% utilisation). Insulation will degrade rapidly "
            f"(Arrhenius — each 10°C above rating halves cable life).",
            f"Upsize to {CABLE_LIBRARY[up]['name']}." if up else
            "Use parallel circuits or improve installation conditions."))
    elif ar.util_cont_pct > 90:
        r.append(Rec("warning", "Very high utilisation (>90%)",
            f"Only {100-ar.util_cont_pct:.1f}% thermal margin remains. "
            "Future load growth, higher ambient or poor soil conditions could cause overload.",
            "Plan for future upsizing or parallel circuit if load is expected to grow >10%."))
    elif ar.util_cont_pct < 50 and ar.alt_down_id:
        dn = ar.alt_down_id
        r.append(Rec("info", "Cable may be oversized",
            f"Current utilisation is only {ar.util_cont_pct:.1f}%. "
            f"A smaller cable may deliver significant cost savings.",
            f"Evaluate {CABLE_LIBRARY[dn]['name']} — verify voltage drop and SC withstand."))

    if dU_pct > load.dU_limit_pct:
        factor = dU_pct / load.dU_limit_pct
        cs_curr = engine.cd["cond_cs"]
        cs_need = int(cs_curr * factor * 1.1)
        r.append(Rec("critical", "Voltage drop exceeds limit",
            f"ΔU={dU_pct:.3f}% at θ={theta_load:.1f}°C exceeds the {load.dU_limit_pct:.1f}% limit. "
            f"Route length {load.L_km:.1f} km, load {I_load:.0f} A.",
            f"Options: (1) Upsize conductor to ≥{cs_need} mm², "
            "(2) Split into parallel circuits, (3) Add reactive compensation at load end."))
    elif dU_pct > 0.8 * load.dU_limit_pct:
        r.append(Rec("warning", "Voltage drop near limit",
            f"ΔU={dU_pct:.3f}% is within 20% of the {load.dU_limit_pct:.1f}% limit.",
            "Monitor load growth; consider route length reduction or larger conductor."))

    if not ar.checks[3].passed:
        r.append(Rec("critical", "Conductor SC thermal limit exceeded",
            f"Fault current {load.Isc_kA:.1f} kA exceeds conductor limit {sc['Isc_cond_kA']:.1f} kA "
            f"for {load.t_fault:.2f}s.",
            "Reduce fault clearance time (faster protection) or select larger conductor."))

    if not ar.checks[4].passed:
        r.append(Rec("critical", "Screen SC thermal limit exceeded",
            f"Fault current {load.Isc_kA:.1f} kA exceeds screen limit {sc['Isc_screen_kA']:.1f} kA.",
            "Specify 35 mm² Cu screen or implement cross-bonding to share fault current."))

    if res.dry_zone:
        r.append(Rec("warning", "Dry-zone formation — thermal runaway risk",
            f"Cable surface θ={res.theta_surface:.1f}°C exceeds dry-out threshold "
            f"{engine.soil.T_crit}°C. Moisture migrates outward, increasing soil resistance "
            f"and conductor temperature — a positive feedback that can lead to thermal runaway.",
            "Use Fluidised Thermal Backfill (FTB) ρ≤1.0 K·m/W or reduce loading. "
            "Alternatively increase burial depth or use trefoil formation."))

    if res.M_cyclic > 1.15:
        r.append(Rec("info", f"Cyclic benefit available (M={res.M_cyclic:.3f})",
            f"IEC 60853-2 cyclic ampacity {res.I_cyclic:.0f} A vs continuous {res.I_cont:.0f} A. "
            f"Loss load factor μ={res.mu:.3f} (profile: {load.L_km:.1f} km).",
            "Verify load profile with asset owner. For renewable generation, use the "
            "peak-irradiance / peak-wind design day as per IEC 60853-2 Annex B."))

    emerg_margin = (res.I_emerg / max(I_load, 1) - 1) * 100
    if emerg_margin < 10:
        r.append(Rec("warning", "Limited emergency headroom",
            f"Emergency rating {res.I_emerg:.0f} A is only {emerg_margin:.0f}% above "
            "the load current. N-1 contingency operation may not be feasible.",
            "Assess N-1 scenarios; consider parallel redundancy."))

    if res.lambda1 > 0.1 and engine.bonding == "both_ends":
        r.append(Rec("warning", f"High screen losses (λ₁={res.lambda1:.3f})",
            f"Screen loss factor {res.lambda1*100:.1f}% of conductor losses. "
            "Solid bonding (both-ends) causes circulating currents.",
            "Consider cross-bonding or single-point bonding to eliminate λ1_circ."))

    if ar.util_cont_pct < 100 and ar.util_cont_pct > 0:
        trench_margin = 100 - ar.util_cont_pct
        if trench_margin > 15 and engine.inst.trench_width > 0.7:
            r.append(Rec("info", "Trench width may be reducible",
                f"Cable utilisation {ar.util_cont_pct:.0f}% — thermal margin exists. "
                "If trench cost is significant, thermal modelling may allow a narrower trench.",
                "Re-run with reduced trench width and verify mutual heating correction."))


def _risks(ar, res, engine, load, I_load):
    risks = []
    T_max = MATERIAL["T_max"].get(engine.cd["ins_mat"], 90.0)
    margin_T = T_max - res.theta_cond

    if ar.util_cont_pct > 100:
        risks.append({"sev":"HIGH","col":"#c82020",
            "title":"Thermal Overload",
            "desc":"Load exceeds continuous ampacity. Rapid insulation ageing (Arrhenius law)."})
    elif ar.util_cont_pct > 90:
        risks.append({"sev":"MED","col":"#d06010",
            "title":"High Thermal Margin Consumption",
            "desc":"Less than 10% thermal margin. Vulnerable to ambient temperature excursions."})

    if margin_T < 5:
        risks.append({"sev":"HIGH","col":"#c82020",
            "title":"Minimal Temperature Margin",
            "desc":f"Operating at {res.theta_cond:.1f}°C — only {margin_T:.1f}°C below limit."})

    if res.dry_zone:
        risks.append({"sev":"HIGH","col":"#c82020",
            "title":"Dry-Zone Thermal Runaway",
            "desc":"Positive feedback: drying → higher ρ_soil → higher θ → more drying."})

    if ar.dU_load_pct > load.dU_limit_pct:
        risks.append({"sev":"HIGH","col":"#c82020",
            "title":"Voltage Quality Violation",
            "desc":f"ΔU={ar.dU_load_pct:.2f}% exceeds {load.dU_limit_pct:.1f}%. EN 50160 breach risk."})
    elif ar.dU_load_pct > 0.8*load.dU_limit_pct:
        risks.append({"sev":"MED","col":"#d06010",
            "title":"Voltage Drop Near Regulatory Limit",
            "desc":"Minor load growth could trigger EN 50160 violation."})

    if not ar.checks[3].passed:
        risks.append({"sev":"HIGH","col":"#c82020",
            "title":"Conductor SC Damage Risk",
            "desc":"Conductor may be destroyed on first earth fault at this network Isc."})

    if not ar.checks[4].passed:
        risks.append({"sev":"HIGH","col":"#c82020",
            "title":"Screen SC Damage Risk",
            "desc":"Cu screen may fail thermally on first earth fault."})

    if engine.bonding == "both_ends" and res.lambda1 > 0.1:
        risks.append({"sev":"MED","col":"#d06010",
            "title":"Screen Circulating Current Losses",
            "desc":f"λ₁={res.lambda1:.3f}: {res.lambda1*100:.1f}% additional loss, reduces effective ampacity."})

    if ar.Ic_A > 20:
        risks.append({"sev":"LOW","col":"#3a8040",
            "title":"Capacitive Reactive Power",
            "desc":f"Charging current {ar.Ic_A:.1f} A contributes capacitive Var load. "
                   "Check reactive power balance at both ends."})

    if not risks:
        risks.append({"sev":"OK","col":"#2a7040",
            "title":"No Significant Risks",
            "desc":"Cable meets all checked criteria with adequate margins."})
    return risks
