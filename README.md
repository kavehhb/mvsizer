# MV Cable Thermal Rating Tool

IEC 60287 / IEC 60853 thermal rating software for Prysmian NA2XS(F)2Y medium-voltage cables.

## Features

- **Full IEC 60287-1-1 engine** — AC resistance (skin + proximity effects), dielectric losses, screen losses (circulating + eddy), iterative Gauss-Seidel convergence
- **IEC 60287-2-1 thermal resistances** — T1 (XLPE), T2 (Cu screen), T3 (PE jacket), T4 self + mutual image method, two-zone soil drying model
- **IEC 60853-2 cyclic rating** — Loss load factor μ, cyclic factor M using wet-soil T4_self only (matches CYMCAP/ELEK published benchmarks)
- **IEC 60949 short-circuit withstand** — conductor and Cu screen adiabatic limits
- **Temperature-corrected voltage drop** — R(θ_actual) not R at 20 °C
- **Complete Prysmian NA2XS(F)2Y library** — 39 cables: 6/10 kV, 12/20 kV, 18/30 kV × 50–1000 mm²
- **Load analysis** — 6 design checks, smart upsizing/downsizing recommendations, risk register
- **CYMCAP-style trench visualisation** — apex-up trefoil, correct scale, dimension annotations
- **PDF report** — full IEC engineering report with trench figure
- **Modern UI** — dark/light mode, responsive layout, clean typography

## Accuracy Validation

Tested against VDE 0276-620 published tables for NA2XS(F)2Y 12/20 kV cables.
Conditions: trefoil, 0.8 m burial, 1.0 K·m/W, 20°C, both-ends bonded, T_crit=50°C.

| Cross-section | VDE reference | Engine result | Deviation |
|---|---|---|---|
| AL 95 mm² | ~200 A | 212 A | +6.2% |
| AL 150 mm² | ~260 A | 268 A | +2.9% |
| AL 240 mm² | ~340 A | 345 A | +1.5% |
| AL 400 mm² | ~435 A | 435 A | +0.0% |
| AL 630 mm² | ~560 A | 558 A | −0.3% |

All results within ±6% of published reference values. Larger cross-sections match almost exactly.

### Cyclic Rating Validation

| Profile | μ | M | Expected (CYMCAP) |
|---|---|---|---|
| Solar PV (PVGIS 52°N June) | 0.232 | 1.39 | 1.28–1.40 ✓ |
| Wind onshore (ERA5 90th pct) | 0.530 | 1.19 | 1.14–1.22 ✓ |
| Flat / continuous | 1.000 | 1.00 | 1.00 ✓ |

## Standards

| Standard | Scope |
|---|---|
| IEC 60287-1-1:2014 | Losses: conductor, dielectric, sheath |
| IEC 60287-2-1:2015 | Thermal resistances & soil models |
| IEC 60853-2:1989 | Cyclic & emergency rating |
| IEC 60502-2:2014 | XLPE insulation thickness |
| IEC 60228:2004 | Conductor DC resistances |
| IEC 60949:1988 | Short-circuit withstand |
| VDE 0276-1000 | German network practice |

## Setup

### Requirements

- Python 3.9+
- pip

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## File Structure

```
mv-cable-rating/
├── app.py            # Streamlit UI — modern design, dark/light mode
├── cable_engine.py   # IEC 60287 / 60853 calculation engine
├── cable_data.py     # Prysmian NA2XS(F)2Y cable library + load profiles
├── load_analysis.py  # Load adequacy checks, recommendations, risk register
├── trench_viz.py     # CYMCAP-style trench cross-section (matplotlib)
├── report_gen.py     # PDF report generator (ReportLab)
├── requirements.txt
└── README.md
```

## Workflow

1. Select cable voltage and cross-section from the Prysmian library
2. Configure installation: burial depth, formation, number of circuits
3. Set soil parameters: wet/dry thermal resistivity, ambient temperature
4. Choose a load profile (flat, residential, industrial, solar PV, wind)
5. Enter load parameters: apparent power, power factor, cable length, fault current
6. Click **▶ CALCULATE**
7. Review results across six tabs
8. Export PDF report

## Limitations

- Analytical engine only — does not replace FEA for complex duct banks, buried crossings, or non-uniform soils
- Emergency rating uses simplified IEC 60287 at θ_e = 105 °C (conservative)
- Mutual heating uses the IEC image method; for non-uniform burial depths use FEA
- Validate against CYMCAP or ELEK for final designs

## License

MIT
