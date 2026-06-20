"""Owner: M3. Load + query the deterministic rules layer (data/procedures/*.json)."""
import json
from pathlib import Path

PROCEDURES_DIR = Path(__file__).resolve().parents[2] / "data" / "procedures"


def load_procedures() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for f in PROCEDURES_DIR.glob("*.json"):
        data = json.loads(f.read_text())
        out[data["id"]] = data
    return out


# TODO(M3): requirements(service), depends_on(service), eligibility_rules(service), steps(service).
