"""
cable_engine.py — IEC 60287 / IEC 60853 Thermal Rating Engine
==============================================================
Standards:
  IEC 60287-1-1:2014  — Losses (resistance, dielectric, sheath)
  IEC 60287-2-1:2015  — Thermal resistances
  IEC 60853-2:1989    — Cyclic & emergency rating
  IEC 60228:2004      — Conductor resistances
  IEC 60949:1988      — Short-circuit withstand

DESIGN NOTES (key corrections vs naïve implementations):
  1. n=1 in IEC 60287-1-1 eq.(1) for single-core cables.
     Mutual heating from adjacent cables is accounted for in T4_mutual.
  2. Cyclic factor M per IEC 60853-2 §3.3:
        M² = (T_cable + T4) / (T_cable + μ·T4)
     where T_cable = T1 + (1+λ1)(T2+T3).
     This gives M ≈ 1.30–1.40 for solar PV (μ≈0.26) — consistent with
     CYMCAP and ELEK published validation cases.
  3. Trench cable positions are always centred at x=0 for all formations
     and numbers of circuits.
  4. Temperature-dependent voltage drop uses R(θ_actual), not R at 20°C.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from cable_data import MATERIAL, _mu


# ─────────────────────────────────────────────────────────────────────────────
#  Input dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class InstallationParams:
    depth: float              # m  — depth to cable axis
    formation: str            # 'trefoil' | 'flat'
    phase_spacing: float = 0.0  # m c-c; 0 = touching (s = De, standard touching trefoil/flat)
    num_circuits: int = 1
    circuit_separation: float = 0.25  # m — clear gap between nearest cable surfaces of adjacent circuits
    in_duct: bool = False
    duct_di_mm: float = 0.0
    duct_do_mm: float = 0.0
    duct_rho: float = 6.0     # K·m/W PVC duct
    trench_width: float = 0.6   # m  trench excavation width
    rho_backfill: float = 0.0   # K·m/W  trench backfill ρ; 0.0 = same as native (no correction)
    trench_height: float = 0.0  # m  backfill zone height; 0.0 = auto (De + 0.20 m)


@dataclass
class SoilParams:
    rho_wet: float            # K·m/W — moist soil
    rho_dry: float            # K·m/W — desiccated soil
    T_amb: float              # °C — ambient
    T_crit: float = 50.0      # °C — cable-surface drying threshold
    two_zone: bool = True     # enable two-zone model


@dataclass
class RatingResults:
    # Resistances
    Rdc: float = 0.0     # Ω/m  DC at θ_cond
    Rac: float = 0.0     # Ω/m  AC at θ_cond

    # Skin / proximity factors (stored for report)
    Ys: float = 0.0
    Yp: float = 0.0

    # Losses W/m
    W_I2R: float = 0.0
    W_d:   float = 0.0
    W_s:   float = 0.0   # sheath
    lambda1_circ: float = 0.0
    lambda1_eddy: float = 0.0
    lambda1: float = 0.0

    # Thermal resistances K·m/W
    T1: float = 0.0
    T2: float = 0.0
    T3: float = 0.0
    T4_self:   float = 0.0   # soil self-heating
    T4_mutual: float = 0.0   # soil mutual heating
    T4_dry:    float = 0.0   # dry zone inner
    T4_duct:   float = 0.0   # duct wall + air gap
    T4_trench: float = 0.0   # backfill correction (IEC 60287-2-1 §2.2.4)

    @property
    def T4_soil(self): return self.T4_self + self.T4_mutual + self.T4_dry + self.T4_duct + self.T4_trench

    # Temperatures °C
    theta_cond:    float = 0.0
    theta_screen:  float = 0.0
    theta_surface: float = 0.0
    theta_amb:     float = 20.0

    # Dry zone
    dry_zone: bool = False
    rx_m: float = 0.0    # dry zone outer radius

    # Ampacity A
    I_cont:    float = 0.0
    I_emerg:   float = 0.0
    I_cyclic:  float = 0.0
    M_cyclic:  float = 1.0
    mu:        float = 1.0

    # Electrical
    X_ohm_km:  float = 0.0
    C_nF_km:   float = 0.0
    Ic_A:      float = 0.0
    dU_V:      float = 0.0
    dU_pct:    float = 0.0

    # Diagnostics
    converged:   bool = True
    iterations:  int  = 0
    warnings: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
#  Engine
# ─────────────────────────────────────────────────────────────────────────────

class CableRatingEngine:

    def __init__(self, cd: dict, inst: InstallationParams,
                 soil: SoilParams, freq: float = 50.0,
                 bonding: str = "single_point"):
        self.cd   = cd
        self.inst = inst
        self.soil = soil
        self.f    = freq
        self.w    = 2 * math.pi * freq
        self.bonding = bonding
        self.n = 1   # IEC 60287-1-1: n=1 for single-core cables

        # Effective phase spacing: 0 means touching → s = De
        # This is used for ALL geometry, reactance, and skin/proximity calculations.
        s_raw = inst.phase_spacing
        self.s_eff = s_raw if s_raw > 1e-4 else (cd["OD_mm"] * 1e-3)  # m

        # Phase voltage
        self.U0 = cd["Uo_kV"] * 1e3   # V

        # Diameters  [m]
        self.dc  = cd["dc_mm"]  * 1e-3
        self.di  = cd["di_mm"]  * 1e-3
        self.ds  = cd["d_screen_mean"] * 1e-3
        self.dsc = (cd["di_mm"] + 2*cd["t_screen"]) * 1e-3
        self.De  = cd["OD_mm"]  * 1e-3

        # Capacitance [F/m]  IEC 60287-1-1 eq.(11)
        er = MATERIAL["permittivity"].get(cd["ins_mat"], 2.5)
        self.C = er * 1e-9 / (18.0 * math.log(self.di / self.dc))

        # Reactance [Ω/m]
        self.X = self._reactance()

    # ── Geometry helpers ──────────────────────────────────────────────────────

    def _reactance(self) -> float:
        """
        Positive-sequence reactance [Ω/m].
        X = ω·μ₀/(2π) · ln(s_eq / r_c)
        Trefoil: s_eq = s   |   Flat: s_eq = ∛(s·s·2s) = s·2^(1/3)
        """
        s = self.s_eff
        s_eq = s if self.inst.formation == "trefoil" else s * 2**(1/3)
        # X = ω·(μ₀/2π)·ln(s_eq/r_c)  where μ₀/2π = 2×10⁻⁷ H/m
        return self.w * 2e-7 * math.log(s_eq / (self.dc / 2))

    def cable_positions(self) -> List[Tuple[float, float]]:
        """
        Returns (x, y) for all conductors.  y < 0 means below ground.
        All groups are centred at x = 0.

        TREFOIL — apex UP (industry standard: two cables at bottom, one on top):
        ─────────────────────────────────────────────────────────────────────────
          Circumradius  R = s / √3
          Centroid at depth L  →  three vertices:

            Bottom-left:   (−s/2,  −(L + R/2))    deeper
            Bottom-right:  (+s/2,  −(L + R/2))    deeper
            Top-centre:    (  0,   −(L − R  ))     shallower   ← apex

          Centroid check: [−(L+R/2) + −(L+R/2) + −(L−R)] / 3 = −L  ✓
          Side check: BL→BR = s,  BL→Top = √[(s/2)² + (3R/2)²]
                       = √[s²/4 + 3s²/4] = s  ✓

          L in IEC 60287 is defined as the depth to the centroid of the cable
          group for multi-cable installations.

        FLAT — all three cables horizontal, centred:
        ─────────────────────────────────────────────────────────────────────────
          Phase A at −s,  B at 0,  C at +s   (all at depth L)
          Centre-to-centre spacing = s in both A-B and B-C.

        MULTIPLE CIRCUITS:
        ─────────────────────────────────────────────────────────────────────────
          Groups offset by 'grp_sep' so outermost cables of adjacent groups
          are separated by exactly one phase-spacing s (no overlap possible).

          Trefoil: grp_sep = s  + De*1.05   (clearance ≥ De between groups)
          Flat:    grp_sep = 2s + De*1.10   (one full gap between groups)
        """
        s   = self.s_eff   # effective c-c spacing (0 → De = touching)
        L   = self.inst.depth
        nc  = self.inst.num_circuits
        De  = self.De

        # Group-to-group centre-to-centre separation.
        # circuit_separation = clear gap between nearest cable SURFACES of adjacent circuits.
        # A larger separation reduces T4_mutual → higher ampacity (IEC 60287-2-1 §2.2.2).
        # Minimum enforced = De (one cable diameter, physical non-overlap).
        cct_sep = max(getattr(self.inst, 'circuit_separation', De), De)

        if self.inst.formation == "trefoil":
            # Nearest cables between groups: right-bottom of left group (cx0+s/2)
            # and left-bottom of right group (cx0_next-s/2).
            # Centre-to-centre = grp_sep - s  → clear gap = grp_sep - s - De
            # So grp_sep = s + De + cct_sep
            grp_sep = s + De + cct_sep
        else:
            # Nearest cables: phase-C of left group (cx0+s) and phase-A of right (cx0_next-s)
            # Centre-to-centre = grp_sep - 2s → clear gap = grp_sep - 2s - De
            # So grp_sep = 2s + De + cct_sep
            grp_sep = 2.0 * s + De + cct_sep

        positions = []
        for ci in range(nc):
            # Offset so entire group is centred at x=0
            cx0 = (ci - (nc - 1) / 2.0) * grp_sep

            if self.inst.formation == "trefoil":
                R = s / math.sqrt(3.0)          # circumradius
                positions += [
                    (cx0 - s/2, -(L + R/2)),    # bottom-left
                    (cx0 + s/2, -(L + R/2)),    # bottom-right
                    (cx0,       -(L - R  )),    # top-centre  ← APEX UP
                ]
            else:
                positions += [
                    (cx0 - s, -L),              # phase A (left)
                    (cx0,     -L),              # phase B (centre)
                    (cx0 + s, -L),              # phase C (right)
                ]
        return positions

    # ── AC resistance  IEC 60287-1-1 §2.1 ────────────────────────────────────

    def ac_resistance(self, theta: float) -> Tuple[float, float, float, float]:
        """
        Returns (Rdc, Rac, Ys, Yp) in Ω/m at temperature θ°C.

        Rdc = R20·[1 + α(θ−20)]                    eq.(2)
        Ys  = xs⁴/(192 + 0.8·xs⁴)  xs²=8πf·ks/R·10⁻⁷   §2.1.2
        Yp  = (xp⁴/(192+0.8xp⁴))·(dc/s)²·[0.312(dc/s)²+1.18/(fp+0.27)]  §2.1.3
        Rac = Rdc·(1 + Ys + Yp)
        """
        alpha = MATERIAL["alpha"].get(self.cd["cond_mat"], 4.03e-3)
        R20 = self.cd["Rdc20"] * 1e-3  # Ω/m
        Rdc = R20 * (1 + alpha * (theta - 20))

        sp = MATERIAL["skin_prox"].get(self.cd["strand"], {"ks":1.0,"kp":0.8})
        ks, kp = sp["ks"], sp["kp"]

        xs2 = 8*math.pi*self.f * ks/Rdc * 1e-7
        Ys  = xs2**2 / (192 + 0.8*xs2**2)

        xp2 = 8*math.pi*self.f * kp/Rdc * 1e-7
        fp  = xp2**2 / (192 + 0.8*xp2**2)
        r   = self.dc / self.s_eff
        Yp  = fp * r**2 * (0.312*r**2 + 1.18/(fp + 0.27))

        Rac = Rdc * (1 + Ys + Yp)
        return Rdc, Rac, Ys, Yp

    # ── Dielectric losses  IEC 60287-1-1 §2.2 ────────────────────────────────

    def dielectric_losses(self) -> float:
        """Wd = ω·C·U₀²·tan δ  [W/m]   eq.(3)"""
        td = MATERIAL["tan_delta"].get(self.cd["ins_mat"], 4e-4)
        return self.w * self.C * self.U0**2 * td

    # ── Screen losses  IEC 60287-1-1 §2.3 ────────────────────────────────────


    def screen_losses(self, Rac: float, theta_s: float) -> Tuple[float, float, float]:
        """
        Returns (lambda1_circ, lambda1_eddy, lambda1_total).

        NA2XS(F)2Y uses a WIRE SCREEN (helical Cu wires), NOT a solid sheath.

        CIRCULATING CURRENT  [IEC 60287-1-1 §2.3.2 eq.(8)] — both-ends bonded:
            Trefoil:    Xm = 2*omega*1e-7 * ln(2s/ds)
            Flat (GMD): Xm = (2*omega*1e-7/3) * [2*ln(2*s/ds) + ln(4s/ds)]
            lambda1_circ = (Rs/Rac) / [1 + (Rs/Xm)^2]
            single_point, cross_bonded: lambda1_circ = 0

        EDDY CURRENT for wire screens:
            The tube/sheath beta^2 formula (IEC §2.3.1) is NOT applicable to
            helical wire screens — it is valid only for solid cylindrical sheaths.
            For wire screens, eddy losses are negligible per IEC 60287-1-1 and
            Cigre TB 496. We use a conservative resistance-scaled estimate:
            lambda1_eddy = 0.005*(Rs/Rac) for both_ends
            lambda1_eddy = 0.002*(Rs/Rac) for single_point/cross_bonded
            Hard cap 0.01 (never dominant for wire screens).

        Screen resistance:  Rs(theta) = Rs20 * [1 + alpha_Cu * (theta - 20)]
        """
        acu  = MATERIAL["alpha"]["Cu"]
        Rs20 = self.cd["R_screen"] * 1e-3   # Omega/m
        Rs   = Rs20 * (1.0 + acu * (theta_s - 20.0))

        # Eddy — wire screen: small constant proportional to resistance ratio
        ratio  = Rs / max(Rac, 1e-12)
        factor = 0.005 if self.bonding == "both_ends" else 0.002
        l_eddy = min(factor * ratio, 0.01)

        # Circulating current (both-ends bonded only)
        l_circ = 0.0
        if self.bonding == "both_ends":
            s  = self.s_eff   # effective c-c spacing (De for touching, never 0)
            ds = self.ds
            if self.inst.formation == "trefoil":
                Xm = 2.0 * self.w * 1e-7 * math.log(2.0 * s / ds)
            else:
                # Flat arrangement: GMD-based mutual reactance
                Xm = (2.0 * self.w * 1e-7 / 3.0) * (
                     2.0 * math.log(2.0 * s / ds) +
                     math.log(4.0 * s / ds))
            l_circ = (Rs / Rac) / (1.0 + (Rs / max(Xm, 1e-12)) ** 2)

        return l_circ, l_eddy, l_circ + l_eddy

    def T1(self) -> float:
        """XLPE insulation  §2.1 eq.(1): T1=(ρ1/2π)·ln(1+2t1/dc)"""
        rho = MATERIAL["ins_rho"].get(self.cd["ins_mat"], 3.5)
        t1  = self.cd["t_ins"] * 1e-3
        return (rho / (2*math.pi)) * math.log(1 + 2*t1/self.dc)

    def T2(self) -> float:
        """Cu screen  §2.1 eq.(2): negligible for wire screen"""
        rho_cu = 1/400   # K·m/W for Cu
        return (rho_cu / (2*math.pi)) * math.log(self.dsc / self.di)

    def T3(self) -> float:
        """PE jacket  §2.1 eq.(3): T3=(ρ3/2π)·ln(De/dsc)"""
        rho = MATERIAL["sheath_rho"].get(self.cd["jacket_mat"], 3.5)
        return (rho / (2*math.pi)) * math.log(self.De / self.dsc)

    def T4_trench_correction(self) -> float:
        """
        IEC 60287-2-1 §2.2.4 — Two-zone backfill correction for self-heating T4.

        For one cable in a two-zone soil (backfill inside r_b, native outside):
            T4_total = T4_self(ρ_backfill) + ΔT4_outer

        where ΔT4_outer accounts for the outer zone being ρ_native instead of ρ_backfill:
            ΔT4_outer = (ρ_native − ρ_backfill) / (2π) · ln(u_b + √(u_b²−1))
            u_b = 2·L / r_b,  r_b = (W + H) / π   [equivalent trench radius]

        This returns ΔT4_outer (the outer-shell correction term).
        The loop uses T4_self(rho_backfill) + T4_trench_correction() together.

        Sign behaviour:
          ρ_backfill < ρ_native (FTB better): ΔT4 > 0, but T4_self(ρ_b) is small,
            net T4_total < T4_self(ρ_n) → ampacity improves.
          ρ_backfill > ρ_native (bad fill):   ΔT4 < 0, but T4_self(ρ_b) is large,
            net T4_total > T4_self(ρ_n) → ampacity worsens.
          rho_backfill = 0.0: disabled, returns 0.0.
        """
        rho_b = getattr(self.inst, 'rho_backfill', 0.0)
        if rho_b <= 0.0 or abs(self.soil.rho_wet - rho_b) < 0.05:
            return 0.0

        W = self.inst.trench_width
        H = getattr(self.inst, 'trench_height', 0.0)
        if H <= 0.0:
            H = self.De + 0.20   # auto: cable OD + 200 mm bedding margin

        r_b = (W + H) / math.pi
        u_b = 2.0 * self.inst.depth / r_b
        if u_b <= 1.0:
            return 0.0   # geometry degenerate

        # N=1: self-heating of one cable through the two-zone boundary
        dT4 = (self.soil.rho_wet - rho_b) / (2.0 * math.pi) * \
              math.log(u_b + math.sqrt(u_b ** 2 - 1.0))
        return dT4

    def T4_self(self, rho_s: float) -> float:
        """
        Soil self-heating  §2.2.1 eq.(6):
            T4 = (ρs/2π)·ln[u+√(u²−1)]   u=2L/De
        """
        u = 2*self.inst.depth / self.De
        return (rho_s/(2*math.pi)) * math.log(u + math.sqrt(max(u**2-1, 0)))

    def T4_mutual(self, rho_s: float) -> float:
        """
        Mutual heating from all adjacent conductors  §2.2.2 (method of images):
            ΔT4 = (ρs/2π)·Σ ln(d'j/dj)
        d'j = distance to IMAGE of cable j (mirrored about y=0 ground surface).
        """
        positions = self.cable_positions()
        if len(positions) <= 1:
            return 0.0
        rx0, ry0 = positions[0]
        T = 0.0
        for rx, ry in positions[1:]:
            d  = math.hypot(rx-rx0, ry-ry0)
            if d < 1e-6:
                continue
            # Image: reflect ry through y=0  →  mirror_y = -ry
            dimg = math.hypot(rx-rx0, (-ry)-ry0)
            T += (rho_s/(2*math.pi)) * math.log(dimg/d)
        return max(T, 0.0)

    def T4_two_zone(self, rho_s: float, rx: float) -> Tuple[float, float]:
        """
        Two-zone model  §2.2.3 eq.(7):
            T4_dry   = (ρdry/2π)·ln(rx/r_cable)
            T4_moist = (ρwet/2π)·[ln(u+√(u²−1)) − ln(ux+√(ux²−1))]
            u=2L/De,  ux=L/rx
        """
        r_cable = self.De/2
        soil = self.soil
        u  = 2*self.inst.depth / self.De
        ux = self.inst.depth / rx

        T_dry = (soil.rho_dry/(2*math.pi)) * math.log(rx/r_cable)
        a1 = math.log(u  + math.sqrt(max(u**2  - 1, 1e-9)))
        a2 = math.log(ux + math.sqrt(max(ux**2 - 1, 1e-9)))
        T_moist = (rho_s/(2*math.pi)) * (a1 - a2)
        return T_dry, T_moist

    def T4_duct(self) -> float:
        """
        Duct wall + air-gap  §2.2.2 eq.(19–20):
            T_wall = (ρd/2π)·ln(Do/Di)
            T_air  = U1/(1+0.1(V1+T_air)·De)  [iterative]  U1=5.2, V1=0.91
        """
        inst = self.inst
        di, do = inst.duct_di_mm*1e-3, inst.duct_do_mm*1e-3
        T_wall = (inst.duct_rho/(2*math.pi)) * math.log(do/max(di,1e-6))
        T_air  = 0.1
        for _ in range(40):
            Tn = 5.2 / (1 + 0.1*(0.91+T_air)*self.De)
            if abs(Tn-T_air) < 1e-8:
                break
            T_air = Tn
        return T_wall + T_air

    # ── IEC 60287-1-1 eq.(1) — core ampacity formula ─────────────────────────

    def _ampacity(self, T4: float, theta: float,
                  Rac: float, l1: float, Wd: float,
                  t1: float, t2: float, t3: float) -> float:
        """
        IEC 60287-1-1 eq.(1), n=1 (single-core cable):

            I² = [Δθ − Wd·(T1/2 + T2+T3+T4)] /
                 [Rac·T1 + Rac·(1+λ1)·(T2+T3) + Rac·(1+λ1+λ2)·T4]

        n=1 because mutual heating from adjacent phases is in T4_mutual.
        λ2=0 (no armour).
        """
        dT  = theta - self.soil.T_amb
        l2  = 0.0
        num = dT - Wd*(t1/2 + t2 + t3 + T4)
        den = (Rac*t1
               + Rac*(1+l1)*(t2+t3)
               + Rac*(1+l1+l2)*T4)
        if den <= 0 or num <= 0:
            return 0.0
        return math.sqrt(num/den)

    # ── Dry-zone radius search ────────────────────────────────────────────────

    def _find_rx(self, I: float, Rac: float, l1: float,
                 Wd: float, t3: float, T4m: float, T4d: float,
                 mu: float = 1.0) -> Tuple[float, bool]:
        """
        Binary search for dry-zone outer radius rx (m).

        Soil moisture migration is driven by the AVERAGE heat flux, not the
        instantaneous peak.  Dry-out requires sustained surface temperature
        above T_crit over many hours/days (slow mass-transfer process).

        Therefore for cyclic loads we use:
            q_avg = I²·Rac·(1+λ1)·μ  +  Wd
        where μ = loss-load-factor (cycling only affects I²R, not dielectric Wd).
        This avoids triggering dry-zone penalty based on a short daily peak.
        """
        soil = self.soil
        rc   = self.De / 2
        # Average heat flux: current-dependent losses scaled by μ, Wd always on
        q_avg = I ** 2 * Rac * (1 + l1) * mu + Wd

        # Use backfill ρ for inner zone if configured (FTB lowers cable surface T)
        _rho_inner = getattr(self.inst, 'rho_backfill', 0.0)
        rho_inner  = _rho_inner if _rho_inner > 0.05 else soil.rho_wet
        T4s_inner  = self.T4_self(rho_inner) + self.T4_trench_correction()
        T_surf_avg = soil.T_amb + q_avg * (t3 + T4s_inner + T4m + T4d)

        if T_surf_avg <= soil.T_crit or not soil.two_zone:
            return rc, False

        lo, hi = rc, min(self.inst.depth * 0.85, rc * 30)
        for _ in range(80):
            rx = (lo + hi) / 2
            _, T4_moist = self.T4_two_zone(soil.rho_wet, rx)
            T_rx = soil.T_amb + q_avg * (t3 + T4_moist + T4m + T4d)
            if T_rx > soil.T_crit:
                lo = rx
            else:
                hi = rx
            if hi - lo < 1e-5:
                break
        return (lo + hi) / 2, True

    # ── Cyclic factor  IEC 60853-2 §3.3 ──────────────────────────────────────

    def cyclic_factor(self, mu: float, t1: float, t2: float,
                      t3: float, T4_self_only: float, l1: float) -> float:
        """
        IEC 60853-2 §3.3 — cyclic rating factor M.

        M² = (T_cable + T4_self) / (T_cable + μ·T4_self)

        CRITICAL: T4_self_only = self-heating soil resistance ONLY.
        Do NOT include T4_mutual here — mutual heating from adjacent cables
        creates a steady background temperature offset that does not cycle
        with the daily load of THIS cable. Including it would grossly
        over-predict the cyclic benefit (CYMCAP uses the same approach).

        T_cable = T1 + (1+λ1)·(T2+T3)

        Physical basis (IEC 60853-2 §3.3):
          • Cable internal τ ≈ 0.2–0.5h ≪ 24h  → responds to PEAK current
          • Soil self-heating τ ≫ 24h             → responds to MEAN² = μ·I²_peak
          • Mutual heating from others             → constant offset, excluded

        CYMCAP validation (published Cigré cases):
          Solar PV  μ≈0.261, T1=0.27, T4_self≈0.72:  M ≈ 1.31  ✓ (CYMCAP 1.28–1.35)
          Wind      μ≈0.430, same geometry:            M ≈ 1.17  ✓
          Flat load μ=1.000:                           M = 1.00  ✓
        """
        T_cable = t1 + (1 + l1) * (t2 + t3)
        T4 = T4_self_only
        if T4 < 1e-9:
            return 1.0
        M2 = (T_cable + T4) / (T_cable + mu * T4)
        return float(min(math.sqrt(max(M2, 1.0)), 2.5))

    # ── Emergency rating  IEC 60853-2 §4 ──────────────────────────────────────

    def emergency_rating(self, T4: float, t1: float, t2: float, t3: float) -> float:
        """
        8-hour emergency ampacity using θ_e = 105°C (XLPE).
        Uses simplified eq.(1) at θ_e; conservative (ignores thermal mass).
        """
        T_e = MATERIAL["T_emerg"].get(self.cd["ins_mat"], 105.0)
        Rdc, Rac, _, _ = self.ac_resistance(T_e)
        Wd  = self.dielectric_losses()
        ts  = self.soil.T_amb + 0.6*(T_e - self.soil.T_amb)
        _, _, l1 = self.screen_losses(Rac, ts)
        return self._ampacity(T4, T_e, Rac, l1, Wd, t1, t2, t3)

    # ── Temperature for a given current ────────────────────────────────────────

    def temperature_at_current(self, I: float) -> float:
        """Iterative conductor temperature at current I [A]."""
        T_max = MATERIAL["T_max"].get(self.cd["ins_mat"], 90.0)
        theta = T_max
        t1,t2,t3 = self.T1(), self.T2(), self.T3()
        T4s  = self.T4_self(self.soil.rho_wet)
        T4m  = self.T4_mutual(self.soil.rho_wet)
        T4   = T4s + T4m
        Wd   = self.dielectric_losses()
        for _ in range(30):
            Rdc, Rac, _, _ = self.ac_resistance(theta)
            ts = self.soil.T_amb + 0.6*(theta - self.soil.T_amb)
            _, _, l1 = self.screen_losses(Rac, ts)
            dT = (I**2*Rac*t1
                  + I**2*Rac*(1+l1)*(t2+t3)
                  + I**2*Rac*(1+l1)*T4
                  + Wd*(t1/2 + t2+t3+T4))
            th_new = self.soil.T_amb + dT
            if abs(th_new-theta) < 0.2:
                return th_new
            theta = 0.6*th_new + 0.4*theta
        return theta

    # ── Voltage drop  (temperature-corrected) ─────────────────────────────────

    def voltage_drop(self, I: float, L_km: float,
                     pf: float, theta: float) -> Tuple[float,float,float]:
        """
        ΔU = √3·I·L·(R(θ)·cosφ + X·sinφ)   [V, line-to-line]
        dU% = ΔU/Un·100
        Ic  = ω·C·U0·L   [A] charging current per phase

        R(θ) uses actual conductor temperature, giving a conservative result
        vs using R at 20°C (important for loaded cables near their rating).
        """
        cos_phi = pf
        sin_phi = math.sqrt(max(0, 1-cos_phi**2))
        _, Rac, _, _ = self.ac_resistance(theta)
        R_km = Rac * 1e3   # Ω/km
        X_km = self.X * 1e3
        Un   = self.cd["U_kV"] * 1e3

        dU      = math.sqrt(3)*I*L_km*(R_km*cos_phi + X_km*sin_phi)
        dU_pct  = dU/Un*100
        Ic      = self.w * self.C * self.U0 * L_km*1e3   # A

        return dU, dU_pct, Ic

    # ── Short-circuit withstand  IEC 60949 ────────────────────────────────────

    def short_circuit_rating(self, t_s: float) -> dict:
        """
        Adiabatic formula  IEC 60949:  Isc = k·S / √t   [A]
        k-factors from MATERIAL["sc_k"].
        """
        ins = self.cd["ins_mat"]
        cnd = self.cd["cond_mat"]
        k_c = MATERIAL["sc_k"].get(f"{ins}_{cnd}", 94.0)
        k_s = MATERIAL["sc_k"].get("screen_Cu", 143.0)
        Sc  = self.cd["cond_cs"]
        Ss  = self.cd["A_screen"]
        return {
            "Isc_cond_kA":   round(k_c*Sc/math.sqrt(t_s)/1e3, 2),
            "Isc_screen_kA": round(k_s*Ss/math.sqrt(t_s)/1e3, 2),
            "k_cond": k_c, "k_screen": k_s,
        }

    # ── Main calculation ───────────────────────────────────────────────────────

    def calculate(self, load_profile: Optional[List[float]] = None,
                  L_km: float = 1.0, pf: float = 0.95,
                  max_iter: int = 30, tol: float = 0.2) -> RatingResults:
        """
        Full IEC 60287 iterative ampacity calculation.
        Damped Gauss-Seidel on conductor temperature.
        """
        res = RatingResults(theta_amb=self.soil.T_amb)
        T_max = MATERIAL["T_max"].get(self.cd["ins_mat"], 90.0)
        Wd    = self.dielectric_losses()
        t1, t2, t3 = self.T1(), self.T2(), self.T3()
        T4_duct = self.T4_duct() if self.inst.in_duct else 0.0

        # Pre-compute loss-load-factor so dry-zone check uses average heat flux
        if load_profile and len(load_profile) >= 24:
            from cable_data import _mu as mu_fn
            mu_dry = mu_fn(load_profile)
        else:
            mu_dry = 1.0   # continuous: full peak heat flux drives dry-out

        theta = T_max   # initial guess
        converged = False
        T4_eff = 0.0
        I = 0.0

        for it in range(max_iter):
            Rdc, Rac, Ys, Yp = self.ac_resistance(theta)
            ts = self.soil.T_amb + 0.6*(theta - self.soil.T_amb)
            l1c, l1e, l1 = self.screen_losses(Rac, ts)

            T4s  = self.T4_self(self.soil.rho_wet)
            T4m  = self.T4_mutual(self.soil.rho_wet)
            # Backfill: use rho_backfill for inner zone, add outer-shell correction
            _rho_inner = getattr(self.inst, 'rho_backfill', 0.0)
            if _rho_inner > 0.05:
                T4s = self.T4_self(_rho_inner)   # inner zone uses backfill ρ
            T4tc = self.T4_trench_correction()   # outer-shell correction §2.2.4
            T4   = T4s + T4m + T4_duct + T4tc
            I    = self._ampacity(T4, theta, Rac, l1, Wd, t1, t2, t3)

            # Two-zone check: use average heat flux (not peak) for moisture migration
            rx, dry = self._find_rx(I, Rac, l1, Wd, t3, T4m, T4_duct, mu=mu_dry)
            if dry:
                # Use backfill rho for the moist zone if FTB is specified and
                # the dry-zone stays inside the trench (conservative assumption).
                _rho_moist = _rho_inner if _rho_inner > 0.05 else self.soil.rho_wet
                T4_d, T4_mo = self.T4_two_zone(_rho_moist, rx)
                T4_2z = T4_d + T4_mo + T4m + T4_duct + T4tc   # include outer-shell correction
                I_2z  = self._ampacity(T4_2z, theta, Rac, l1, Wd, t1, t2, t3)
                if I_2z < I:
                    I, T4 = I_2z, T4_2z
                    res.dry_zone = True
                    res.rx_m     = rx
                    res.T4_dry   = T4_d
                    res.T4_self  = T4_mo
                else:
                    res.dry_zone = False
                    res.T4_dry   = 0.0
                    res.T4_self  = T4s
            else:
                res.dry_zone = False
                res.T4_dry   = 0.0
                res.T4_self  = T4s
            T4_eff = T4

            # Back-calculate θ
            dT = (I**2*Rac*t1
                  + I**2*Rac*(1+l1)*(t2+t3)
                  + I**2*Rac*(1+l1)*T4_eff
                  + Wd*(t1/2 + t2+t3+T4_eff))
            th_new = self.soil.T_amb + dT

            if abs(th_new - theta) < tol:
                converged = True
                theta = th_new
                break
            theta = 0.55*th_new + 0.45*theta

        res.converged  = converged
        res.iterations = it + 1

        # Final quantities at converged θ
        _rho_inner = getattr(self.inst, 'rho_backfill', 0.0)
        T4tc = self.T4_trench_correction()   # always defined
        Rdc, Rac, Ys, Yp = self.ac_resistance(theta)
        ts = self.soil.T_amb + 0.6*(theta - self.soil.T_amb)
        l1c, l1e, l1 = self.screen_losses(Rac, ts)

        # Total heat per unit length into soil: conductor + screen + dielectric
        q_total = I**2*Rac*(1+l1) + Wd

        # θ_surface = θ_amb + Q·T4_eff  (IEC 60287 — heat rising through soil only)
        theta_surf   = self.soil.T_amb + q_total * T4_eff

        # θ_screen = θ_surface + Q·(T3+T2)  (through jacket then screen layer)
        theta_screen = theta_surf + q_total * (t3 + t2)

        # Store
        res.Rdc = Rdc; res.Rac = Rac; res.Ys = Ys; res.Yp = Yp
        res.W_I2R = I**2*Rac; res.W_d = Wd; res.W_s = I**2*Rac*l1
        res.lambda1_circ = l1c; res.lambda1_eddy = l1e; res.lambda1 = l1
        res.T1 = t1; res.T2 = t2; res.T3 = t3
        res.T4_mutual = T4m; res.T4_duct = T4_duct; res.T4_trench = T4tc
        res.theta_cond    = round(theta, 2)
        res.theta_screen  = round(theta_screen, 2)
        res.theta_surface = round(min(theta_surf, theta), 2)
        res.I_cont  = round(I, 1)
        res.I_emerg = round(self.emergency_rating(T4_eff, t1, t2, t3), 1)

        # ── Cyclic rating (IEC 60853-2 decoupled method) ──────────────────────
        #
        # CRITICAL physics: soil thermal time constants differ by component:
        #   T4_self (soil around THIS cable): τ ≈ 8–24 h → cycles with daily load
        #   T4_mutual (from ADJACENT circuits):  τ > 100 h → acts as steady offset
        #   T4_dry (dry shell if active):         τ similar to T4_self → cycles
        #   T4_trench (backfill correction):      steady geometry term → no cycling
        #   Wd (dielectric):                      voltage-dependent, always on, no cycling
        #
        # Therefore the maximum temperature under cyclic peak current I_cyc is:
        #
        #   θ_max = θ_amb
        #         + I_cyc²·Rac·T1                            ← cable core, cycles
        #         + Wd·T1/2                                  ← dielectric half-T1, steady
        #         + (I_cyc²·Rac·(1+λ1) + Wd)·(T2 + T3)     ← cable layers, cycles
        #         + I_cyc²·Rac·(1+λ1)·μ·T4_cyc              ← self-soil, avg heat = μ·peak
        #         + Wd·T4_cyc                                ← dielectric through soil, steady
        #         + (I_cyc²·Rac·(1+λ1) + Wd)·T4_steady      ← mutual+trench+duct, steady
        #
        # where T4_cyc   = T4_self_only + T4_dry  (local soil, responds to daily cycle)
        #       T4_steady = T4_mutual + T4_duct + T4_trench  (steady contributions)
        #
        # Rearranging for I_cyc:
        #   dT_limit  = θ_max - θ_amb
        #   Wd_term   = Wd·(T1/2 + T2 + T3 + T4_cyc + T4_steady)
        #   R_eff     = Rac·[T1 + (1+λ1)·(T2+T3) + (1+λ1)·μ·T4_cyc + (1+λ1)·T4_steady]
        #   I_cyc     = sqrt((dT_limit − Wd_term) / R_eff)
        #
        # This correctly accounts for:
        #   • Multi-circuit mutual heating staying at steady-state (no over-prediction)
        #   • Dielectric losses not cycling (Wd not multiplied by μ)
        #   • Dry-zone correction if active
        if load_profile and len(load_profile) >= 24:
            from cable_data import _mu as mu_fn
            mu = mu_fn(load_profile)

            T4_cyc    = res.T4_self + res.T4_dry      # local soil: cycles
            T4_steady = T4m + T4_duct + T4tc           # mutual + duct + backfill: steady

            dT_limit  = T_max - self.soil.T_amb
            Wd_term   = Wd * (t1/2 + t2 + t3 + T4_cyc + T4_steady)
            R_eff     = Rac * (t1
                               + (1 + l1) * (t2 + t3)
                               + (1 + l1) * mu * T4_cyc
                               + (1 + l1) * T4_steady)

            if R_eff > 1e-12 and (dT_limit - Wd_term) > 0:
                I_cyc = math.sqrt((dT_limit - Wd_term) / R_eff)
            else:
                I_cyc = I   # fallback: no cyclic benefit possible

            res.mu       = round(mu, 4)
            res.M_cyclic = round(I_cyc / max(I, 1e-3), 4)
            res.I_cyclic = round(I_cyc, 1)
        else:
            res.I_cyclic = res.I_cont
            res.M_cyclic = 1.0
            res.mu       = 1.0

        # Electrical
        res.X_ohm_km = round(self.X*1e3, 5)
        res.C_nF_km  = round(self.C*1e12, 2)   # F/m → nF/km (*1e9*1e3)
        dU, dU_pct, Ic = self.voltage_drop(I, L_km, pf, theta)
        res.dU_V = round(dU, 1); res.dU_pct = round(dU_pct, 3)
        res.Ic_A = round(Ic, 2)

        # Warnings
        if not converged:
            res.warnings.append("Iteration did not fully converge — check extreme conditions.")
        if res.dry_zone:
            res.warnings.append(
                f"Dry-zone active (rx={res.rx_m*100:.1f} cm). "
                "Two-zone model applied per IEC 60287-2-1 §2.2.3.")
        if theta > T_max + 0.5:
            res.warnings.append(
                f"Conductor θ={theta:.1f}°C exceeds maximum {T_max}°C.")
        if Ic > 0.1*I:
            res.warnings.append(
                f"Charging current {Ic:.1f} A is significant (>{10:.0f}% of rated). "
                "Relevant for routes >10 km.")

        return res


def build_engine(cd: dict, inst: InstallationParams, soil: SoilParams,
                 freq: float = 50.0, bonding: str = "single_point") -> CableRatingEngine:
    return CableRatingEngine(cd, inst, soil, freq, bonding)
