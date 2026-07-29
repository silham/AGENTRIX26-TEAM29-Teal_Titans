"""Pre-translate every FIXED citizen-facing string, and export them for review.

Two reasons this exists rather than letting the cache fill on demand:

1. **Latency.** These strings are deterministic and finite — the procedure
   JSONs, requirement names, eligibility labels and lock reasons. Warming them
   means the first Sinhala citizen gets an instant page instead of waiting on
   the model.
2. **Accuracy.** Sri Lankan government terminology has canonical Sinhala and
   Tamil forms, and sending a citizen to the wrong office is exactly what this
   product exists to prevent. Machine output should be reviewed by a speaker
   before it reaches the public, and `--export` produces the file to review.

Usage:
    python -m scripts.seed_translations                 # translate si + ta
    python -m scripts.seed_translations --lang si       # one language
    python -m scripts.seed_translations --export out.tsv
    python -m scripts.seed_translations --import out.tsv  # mark rows human-reviewed

Corrected rows are stored with source='human' and are never overwritten by a
later machine run.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Allow `python scripts/seed_translations.py` as well as `-m scripts...`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.db.models import Translation  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.graph.nodes import checklist as checklist_node  # noqa: E402
from app.graph.nodes import eligibility as eligibility_node  # noqa: E402
from app.i18n import translator  # noqa: E402
from app.rag import rules  # noqa: E402


def collect_source_strings() -> list[str]:
    """Every fixed English string a citizen can see, deduped.

    Deliberately excludes anything an LLM generates at runtime (custom plan
    steps, eligibility questions for custom goals) — those vary per case and
    are translated on demand.
    """
    out: list[str] = []

    # 1. The procedure rules layer: service names, step titles/descriptions,
    #    and the "why is this locked" reasons.
    for proc in rules.load_procedures().values():
        if isinstance(proc.get("name"), str):
            out.append(proc["name"])
        for step in proc.get("steps", []) or []:
            for key in ("title", "description"):
                if isinstance(step.get(key), str):
                    out.append(step[key])
        for cond in proc.get("dependency_conditions", []) or []:
            if isinstance(cond.get("reason"), str):
                out.append(cond["reason"])

    # 2. Requirement display names (the Requirements tab).
    out.extend(checklist_node._REQ_NAMES.values())

    # 3. Lock reasons composed in the checklist node.
    out.extend(
        [
            "Blocked by a prerequisite step.",
            "Not eligible for this service.",
        ]
    )

    # 4. Eligibility: the template questions and every reason string the rules
    #    can actually produce, rendered against the real rules so we translate
    #    the exact sentences citizens see rather than a guess at them.
    for field in eligibility_node._FIELD_LABELS:
        out.append(eligibility_node._template_question(field))
    out.append("Other")
    for proc in rules.load_procedures().values():
        for rule in proc.get("eligibility_rules", []) or []:
            field = rule.get("field")
            if field:
                out.append(eligibility_node._rule_reason(rule, field))

    # 5. Prerequisite phrasing from the dependency node.
    for sid in rules.load_procedures():
        out.append(f"{rules.name(sid)} required first.")

    seen: set[str] = set()
    deduped: list[str] = []
    for text in out:
        if isinstance(text, str) and text.strip() and text not in seen:
            seen.add(text)
            deduped.append(text)
    return deduped


def seed(langs: list[str]) -> None:
    texts = collect_source_strings()
    print(f"{len(texts)} distinct source strings")
    for lang in langs:
        before = _count(lang)
        translator.translate_many(texts, lang)
        after = _count(lang)
        print(f"  {lang}: {after} cached (+{after - before})")


def _count(lang: str) -> int:
    with SessionLocal() as db:
        return len(
            db.execute(
                select(Translation.source_hash).where(
                    Translation.lang == lang,
                    Translation.prompt_version == translator.PROMPT_VERSION,
                )
            ).all()
        )


def export(path: Path, langs: list[str]) -> None:
    """Dump rows as TSV for a speaker to correct.

    Columns: lang, source(machine|human), english, translation. Edit the
    translation column, leave everything else alone, then --import.
    """
    with SessionLocal() as db:
        rows = db.execute(
            select(
                Translation.lang,
                Translation.source,
                Translation.source_text,
                Translation.translated_text,
            )
            .where(
                Translation.lang.in_(langs),
                Translation.prompt_version == translator.PROMPT_VERSION,
            )
            .order_by(Translation.lang, Translation.source_text)
        ).all()

    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["lang", "source", "english", "translation"])
        writer.writerows(rows)
    print(f"exported {len(rows)} rows to {path}")


def import_reviewed(path: Path) -> None:
    """Apply a corrected TSV, marking every applied row source='human'.

    A human row is authoritative: `translate_many` inserts with
    ON CONFLICT DO NOTHING, so it will never be overwritten by a later machine
    run — the review survives re-seeding.
    """
    updated = 0
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        with SessionLocal() as db:
            for row in reader:
                lang, english = row.get("lang"), row.get("english")
                translated = (row.get("translation") or "").strip()
                if not (lang and english and translated):
                    continue
                source_hash = translator._hash(english)
                existing = db.get(
                    Translation, (source_hash, lang, translator.PROMPT_VERSION)
                )
                if existing is None:
                    db.add(
                        Translation(
                            source_hash=source_hash,
                            lang=lang,
                            prompt_version=translator.PROMPT_VERSION,
                            source_text=english,
                            translated_text=translated,
                            source="human",
                        )
                    )
                    updated += 1
                elif existing.translated_text != translated or existing.source != "human":
                    existing.translated_text = translated
                    existing.source = "human"
                    updated += 1
            db.commit()
    print(f"marked {updated} row(s) as human-reviewed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", action="append", choices=["si", "ta"])
    parser.add_argument("--export", type=Path, help="write a TSV for review")
    parser.add_argument("--import", dest="import_path", type=Path, help="apply a reviewed TSV")
    args = parser.parse_args()

    langs = args.lang or ["si", "ta"]

    if args.import_path:
        import_reviewed(args.import_path)
        return
    if args.export:
        export(args.export, langs)
        return
    seed(langs)


if __name__ == "__main__":
    main()
