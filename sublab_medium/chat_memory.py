"""Sublab Medium - memory you choose: the `compress` command.

Two scripted runs over the same twelve turns:
  A - never compressed (the `<compress>` turn is skipped entirely)
  B - compressed at the `<compress>` turn into one structured state object
Then five probes are asked after each run. Tokens are the real
`usage.prompt_tokens` reported by the API for every call.

    python -m sublab_medium.chat_memory
    python -m sublab_medium.chat_memory --interactive
"""

import argparse
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import ValidationError, validate
from openai import OpenAI

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SCRIPT_FILE = DATA_DIR / "chat_script.json"
SCHEMA_FILE = DATA_DIR / "memory_state.schema.json"
POLICY_FILE = DATA_DIR / "policy.json"
RECORDS_FILE = DATA_DIR / "records.json"
OUT_FILE = Path(__file__).resolve().parent / "last_run.json"

MODEL_NAME = "gpt-5.6-luna"
COMPRESS_MARKER = "<compress>"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

_policy = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
_records = json.loads(RECORDS_FILE.read_text(encoding="utf-8"))

# The assistant must know the rule and the records, otherwise it cannot answer
# "how much would that come to?" (probe Q-3) whatever the memory strategy is.
SYSTEM_PROMPT = (
    "You are the assistant of a grant office. Help the applicant with their "
    "enquiry and keep track of what they tell you accurately. Answer briefly, "
    "from the record and the rule below; do not accept a claim as fact if the "
    "record says otherwise.\n\nRULE:\n"
    + json.dumps(_policy, ensure_ascii=False)
    + "\n\nRECORDS:\n"
    + json.dumps(_records, ensure_ascii=False)
)

COMPRESS_PROMPT = """The conversation so far must be compressed into ONE JSON object.
Output the JSON object and nothing else (no commentary, no markdown).

Use EXACTLY these keys and no others:
{
  "applicant_id": string or null,
  "topic": string,
  "facts": [string, ...],
  "decisions": [string, ...],
  "constraints": [string, ...],
  "open_questions": [string, ...],
  "language": string
}

Rules:
- applicant_id: the applicant's id if the conversation established it, else null.
- topic: one short phrase saying what the conversation is about.
- facts: things the APPLICANT stated (name, id, income band, documents sent or
  NOT sent, relatives mentioned...). Not things you worked out.
- decisions: decisions or amounts the assistant actually gave. [] if none.
- constraints: conditions on how or when something can happen (a day of the
  week, a deadline, a requirement the applicant set). Keep the exact day/date.
- open_questions: things the applicant asked that have NOT been answered yet.
  Keep enough detail that the question can be answered later.
- language: main language(s) of the conversation, e.g. "en", "kk+en".
- Arrays are [] when empty, never omitted.
- Nothing may be invented: a fact that was never said is not a fact.
- Keep every detail that was said only once (ids, amounts, missing documents,
  days of the week, unanswered questions): it will not be available again."""


# --------------------------------------------------------------------------
# API helpers
# --------------------------------------------------------------------------

def chat(messages: list[dict], **kwargs) -> tuple[str, int]:
    """One model call. Returns (reply text, prompt tokens actually sent)."""
    resp = client.chat.completions.create(model=MODEL_NAME, messages=messages, **kwargs)
    return resp.choices[0].message.content or "", resp.usage.prompt_tokens


def clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


def load_data() -> tuple[dict, dict]:
    script = json.loads(SCRIPT_FILE.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    return script, schema


def compress(history: list[dict], schema: dict) -> tuple[dict | None, int, str | None]:
    """Ask for a structured state. Returns (state or None, tokens of the call, error).

    On any failure the caller keeps the full history: a malformed summary must
    never silently replace the conversation.
    """
    messages = history + [{"role": "user", "content": COMPRESS_PROMPT}]
    raw, tokens = chat(messages, response_format={"type": "json_object"})
    try:
        state = json.loads(clean_json(raw))
        validate(instance=state, schema=schema)
        return state, tokens, None
    except (json.JSONDecodeError, ValidationError) as e:
        return None, tokens, str(e).splitlines()[0]


def history_from_state(state: dict) -> list[dict]:
    """After compression the state is what is sent, not the turns."""
    state_str = json.dumps(state, ensure_ascii=False)
    return [{
        "role": "system",
        "content": SYSTEM_PROMPT + "\n\nSTATE OF THE CONVERSATION SO FAR "
                   "(turns were discarded; rely on this): " + state_str,
    }]


# --------------------------------------------------------------------------
# Scripted run
# --------------------------------------------------------------------------

def probe_passed(reply: str, probe: dict) -> bool:
    r = reply.lower()
    return any(s.lower() in r for s in probe["expect_contains"])


def run_scripted(compress_enabled: bool) -> dict:
    script, schema = load_data()
    turns, probes = script["conversation"], script["probes"]

    label = "B (compressed)" if compress_enabled else "A (never compressed)"
    print(f"\n--- Run {label} ---")

    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    tokens_by_turn: dict[int, int] = {}
    state = None

    for i, text in enumerate(turns, start=1):
        if text.strip() == COMPRESS_MARKER:
            if not compress_enabled:
                print(f"Turn {i:02d}: <compress> skipped")
                continue
            new_state, tok, err = compress(history, schema)
            tokens_by_turn[i] = tok  # the compress call itself costs tokens
            if new_state is None:
                print(f"Turn {i:02d}: COMPRESSION FAILED ({err}); history kept")
            else:
                state = new_state
                history = history_from_state(state)
                print(f"Turn {i:02d}: compressed (call cost {tok} tokens)")
            continue  # the marker is never sent as an applicant turn

        history.append({"role": "user", "content": text})
        reply, tok = chat(history)
        tokens_by_turn[i] = tok
        history.append({"role": "assistant", "content": reply})
        print(f"Turn {i:02d}: {tok} tokens sent")

    print("\nProbes:")
    results = []
    for probe in probes:
        # each probe is asked against the same history; probe turns are not kept
        reply, tok = chat(history + [{"role": "user", "content": probe["question"]}])
        ok = probe_passed(reply, probe)
        results.append({"id": probe["id"], "retrieved": ok, "reply": reply,
                        "tokens": tok, "expect_contains": probe["expect_contains"]})
        print(f"  {probe['id']}: {'RETRIEVED' if ok else 'LOST'}  -> {reply.strip()[:160]!r}")

    return {"tokens_by_turn": tokens_by_turn, "probes": results, "state": state}


def print_tables(a: dict, b: dict) -> None:
    ta, tb = a["tokens_by_turn"], b["tokens_by_turn"]
    print("\n" + "=" * 62)
    print("TOKENS SENT PER CALL")
    print("=" * 62)
    print(f"{'Call':<6} | {'A - never compressed':<22} | {'B - compressed':<16}")
    print("-" * 62)
    for n in range(1, 13):
        print(f"{n:<6} | {str(ta.get(n, '-')):<22} | {str(tb.get(n, '-')):<16}")
    print("-" * 62)
    print(f"{'peak':<6} | {max(ta.values()):<22} | {max(tb.values()):<16}")
    print(f"{'total':<6} | {sum(ta.values()):<22} | {sum(tb.values()):<16}")

    print("\n" + "=" * 62)
    print("PROBES")
    print("=" * 62)
    for pa, pb in zip(a["probes"], b["probes"]):
        print(f"{pa['id']}: A={'retrieved' if pa['retrieved'] else 'LOST':<9} "
              f"B={'retrieved' if pb['retrieved'] else 'LOST'}")
    print(f"retrieved: A {sum(p['retrieved'] for p in a['probes'])}/5, "
          f"B {sum(p['retrieved'] for p in b['probes'])}/5")

    print("\nSTATE PRODUCED BY COMPRESSION:")
    print(json.dumps(b["state"], indent=2, ensure_ascii=False))


# --------------------------------------------------------------------------
# Interactive mode
# --------------------------------------------------------------------------

def run_interactive() -> None:
    _, schema = load_data()
    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    last_tokens = 0

    print("\n=== Interactive grant-office assistant ===")
    print("Commands: compress | tokens | history | exit\n")

    while True:
        try:
            user_input = input("You > ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input:
            continue
        cmd = user_input.lower()

        if cmd in ("exit", "quit"):
            break
        if cmd == "tokens":
            print(f"[last call sent {last_tokens} tokens]\n")
            continue
        if cmd == "history":
            print(json.dumps(history, indent=2, ensure_ascii=False), "\n")
            continue
        if cmd == "compress":
            state, tok, err = compress(history, schema)
            last_tokens = tok
            if state is None:
                print(f"Compression FAILED ({err}). History kept ({len(history)} messages).\n")
            else:
                history = history_from_state(state)
                print("Compressed. State now sent instead of the turns:")
                print(json.dumps(state, indent=2, ensure_ascii=False))
                print(f"[the compress call sent {tok} tokens]\n")
            continue

        history.append({"role": "user", "content": user_input})
        reply, last_tokens = chat(history)
        history.append({"role": "assistant", "content": reply})
        print(f"\nAssistant > {reply}")
        print(f"[tokens sent: {last_tokens}]\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()

    if args.interactive:
        run_interactive()
    else:
        print("=== Sublab Medium: compressed vs uncompressed ===")
        run_a = run_scripted(compress_enabled=False)
        run_b = run_scripted(compress_enabled=True)
        print_tables(run_a, run_b)
        OUT_FILE.write_text(json.dumps({"A": run_a, "B": run_b}, indent=2,
                                       ensure_ascii=False), encoding="utf-8")
        print(f"\n(full replies saved to {OUT_FILE.name})")