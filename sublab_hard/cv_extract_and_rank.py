"""Sublab Hard - stories in, CVs out, the best candidate by code.

1. Extract a structured CV from each story (rules are in the prompt).
2. Ask the model for three 0-5 scores per candidate and NOTHING else to compute.
3. The code computes the weighted total and names the winner.
4. In a separate call, ask the model in prose who should win.

    python -m sublab_hard.cv_extract_and_rank
"""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import ValidationError, validate
from openai import OpenAI

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CANDIDATES_DIR = DATA_DIR / "candidates"
RUBRIC_FILE = DATA_DIR / "candidate_rubric.json"
OUT_FILE = Path(__file__).resolve().parent / "last_run.json"

MODEL_NAME = "gpt-5.6-luna"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------

EXTRACTION_SYSTEM_PROMPT = """You extract a structured CV record from ONE written scholarship application.
The story may be in English or Kazakh. Reply with ONE JSON object and nothing else.

RULES (follow all of them):
1. A fact the story does not state is null. Never estimate, infer or fill in.
   No GPA in the story means gpa_original and gpa_4_scale are null - not a
   GPA guessed from the degree, the university or the tone of the story.
2. A GPA on another scale is converted to a 4.0 scale:
   gpa_4_scale = gpa_original / gpa_scale_max * 4. Record the number the story
   gave in gpa_original and the maximum of its scale in gpa_scale_max
   (a story on the 4.0 scale has gpa_scale_max 4.0).
3. A paper is published ONLY when the story says it is published or accepted.
   "submitted", "under review", "in preparation", "in press", "planned" are NOT
   published: list each in unpublished_papers with its status, and do NOT count
   it in published_count. Posters and talks are not papers.
4. Contradictions are not resolved and not averaged. If the story gives two
   different values for the same fact (two GPAs, two graduation years...), that
   field is null and the contradiction is described in ambiguities.
5. Experience is counted in MONTHS, not jobs. Overlapping periods count once.
   A period with no dates and no stated months is not countable: do not count
   it, describe it in experience_notes. Use months the story states, or
   months that follow directly from stated start and end dates. If the story
   only gives a vague amount ("about", "roughly") say so in experience_notes.
6. For every field you fill with a non-null value, put a short verbatim quote
   from the story in evidence[<field name>]. No quote, no value.

JSON shape (all keys required):
{
  "full_name": string or null,
  "degree": string or null,
  "graduation_year": integer or null,
  "gpa_original": number or null,
  "gpa_scale_max": number or null,
  "gpa_4_scale": number or null,
  "languages": [string],
  "published_count": integer,
  "unpublished_papers": [{"description": string, "status": string}],
  "experience_months": integer or null,
  "experience_notes": string or null,
  "ambiguities": [string],
  "evidence": {"<field name>": "<verbatim quote>"}
}"""

SCORING_SYSTEM_PROMPT = """You are a member of a scholarship committee.
You receive one candidate's structured record and the rubric. Give a score from
0 to 5 (numbers, decimals allowed) for each of the three criteria, using only
the rubric's definitions, the counting rules, and the record.

Rules:
- Score only what the record states. A null field is treated as NOT STATED
  (for academic: no GPA means 0, exactly as the counting rule says). This
  applies equally to a field that is null because the story contradicted itself.
- published_count and experience_months in the record were already counted
  under the counting rules (published peer-reviewed outputs only; countable
  months only). Use them as given: do not recount, and do not lower a score
  because an evidence quote is shortened or mentions only one of the outputs.
- Do NOT compute a total and do NOT rank. Only the three scores.

Reply with ONE JSON object and nothing else:
{"academic": number, "research": number, "experience": number, "note": string}
("note" is one short sentence saying what the scores rest on.)"""

PROSE_SYSTEM_PROMPT = """You are the head of a scholarship committee with one funded place.
Below are the rubric and the six candidates' written applications. Say in prose
which candidate should win. Name the winner by its id (story-01 ... story-06)
and explain in 2-3 sentences."""


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

CV_SCHEMA = {
    "type": "object",
    "required": ["full_name", "degree", "graduation_year", "gpa_original",
                 "gpa_scale_max", "gpa_4_scale", "languages", "published_count",
                 "unpublished_papers", "experience_months", "experience_notes",
                 "ambiguities", "evidence"],
    "properties": {
        "full_name": {"type": ["string", "null"]},
        "degree": {"type": ["string", "null"]},
        "graduation_year": {"type": ["integer", "null"]},
        "gpa_original": {"type": ["number", "null"]},
        "gpa_scale_max": {"type": ["number", "null"]},
        "gpa_4_scale": {"type": ["number", "null"]},
        "languages": {"type": "array", "items": {"type": "string"}},
        "published_count": {"type": "integer", "minimum": 0},
        "unpublished_papers": {
            "type": "array",
            "items": {"type": "object", "required": ["description", "status"]},
        },
        "experience_months": {"type": ["integer", "null"], "minimum": 0},
        "experience_notes": {"type": ["string", "null"]},
        "ambiguities": {"type": "array", "items": {"type": "string"}},
        "evidence": {"type": "object"},
    },
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def ask(system: str, user: str, json_mode: bool) -> str:
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        **kwargs,
    )
    return resp.choices[0].message.content or ""


def clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def extract_cv(candidate_id: str, story: str) -> dict:
    """Returns {'cv', 'parsed', 'valid', 'error', 'code_notes'}."""
    raw = ask(EXTRACTION_SYSTEM_PROMPT, f"STORY:\n{story}", json_mode=True)
    res = {"cv": None, "parsed": False, "valid": False, "error": None,
           "code_notes": [], "raw": raw}
    try:
        cv = json.loads(clean_json(raw))
        res["parsed"] = True
        validate(instance=cv, schema=CV_SCHEMA)
        res["valid"] = True
    except json.JSONDecodeError as e:
        res["error"] = f"parse: {e}"
        return res
    except ValidationError as e:
        res["error"] = f"schema: {e.message}"
        res["cv"] = cv
        return res

    cv["candidate_id"] = candidate_id  # decided by code: stories carry no id

    # --- the code decides where the model might guess -----------------------
    # No original GPA in the story -> no GPA at all, whatever the model wrote.
    if cv["gpa_original"] is None and cv["gpa_4_scale"] is not None:
        res["code_notes"].append(f"gpa_4_scale {cv['gpa_4_scale']} set to null (no GPA stated)")
        cv["gpa_4_scale"] = None
    # Conversion is arithmetic: the code does it and overrides the model if they differ.
    if cv["gpa_original"] is not None and cv["gpa_scale_max"]:
        computed = round(cv["gpa_original"] / cv["gpa_scale_max"] * 4, 2)
        if cv["gpa_4_scale"] is None or abs(cv["gpa_4_scale"] - computed) > 0.02:
            res["code_notes"].append(
                f"gpa_4_scale {cv['gpa_4_scale']} replaced by computed {computed}")
            cv["gpa_4_scale"] = computed
    res["cv"] = cv
    return res


def load_rubric() -> tuple[dict, dict]:
    rubric = json.loads(RUBRIC_FILE.read_text(encoding="utf-8"))
    weights = {c["id"]: c["weight"] for c in rubric["criteria"]}
    return rubric, weights


def valid_scores(obj, weights: dict) -> bool:
    return (isinstance(obj, dict)
            and all(k in obj for k in weights)
            and all(isinstance(obj[k], (int, float)) and not isinstance(obj[k], bool)
                    and 0 <= obj[k] <= 5 for k in weights))


def score_candidate(cv: dict, rubric: dict, weights: dict) -> dict:
    # weights and the ranking rule are NOT sent: the model must not compute a total
    rubric_for_model = {
        "criteria": [{k: v for k, v in c.items() if k != "weight"} for c in rubric["criteria"]],
        "counting_rules": rubric["counting_rules"],
    }
    user = ("CANDIDATE RECORD:\n" + json.dumps(cv, indent=2, ensure_ascii=False)
            + "\n\nRUBRIC:\n" + json.dumps(rubric_for_model, indent=2, ensure_ascii=False))
    raw = ask(SCORING_SYSTEM_PROMPT, user, json_mode=True)
    try:
        obj = json.loads(clean_json(raw))
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"parse: {e}", "raw": raw}
    if not valid_scores(obj, weights):
        return {"ok": False, "error": "scores missing or outside 0-5", "raw": raw}
    return {"ok": True, "scores": {k: obj[k] for k in weights}, "note": obj.get("note")}


def weighted_total(scores: dict, weights: dict) -> float:
    """Computed by code, never by the model. Rubric rule: 0.5/0.3/0.2, 2 decimals."""
    return round(sum(weights[k] * scores[k] for k in weights), 2)


def traps_hit(cv: dict) -> list[str]:
    hit = []
    if cv["gpa_original"] is None and not any("gpa" in a.lower() for a in cv["ambiguities"]):
        hit.append("no GPA")
    if cv["gpa_scale_max"] not in (None, 4, 4.0):
        hit.append(f"other scale (/{cv['gpa_scale_max']:g})")
    if cv["unpublished_papers"]:
        hit.append(f"{len(cv['unpublished_papers'])} unpublished")
    if cv["ambiguities"]:
        hit.append("ambiguity flagged (check text)")
    return hit


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def run() -> None:
    rubric, weights = load_rubric()
    story_files = sorted(CANDIDATES_DIR.glob("story-*.md"))
    stories = {f.stem: f.read_text(encoding="utf-8") for f in story_files}

    # ---- Part 1: extraction ----------------------------------------------
    print("=== Part 1: extraction ===")
    extractions = {}
    print(f"{'Story':<9} | {'Parsed':<6} | {'Valid':<5} | {'Null fields':<48} | Traps hit")
    print("-" * 110)
    for cid, text in stories.items():
        res = extract_cv(cid, text)
        extractions[cid] = res
        if res["valid"]:
            cv = res["cv"]
            nulls = [k for k in ("degree", "graduation_year", "gpa_original", "gpa_4_scale",
                                 "experience_months") if cv[k] is None]
            traps = ", ".join(traps_hit(cv)) or "-"
            print(f"{cid:<9} | {'yes':<6} | {'yes':<5} | {', '.join(nulls) or '-':<48} | {traps}")
            for note in res["code_notes"]:
                print(f"          code: {note}")
        else:
            print(f"{cid:<9} | {'yes' if res['parsed'] else 'no':<6} | {'no':<5} | "
                  f"{'-':<48} | FAILED: {res['error']}")

    if "story-06" in extractions and extractions["story-06"]["valid"]:
        print("\nExtraction for story-06:")
        print(json.dumps(extractions["story-06"]["cv"], indent=2, ensure_ascii=False))

    # ---- Part 2: scores (model) and totals (code) --------------------------
    print("\n=== Part 2: scores by the model, totals by the code ===")
    rows, invalid = [], []
    for cid, res in extractions.items():
        if not res["valid"]:
            invalid.append((cid, f"extraction failed: {res['error']}"))
            continue
        sc = score_candidate(res["cv"], rubric, weights)
        if not sc["ok"]:
            invalid.append((cid, f"scoring failed: {sc['error']}"))
            continue
        rows.append({"candidate_id": cid, "full_name": res["cv"]["full_name"],
                     "scores": sc["scores"], "note": sc["note"],
                     "total": weighted_total(sc["scores"], weights)})

    rows.sort(key=lambda r: r["total"], reverse=True)
    print(f"{'Rank':<5} | {'Candidate':<9} | {'academic':<8} | {'research':<8} | "
          f"{'experience':<10} | {'total (code)':<12}")
    print("-" * 70)
    for i, r in enumerate(rows, 1):
        s = r["scores"]
        print(f"{i:<5} | {r['candidate_id']:<9} | {s['academic']:<8} | {s['research']:<8} | "
              f"{s['experience']:<10} | {r['total']:<12}")
    for cid, why in invalid:
        print(f"  EXCLUDED {cid}: {why}")

    code_winner = rows[0]["candidate_id"] if rows else None
    if rows:
        print(f"\nWINNER COMPUTED BY CODE: {code_winner} ({rows[0]['full_name']}), "
              f"total {rows[0]['total']}")
        if len(rows) > 1:
            gap = round(rows[0]["total"] - rows[1]["total"], 2)
            print(f"Gap to second place ({rows[1]['candidate_id']}): {gap}"
                  + ("  <- within 0.05" if gap <= 0.05 else ""))

    # ---- Prose ranking: separate call, no scores shown ---------------------
    print("\n=== Prose ranking (separate call, independent of the scores) ===")
    rubric_text = json.dumps({"criteria": rubric["criteria"],
                              "counting_rules": rubric["counting_rules"]},
                             indent=2, ensure_ascii=False)
    prose_input = "RUBRIC:\n" + rubric_text + "\n\n" + "\n\n".join(
        f"--- {cid} ---\n{text}" for cid, text in stories.items())
    prose = ask(PROSE_SYSTEM_PROMPT, prose_input, json_mode=False)
    print(prose)

    m = re.search(r"story-0\d", prose)
    prose_winner = m.group(0) if m else None
    print(f"\nProse winner: {prose_winner} | code winner: {code_winner} | "
          f"{'AGREE' if prose_winner == code_winner else 'DISAGREE'}")

    OUT_FILE.write_text(json.dumps(
        {"extractions": {k: {kk: vv for kk, vv in v.items()} for k, v in extractions.items()},
         "ranking": rows, "excluded": invalid, "prose": prose},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n(everything saved to {OUT_FILE.name})")


if __name__ == "__main__":
    run()