"""Government terminology control for the translator.

Two DIFFERENT things, deliberately kept apart:

* ``DO_NOT_TRANSLATE`` — tokens that must survive byte-for-byte. Form codes,
  department acronyms used as identifiers. A citizen searching for "K-35-A" at
  a counter needs that exact string.

* ``GLOSSARY`` — terms that must become the OFFICIAL localized form. Leaving
  "Divisional Secretariat" in Latin script inside a Sinhala sentence is the
  half-translated output that makes a government service look untrustworthy,
  and a citizen asking for it by the English name at a rural office may not be
  understood.

Getting this wrong is not a cosmetic problem: sending someone to the wrong
office is the failure mode this whole product exists to prevent.
"""
from __future__ import annotations

SUPPORTED_LANGUAGES: frozenset[str] = frozenset({"en", "si", "ta"})
DEFAULT_LANGUAGE = "en"

LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "si": "Sinhala",
    "ta": "Tamil",
}

# Kept verbatim in every language.
DO_NOT_TRANSLATE: frozenset[str] = frozenset(
    {
        "HelpLK",
        "K-35-A",       # passport application form
        "RG-D-01",      # duplicate NIC application form
        "B-11",         # birth certificate application form
        "NIC",          # only as a bare code; the full term is in GLOSSARY
        "eNIC",
        "RMV",          # Registrar of Motor Vehicles
        "DRP",          # Department for Registration of Persons
        "TIN",
        "EPF",
        "ETF",
        "VAT",
    }
)

# English → official localized term.
GLOSSARY: dict[str, dict[str, str]] = {
    "si": {
        "National Identity Card": "ජාතික හැඳුනුම්පත",
        "Passport": "විදේශ ගමන් බලපත්‍රය",
        "Birth Certificate": "උප්පැන්න සහතිකය",
        "Driving Licence": "රියදුරු බලපත්‍රය",
        "Marriage Certificate": "විවාහ සහතිකය",
        "Death Certificate": "මරණ සහතිකය",
        "Police Report": "පොලිස් වාර්තාව",
        "Grama Niladhari": "ග්‍රාම නිලධාරී",
        "Divisional Secretariat": "ප්‍රාදේශීය ලේකම් කාර්යාලය",
        "District Secretariat": "දිස්ත්‍රික් ලේකම් කාර්යාලය",
        "Department of Immigration and Emigration": "ආගමන විගමන දෙපාර්තමේන්තුව",
        "Registrar General's Department": "රෙජිස්ට්‍රාර් ජනරාල් දෙපාර්තමේන්තුව",
        "Department for Registration of Persons": "පුද්ගලයන් ලියාපදිංචි කිරීමේ දෙපාර්තමේන්තුව",
        "Medical Certificate": "වෛද්‍ය සහතිකය",
        "Application Form": "අයදුම් පත්‍රය",
        "Affidavit": "දිවුරුම් ප්‍රකාශය",
    },
    "ta": {
        "National Identity Card": "தேசிய அடையாள அட்டை",
        "Passport": "கடவுச்சீட்டு",
        "Birth Certificate": "பிறப்புச் சான்றிதழ்",
        # Sri Lankan Tamil, not the Indian "ஓட்டுநர் உரிமம்".
        "Driving Licence": "சாரதி அனுமதிப்பத்திரம்",
        "Marriage Certificate": "திருமணச் சான்றிதழ்",
        "Death Certificate": "இறப்புச் சான்றிதழ்",
        "Police Report": "பொலிஸ் அறிக்கை",
        "Grama Niladhari": "கிராம சேவகர்",
        "Divisional Secretariat": "பிரதேச செயலகம்",
        "District Secretariat": "மாவட்ட செயலகம்",
        "Department of Immigration and Emigration": "குடிவரவு குடியகல்வு திணைக்களம்",
        "Registrar General's Department": "பதிவாளர் நாயகம் திணைக்களம்",
        "Department for Registration of Persons": "ஆட்பதிவு திணைக்களம்",
        "Medical Certificate": "மருத்துவச் சான்றிதழ்",
        "Application Form": "விண்ணப்பப் படிவம்",
        "Affidavit": "பிரமாணப் பத்திரம்",
    },
}


def glossary_for(lang: str) -> dict[str, str]:
    return GLOSSARY.get(lang, {})


def glossary_prompt_block(lang: str) -> str:
    """The glossary and do-not-translate list, formatted for a system prompt.

    Only terms for the requested language are included — sending the Tamil
    table while translating to Sinhala wastes tokens and invites cross-talk.
    """
    lines: list[str] = []
    terms = glossary_for(lang)
    if terms:
        lines.append("Use EXACTLY these official translations:")
        lines.extend(f"  {en} = {local}" for en, local in terms.items())
    if DO_NOT_TRANSLATE:
        lines.append(
            "Keep these EXACTLY as written, unchanged: "
            + ", ".join(sorted(DO_NOT_TRANSLATE))
        )
    return "\n".join(lines)
