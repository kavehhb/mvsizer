# Deploy instructions

Use this exact folder structure:

```text
repo-root/
├── app.py
├── cable_data.py
├── cable_engine.py
├── load_analysis.py
├── report_gen.py
├── trench_viz.py
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml
└── ui/
    ├── __init__.py
    ├── components.py
    ├── state.py
    └── theme.py
```

Important:
- Do not place `components.py`, `state.py`, `theme.py`, or `__init__.py` in the repo root.
- They must stay inside the `ui/` folder.
- `config.toml` must stay inside `.streamlit/`.
- Run with `streamlit run app.py`.
