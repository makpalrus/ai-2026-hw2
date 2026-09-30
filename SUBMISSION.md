# HW2 submission

**Name:** Ruskulbek Makpal
**Student ID:** S23067710
**Group:** 9

## AI tool disclosure

<!-- TODO: check this is accurate and edit it in your own words. -->

> I used an AI assistant (Claude, Anthropic) to write and debug the three programs
> (`role_prompts.py`, `chat_memory.py`, `cv_extract_and_rank.py`) and to help draft
> their prompts: the four role paragraphs, the compress prompt, and the extraction
> and scoring prompts. All tables, numbers and transcripts below come from my own
> runs of those programs (`last_run.json` in each sublab folder). The written
> answers are my own analysis of those runs.

---

## Sublab Easy — one task, four roles

Model: `gpt-5.6-luna`. The user message (records, rule, shape description, enquiry
text) is identical for all four roles; only the system message changes. The
`expected` field is never sent to the model.

### Decisions per role

`✓` = all four structured fields agree with `expected`; `✗` = at least one differs.

| Enquiry | policy_officer | front_desk | auditor | bilingual_clerk |
|---|---|---|---|---|
| E-01 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-02 | more_info ✓ | more_info ✓ | refused ✗ | more_info ✓ |
| E-03 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-04 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-05 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-06 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-07 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-08 | not_found ✓ | not_found ✓ | not_found ✓ | not_found ✓ |
| E-09 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-10 | more_info ✓ | more_info ✓ | refused ✗ | refused ✗ |
| **agrees with `expected`** | 10/10 | 7/10 | 4/10 | 9/10 |
| **parsed** | 10/10 | 10/10 | 10/10 | 10/10 |
| **schema-valid** | 10/10 | 10/10 | 10/10 | 10/10 |

### Which field moved, on which enquiry, under which role

Compared with the policy officer's reply.

| Field | Enquiries that moved | Role(s) that moved it |
|---|---|---|
| `found` | none (moved on no enquiry) | none |
| `decision` | E-01, E-02, E-03, E-04, E-05, E-06, E-07, E-09, E-10 | auditor (E-01, E-02, E-05, E-06, E-07, E-10); front_desk (E-03, E-04, E-09); bilingual_clerk (E-10) |
| `amount` | E-01, E-05, E-06, E-07 | auditor |
| `missing_documents` | none (moved on no enquiry) | none |

Language of `reason` for the bilingual clerk matched the language of the enquiry on
all ten enquiries (English for E-01…E-06 and E-08…E-10, Kazakh for E-07).

### Raw replies

A reply where a role changed the decision away from the policy officer's
(auditor on E-01; the policy officer said `granted`):

```
{
  "applicant_id": "A-201",
  "found": true,
  "decision": "more_info",
  "amount": 0,
  "missing_documents": [],
  "reason": "The Need-based study grant 2026 rule appears satisfied: the record shows GPA 3.4, income band 1, and both required documents (transcript and id_card). A second review is required before any grant is issued."
}
```

E-07 (the Kazakh enquiry), bilingual clerk:

```
{
  "applicant_id": "A-201",
  "found": true,
  "decision": "granted",
  "amount": 250000,
  "missing_documents": [],
  "reason": "Сіз грант талаптарына сай келесіз: GPA көрсеткіші 3.4, табыс санатыңыз 1, транскрипт пен жеке куәлік құжаттарыңыз бар. Грант мөлшері — 250000 теңге."
}
```

### Written answers

<!-- TODO: write these yourself, about your own run. Look at: the decision and
amount rows of the field-movement table, which roles moved them, the E-03/E-04/
E-07/E-10 rows, the E-10 row for auditor and bilingual_clerk, and what your
downstream code could read from a record. -->

**1. Which fields are role-sensitive and which are not?** Point at rows in your
tables.

>

**2. Which enquiries are most sensitive to the role, and why those?** Say what
E-03, E-04, E-07 and E-10 are each testing.

>

**3. Where does discretion belong — the role paragraph, or code that reads
`decision` afterwards?** Say what a downstream program can and cannot tell about
which role produced a record.

>

**4. Is a role a boundary?** Say in Week 2 terms what the role paragraph is made
of, and what you would put in code — not in the prompt — if a wrong `decision`
were expensive.

>

---

## Sublab Medium — memory you choose

Model: `gpt-5.6-luna`. The system message holds the assistant instruction, the
grant rule and the records (about 600 tokens), so call 1 already costs 687 tokens.
Tokens are the `prompt_tokens` reported by the API. Both runs send the same
eleven applicant turns; in run A the `<compress>` turn is skipped.

### Tokens per call

| Call | A — never compressed | B — compressed at the `compress` turn |
|---|---|---|
| 1 | 687 | 687 |
| 2 | 784 | 795 |
| 3 | 857 | 865 |
| 4 | 918 | 923 |
| 5 | 974 | 976 |
| 6 | 1088 | 1080 |
| 7 | 1199 | 1158 |
| 8 | 1287 | 1233 |
| 9 | 1382 | 1319 |
| 10 | — (skipped) | 1718 (the compress call itself) |
| 11 | 1476 | 951 |
| 12 | 1574 | 1046 |
| **peak** | 1574 | 1718 |
| **total for the run** | 12226 | 12751 |

The totals above do not include the five probe calls. The probe calls sent
1613, 1611, 1616, 1614, 1611 tokens in run A (8065 in total) and
1089, 1087, 1092, 1090, 1087 tokens in run B (5445 in total).

### Probes after the conversation

| Probe | Tests | A retrieved? | A answer | B retrieved? | B answer |
|---|---|---|---|---|---|
| Q-1 identity | turn 1 | yes | You are Daniyar Qoshan, applicant A-202. | yes | You are Daniyar Qoshan, applicant A-202. |
| Q-2 missing document | turn 5 | yes | Your id_card is still missing from the file. | yes | Your ID card is still missing from your file. |
| Q-3 band and amount | turns 3–4 | yes | Your record lists your income band as 2, which corresponds to a grant amount of 150,000 KZT. | yes | Your recorded income band is 2, which corresponds to a grant amount of 150,000 KZT, provided your ID card is added to the record. |
| Q-4 the constraint | turn 6 | yes | You said you can come to the office on Thursdays. | yes | You can come to the office on Thursdays. |
| Q-5 the open question | turn 7 | yes | You asked whether a scanned letter from your employer would count or whether the original was required. I explained that only the transcript and id_card are listed as required documents, and the record does not specify whether a scan or original is accepted. | **no** (lost) | You haven't asked me anything about your employer in the available conversation record. |
| **retrieved** | | 5/5 | | 4/5 | |

Note on Q-5 in run B: the script's substring check (`expect_contains`) marked it
retrieved only because the reply contains the word "employer"; reading the
reply, the question from turn 7 was lost. Counted here as lost.

### The state my compression produced

```json
{
  "applicant_id": "A-202",
  "topic": "Need-based study grant eligibility",
  "facts": [
    "Applicant stated their name is Daniyar Qoshan.",
    "Applicant stated they sent their transcript last week.",
    "Applicant stated their income band is 2 and their family's certificate says so.",
    "Applicant stated they could not upload their ID card because the scanner at home broke.",
    "Applicant stated they can only come to the office on Thursdays because they have lab all week otherwise.",
    "Applicant stated their sister Aruzhan applied last year and is on file."
  ],
  "decisions": [
    "Applicant does not currently qualify because the ID card is missing from the record.",
    "If the ID card is added and the application qualifies, the grant amount is 150,000 KZT.",
    "The record does not specify whether the decision would be made on the same day.",
    "Aruzhan Nurlan qualifies for 250,000 KZT under the 2026 scheme."
  ],
  "constraints": [
    "The ID card must be added to the record for the applicant to qualify.",
    "The applicant can come to the office only on Thursdays.",
    "The applicant has lab all week otherwise."
  ],
  "open_questions": [],
  "language": "en+kk"
}
```

### Written answers

<!-- TODO: write these yourself, about your own run. Look at: peak and total
tokens in both directions, calls 11–12 against the compress call, the five
probes (especially Q-5 in B and the empty `open_questions`), what the state
contains that the applicant never said (the Aruzhan line in `decisions`), and
the state fields that have no place for something said in turns 1–9. -->

**1. What did compression buy?** Peak tokens both ways, probes retrieved both
ways, and — if a probe was lost — which one and which turn it came from.

>

**2. Why must the state be structured rather than a paragraph?** You could have
asked for "a summary". Say what changes when the summary is an object with named
fields.

>

**3. What is missing from your state that you would add?** Name what you would
add and what you would drop to pay for it.

>

**4. When is compression the wrong choice?** Name a conversation where it would
lose something that cannot be recovered, and say whether your program would
notice.

>

---

## Sublab Hard — stories in, CVs out, the best candidate by code

Model: `gpt-5.6-luna`. The weights come from `candidate_rubric.json`
(0.5 / 0.3 / 0.2); the model returns only the three 0–5 scores and the code
computes the total and the winner.

### Part 1 — extraction

| Story | Parsed? | Valid? | Fields that came back `null` | Traps hit |
|---|---|---|---|---|
| story-01 | yes | yes | none | none |
| story-02 | yes | yes | graduation_year, gpa_original, gpa_4_scale | no GPA stated |
| story-03 | yes | yes | none | GPA on another scale (4.6 / 5.0); one paper under review (not counted) |
| story-04 | yes | yes | none | three papers not published (one under review, two in preparation) |
| story-05 | yes | yes | none | one paper not published (not submitted anywhere) |
| story-06 | yes | yes | graduation_year, gpa_original, gpa_4_scale | contradiction (GPA 3.2 vs 3.5; graduated 2024 vs graduating 2026) |

The four traps, for reference: no GPA stated · a GPA on another scale · a paper
that is not published · a story that contradicts itself.

Extraction for **story-06**:

```json
{
  "full_name": "Nurzhan Abilov",
  "degree": "BSc in Statistics",
  "graduation_year": null,
  "gpa_original": null,
  "gpa_scale_max": null,
  "gpa_4_scale": null,
  "languages": [
    "Kazakh",
    "Russian",
    "English"
  ],
  "published_count": 1,
  "unpublished_papers": [],
  "experience_months": 40,
  "experience_notes": "The story describes the duration as approximate; the first eight months were part-time.",
  "ambiguities": [
    "Graduation status and year are contradictory: the story says, \"I graduated in 2024\" and also says, \"I am currently a final-year student graduating in 2026.\"",
    "GPA is contradictory: the story gives both 3.2 and 3.5, and no grading scale is stated."
  ],
  "evidence": {
    "full_name": "# Nurzhan Abilov",
    "degree": "I graduated in 2024 with a BSc in Statistics.",
    "languages": "Languages: Kazakh, Russian, English.",
    "published_count": "one paper published, in a peer-reviewed proceedings, on survey weighting.",
    "experience_months": "I have been at an insurance analytics team since February 2023, which is about forty months.",
    "experience_notes": "I was part-time for the first eight of those while I was still studying, then full-time."
  },
  "candidate_id": "story-06"
}
```

### Part 2 — scores and the winner

| Candidate | academic (0–5) | research (0–5) | experience (0–5) | weighted total (code) |
|---|---|---|---|---|
| story-01 | 5 | 5 | 1.67 | 4.33 |
| story-02 | 0 | 2.5 | 5 | 1.75 |
| story-03 | 5 | 2.5 | 2.92 | 3.83 |
| story-04 | 4 | 2.5 | 5 | 3.75 |
| story-05 | 5 | 2.5 | 1.25 | 3.5 |
| story-06 | 1 | 2.5 | 5 | 2.25 |

**Winner, computed by my code:** story-01 (Aziza Bekova), total 4.33. Gap to
second place (story-03): 0.5.

**The model's prose answer, asked separately ("who should win?"):**

> **story-01 should win.** Aziza has a strong 3.8/4.0 GPA and two published peer-reviewed papers, satisfying the highest research criterion; her eight months of relevant data-team experience is an additional advantage. Although other candidates have longer work histories, none combines her academic record with two confirmed publications.

Prose winner story-01, code winner story-01: they agreed in this run.

Other runs of the same program, same code apart from the scoring-prompt rule
described in the answers below, gave different numbers: in one earlier run
story-01 got research 2.5 and the code winner was story-03 (3.85) with story-04
second (3.75), while the prose answer still named story-01.

### Part 3 — written answers

<!-- TODO: write these yourself, about your own run(s). Look at: the research
score of story-01 across your runs and the `note` the model wrote when it gave
2.5; the academic scores of story-02 and story-06 (0 vs 1) against the
contradiction rule in your scoring prompt; story-03's GPA 4.6/5.0 converted to
3.68 against the "at or above 3.7" anchor; the gap between first and second in
each of your runs. -->

**1. Which rule did you have to add, and what broke without it?** Name the story
that forced it.

>

**2. Where did the model guess, and where did your code have to decide?** One
example of each, from your run.

>

**3. Did your prose ranking and your computed ranking agree?** Say which one you
trust and why — and if they agreed, what you would need to see before trusting the
prose one alone.

>

**4. The rubric has no anchor for a contradicted field.** The stories say 3.2 and
3.5; the rubric defines a 0 and a 5 and nothing in between for this case. Say what
you did and what the rule should be.

>

**5. How close were your top two candidates?** If they were within 0.05, say what
you would tell the committee and what you would change in the extraction to make
that call defensible.

>

---

## Reflection (optional, one short paragraph)

Having now written a role prompt, compressed a conversation, and ranked six
extractions — what will you do differently the next time you build something that
has to get reliable structured output out of a model?

>
