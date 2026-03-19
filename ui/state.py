"""Session state helpers."""
from cable_data import LOAD_PROFILES


def init_state(session_state) -> None:
    defaults = {
        "dark": True,
        "res": None,
        "ar": None,
        "eng": None,
        "cdid": None,
        "profile_key": "residential",
        "profile_source": "Standard",
        "load_profile": LOAD_PROFILES["residential"],
        "project_name": "MV Cable Study",
        "engineer_name": "",
        "project_ref": "",
        "error": None,
    }
    for key, value in defaults.items():
        if key not in session_state:
            session_state[key] = value
