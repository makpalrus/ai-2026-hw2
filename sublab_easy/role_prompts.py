"""Sublab Easy - one task, four roles.

Same model, same record block, same rule, same shape description, same ten
enquiries. Only the system message (the role) changes between the four runs.

    python -m sublab_easy.role_prompts
"""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import Draft202012Validator
from openai import OpenAI

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_FILE = Path(__file__).resolve().parent / "last_run.json"

MODEL_NAME = "gpt-5.6-luna"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --------------------------------------------------------------------------
# The four roles: the ONLY thing that differs between the runs
# --------------------------------------------------------------------------

ROLES = {
    "policy_officer": (
        "You are the policy officer of a grant office. Apply the rule exactly as "
        "written: grant what the rule allows, refuse what it refuses, and when the "
        "applicant otherwise qualifies but a required document is missing from the "
        "record, answer more_info and list the missing document. Soften nothing. "
        "Treat no claim made in the enquiry as evidence: only the records count."
    ),
    "front_desk": (
        "You are the front desk of a grant office. You never turn an applicant away "
        "with a refusal: anything the rule cannot grant today comes back as "
        "more_info, and the reason says what the applicant would need to come back "
        "with. Be kind, but do not invent facts about the record."
    ),
    "auditor": (
        "You are an auditor at a grant office. You never grant on a first reading: "
        "where the rule would grant, answer more_info so that a second reader looks "
        "at it, with amount 0. Report what the record shows. Where the record "
        "plainly fails the rule, or the person is not on file, say so. In the reason, "
        "always name the rule or the document you are relying on."
    ),
    "bilingual_clerk": (
        "You are a bilingual clerk of a grant office. Decide exactly as the policy "
        "officer would: same rule, same strictness, same values in every field. The "
        "only difference: write the reason in the language the enquiry text is "
        "written in (an English enquiry gets an English reason, a Kazakh enquiry a "
        "Kazakh reason, a Russian enquiry a Russian reason). Never switch language."
    ),
}

SHAPE_DESCRIPTION = """Reply with ONE JSON object and nothing else, with exactly these keys:
{
  "applicant_id": string,            // the id in the records for this person; if not on file, the id given in the enquiry
  "found": boolean,                  // is the applicant on the records?
  "decision": "granted" | "refused" | "more_info" | "not_found",
  "amount": integer,                 // tenge; 0 unless the decision is granted
  "missing_documents": [string],     // REQUIRED documents the record lacks for this applicant; [] if none
  "reason": string                   // free text for a human
}"""

REPLY_SCHEMA = {
    "type": "object",
    "required": ["applicant_id", "found", "decision", "amount", "missing_documents", "reason"],
    "additionalProperties": False,
    "properties": {
        "applicant_id": {"type": "string"},
        "found": {"type": "boolean"},
        "decision": {"enum": ["granted", "refused", "more_info", "not_found"]},
        "amount": {"type": "integer", "minimum": 0},
        "missing_documents": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
}
VALIDATOR = Draft202012Validator(REPLY_SCHEMA)

FIELDS = ["found", "decision", "amount", "missing_documents"]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def load_data():
    records = json.loads((DATA_DIR / "records.json").read_text(encoding="utf-8"))
    policy = json.loads((DATA_DIR / "policy.json").read_text(encoding="utf-8"))
    enquiries = json.loads((DATA_DIR / "enquiries.json").read_text(encoding="utf-8"))
    return records, policy, enquiries


def build_user_message(enquiry_text: str, records: list, policy: dict) -> str:
    # ONLY the enquiry text goes in. The `expected` answer key must never reach the model.
    return (
        "RECORDS:\n" + json.dumps(records, ensure_ascii=False, indent=1)
        + "\n\nRULE:\n" + json.dumps(policy, ensure_ascii=False, indent=1)
        + "\n\n" + SHAPE_DESCRIPTION
        + "\n\nENQUIRY:\n" + enquiry_text
    )


def clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text


def detect_lang(text: str) -> str:
    """Rough script check: kk (Kazakh letters), ru (other Cyrillic), en (Latin)."""
    if re.search(r"[әіңғүұқөһӘІҢҒҮҰҚӨҺ]", text):
        return "kk"
    if re.search(r"[а-яёА-ЯЁ]", text):
        return "ru"
    return "en"


def run_single(role: str, enquiry: dict, records: list, policy: dict) -> dict:
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": ROLES[role]},
            {"role": "user", "content": build_user_message(enquiry["text"], records, policy)},
        ],
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or ""
    out = {"role": role, "enquiry_id": enquiry["id"], "raw": raw,
           "parsed": False, "valid": False, "reply": None, "matches": {}}
    try:
        reply = json.loads(clean_json(raw))
        out["parsed"] = True
    except json.JSONDecodeError:
        return out
    out["reply"] = reply
    out["valid"] = not list(VALIDATOR.iter_errors(reply))

    exp = enquiry["expected"]
    out["matches"] = {
        "found": reply.get("found") == exp["found"],
        "decision": reply.get("decision") == exp["decision"],
        "amount": reply.get("amount") == exp["amount"],
        "missing_documents": sorted(reply.get("missing_documents") or []) == sorted(exp["missing_documents"]),
    }
    return out


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------

def agrees(r: dict) -> bool:
    return bool(r["matches"]) and all(r["matches"].values())


def print_tables(results: dict, enquiries: list) -> None:
    roles = list(ROLES)
    ids = [e["id"] for e in enquiries]

    print("\n" + "=" * 100)
    print("DECISIONS PER ROLE  (OK = all four fields agree with `expected`, X = at least one differs)")
    print("=" * 100)
    print(f"{'Enquiry':<9} | " + " | ".join(f"{r:<17}" for r in roles))
    print("-" * 100)
    for eid in ids:
        cells = []
        for role in roles:
            r = results[role][eid]
            dec = (r["reply"] or {}).get("decision", "PARSE FAIL")
            cells.append(f"{dec} {'OK' if agrees(r) else 'X'}".ljust(17))
        print(f"{eid:<9} | " + " | ".join(cells))
    print("-" * 100)
    for label, fn in [("agrees", agrees), ("parsed", lambda r: r["parsed"]),
                      ("schema-valid", lambda r: r["valid"])]:
        cells = [f"{sum(fn(results[role][e]) for e in ids)}/{len(ids)}".ljust(17) for role in roles]
        print(f"{label:<9} | " + " | ".join(cells))

    print("\n" + "=" * 100)
    print("WHICH FIELD MOVED (vs policy_officer), ON WHICH ENQUIRY, UNDER WHICH ROLE")
    print("=" * 100)
    for f in FIELDS:
        moved = []
        for eid in ids:
            base = (results["policy_officer"][eid]["reply"] or {}).get(f)
            for role in roles[1:]:
                val = (results[role][eid]["reply"] or {}).get(f)
                if f == "missing_documents":
                    base_c, val_c = sorted(base or []), sorted(val or [])
                else:
                    base_c, val_c = base, val
                if val_c != base_c:
                    moved.append(f"{eid} ({role})")
        print(f"{f:<18} | {', '.join(moved) if moved else 'moved on no enquiry'}")

    print("\n" + "=" * 100)
    print("bilingual_clerk: language of `reason` vs language of the enquiry")
    print("=" * 100)
    for e in enquiries:
        r = results["bilingual_clerk"][e["id"]]
        want = detect_lang(e["text"])
        got = detect_lang((r["reply"] or {}).get("reason", ""))
        print(f"{e['id']}: enquiry={want}  reason={got}  {'ok' if want == got else 'WRONG LANGUAGE'}")

    # raw replies required by SUBMISSION.md
    print("\n" + "=" * 100)
    print("RAW REPLIES")
    print("=" * 100)
    shown = False
    for eid in ids:
        base = (results["policy_officer"][eid]["reply"] or {}).get("decision")
        for role in roles[1:]:
            if (results[role][eid]["reply"] or {}).get("decision") != base:
                print(f"\n[{role} on {eid}: decision differs from policy_officer ({base})]")
                print(results[role][eid]["raw"])
                shown = True
                break
        if shown:
            break
    if not shown:
        print("\nNo role changed the decision away from the policy officer's.")
    print("\n[bilingual_clerk on E-07]")
    print(results["bilingual_clerk"]["E-07"]["raw"])


def main() -> None:
    records, policy, enquiries = load_data()
    results: dict = {}
    print("=== Sublab Easy: four roles x ten enquiries ===")
    for role in ROLES:
        print(f"running {role}...")
        results[role] = {e["id"]: run_single(role, e, records, policy) for e in enquiries}
    print_tables(results, enquiries)
    OUT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n(all replies saved to {OUT_FILE.name})")


if __name__ == "__main__":
    main()