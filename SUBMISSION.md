# HW2 submission

**Name:** Ruskulbek Makpal
**Student ID:** S23067710
**Group:** 9
**Repository:** https://github.com/makpalrus/ai-2026-hw2
---

## Sublab Easy — one task, four roles

Model: `gpt-5.6-luna`. The user message (records, rule, shape description, enquiry text) is identical for all four roles; only the system message changes. The `expected` field is never sent to the model. No temperature was set, so the runs are not deterministic.

### Decisions per role

✓ = all four structured fields agree with `expected`; ✗ = at least one differs.

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

The language of `reason` for the bilingual clerk matched the language of the enquiry on all ten enquiries (English for E-01…E-06 and E-08…E-10, Kazakh for E-07).

### Raw replies

A reply where a role changed the decision away from the policy officer's (auditor on E-01; the policy officer said `granted`):

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

**1. Which fields are role-sensitive and which are not?**

`decision` is role-sensitive, and `amount` follows it; `found` and `missing_documents` are not role-sensitive at all.

- `found` moved on no enquiry. Whether a person is on file is a lookup, and no role paragraph touches it (E-08 is `not_found` under all four roles).
- `missing_documents` moved on no enquiry. Even on E-10, where two roles changed the decision, all four roles returned `["id_card"]`.
- `decision` moved on nine of ten enquiries (every row except E-08). The auditor moved it on six (E-01, E-02, E-05, E-06, E-07, E-10), the front desk on three (E-03, E-04, E-09), and the bilingual clerk on one (E-10).
- `amount` moved on E-01, E-05, E-06 and E-07 under the auditor only. It is not an independent field: the amount is non-zero only when the decision is `granted`, so it changes exactly where the auditor turned a `granted` into `more_info`.

The task expects one role to move `decision` and one to move only `reason`. From my counts, the decision-movers are the auditor (6 enquiries) and the front desk (3). The role that should move only `reason` is the bilingual clerk, and in nine of ten rows it did: same decision, amount and documents as the policy officer, with the reason in the enquiry's language. The exception is E-10, where it returned `refused` instead of `more_info`. The most likely cause is in my own prompt: the clerk paragraph says "decide exactly as the policy officer would", but the model never sees the policy officer's paragraph, so the sentence "if a required document is missing, answer `more_info`" is absent from the clerk's prompt. The clerk then read "a claim in the enquiry is not evidence" as "the applicant does not qualify". I did not fix a temperature, so part of this could also be sampling variation; I report it as it came out.

**2. Which enquiries are most sensitive to the role, and why those?**

The rows that move are the ones where the outcome is the thing a role is written about.

- The auditor's rule is "never grant on a first reading", so it flipped all four enquiries where the policy officer granted: E-01, E-05, E-06, E-07 (and `amount` went from the granted sum to 0 with it).
- The front desk's rule is "never refuse", so it flipped all three refusals: E-03, E-04, E-09.
- E-03 and E-04 are the plain refusals the rule demands, with nothing missing and nothing to ask for. They test whether a role softens a refusal. Only the front desk did.
- E-07 is the same grant as E-01 in Kazakh. It tests whether the language of the enquiry changes the decision. It did not: the policy officer and the clerk both returned `granted`, 250000, and the clerk wrote the reason in Kazakh. The only thing that moved E-07 was the auditor's rule.
- E-10 tests whether the model treats the applicant's claim ("I uploaded my id card yesterday") as evidence. The record does not show it, so the expected answer is `more_info` with `id_card` missing. The policy officer and the front desk got it. The auditor and the clerk answered `refused`: they correctly refused to believe the claim, but then treated the missing document as a failed application instead of an incomplete one.
- E-02 is also worth naming: the auditor changed `more_info` to `refused`, so its effect is not limited to "grants become more_info". Told to say so when the record "plainly fails the rule", it counted a missing document as a failure.
- E-08 is the least sensitive row: a name that is not in the records gives `not_found` under every role, because there is nothing to interpret.

**3. Where does discretion belong — the role paragraph, or code that reads `decision` afterwards?**

Discretion belongs in code. The role paragraph only shifts the probabilities of what the model writes, and my table shows it does so unevenly: the auditor's rule held on 4 of 4 grants, but it also leaked into E-02 and E-10, which it was never meant to touch, and the clerk's "same as the policy officer" did not fully hold on E-10. Code that reads `decision` can enforce a rule exactly every time.

A downstream program that receives the six-field JSON can check that it parses, that it matches the schema, that `amount` is non-zero only when `decision` is `granted`, and that `found` agrees with the records. It cannot tell which role produced a record. There is no role field in the contract, and the same reply is possible from several roles: E-02 `more_info` with `["id_card"]` is identical for the policy officer, the front desk and the clerk, and E-10 `refused` came from two different roles. The `reason` text sometimes hints at the role (the auditor names the rule), but it is free text a program cannot rely on. If the role matters, the program has to record it itself, next to the reply, rather than ask the model to say it.

**4. Is a role a boundary?**

No. In Week 2 terms the role paragraph is a few dozen tokens placed in the same context as the records and the enquiry; the model is continuing a document, and it has no separate channel in which the system text is binding and the applicant's text is not. Nothing in the architecture enforces "you never grant". The auditor mostly followed it, but E-10 shows how a role paragraph misfires on a case it was not written for, and both the auditor and the clerk failed to reproduce the policy officer's behaviour there.

If a wrong decision were expensive, I would put the decision in code and keep the model only for the text:
- compute the decision from `records.json` and `policy.json` (GPA threshold, income band, required documents) in plain Python, and compare it with the model's `decision`; on any mismatch, flag it or use the code's value;
- derive `amount` from the policy table in code, never take it from the model;
- require a human second reader for every `granted` before it is issued;
- treat claims in the enquiry text as untrusted input and never let them change what the code checks;
- log which role and which prompt version produced each record.

---

## Sublab Medium — memory you choose

Model: `gpt-5.6-luna`. The system message holds the assistant instruction, the grant rule and the records (about 600 tokens), so call 1 already costs 687 tokens. Tokens are the `prompt_tokens` reported by the API. Both runs send the same eleven applicant turns; in run A the `<compress>` turn is skipped.

### Tokens per call

| Call | A — never compressed | B — compressed at the compress turn |
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

The totals above do not include the five probe calls. The probe calls sent 1613, 1611, 1616, 1614, 1611 tokens in run A (8065 in total) and 1089, 1087, 1092, 1090, 1087 tokens in run B (5445 in total). Including probes, the totals are 20291 (A) and 18196 (B).

### Probes after the conversation

| Probe | Tests | A retrieved? | A answer | B retrieved? | B answer |
|---|---|---|---|---|---|
| Q-1 identity | turn 1 | yes | You are Daniyar Qoshan, applicant A-202. | yes | You are Daniyar Qoshan, applicant A-202. |
| Q-2 missing document | turn 5 | yes | Your id_card is still missing from the file. | yes | Your ID card is still missing from your file. |
| Q-3 band and amount | turns 3–4 | yes | Your record lists your income band as 2, which corresponds to a grant amount of 150,000 KZT. | yes | Your recorded income band is 2, which corresponds to a grant amount of 150,000 KZT, provided your ID card is added to the record. |
| Q-4 the constraint | turn 6 | yes | You said you can come to the office on Thursdays. | yes | You can come to the office on Thursdays. |
| Q-5 the open question | turn 7 | yes | You asked whether a scanned letter from your employer would count or whether the original was required. I explained that only the transcript and id_card are listed as required documents, and the record does not specify whether a scan or original is accepted. | no (lost) | You haven't asked me anything about your employer in the available conversation record. |
| **retrieved** | | **5/5** | | **4/5** | |

Note on Q-5 in run B: the script's substring check (`expect_contains`) marked it retrieved only because the reply contains the word "employer"; reading the reply, the question from turn 7 was lost. Counted here as lost.

### The state my compression produced

```
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

**1. What did compression buy?**

Peak tokens: 1574 without compression, 1718 with it. So compression did not lower the peak. The compress call itself is the most expensive call of the run, because it sends the whole history plus the compress instruction (1718 tokens), and run A has no such call.

What it bought is cheaper calls afterwards. After the compression, call 11 cost 951 instead of 1476 (−525) and call 12 cost 1046 instead of 1574 (−528). Each probe cost about 1090 instead of about 1613, saving 2620 tokens over the five probes. Over the whole run including probes, run B sent 18196 tokens against 20291 for run A, a saving of 2095 (about 10%). The one-off cost of 1718 is paid back after about four further calls at roughly 525 tokens saved each, and the gap keeps growing with every later turn, because the uncompressed history grows and the state does not.

Probes retrieved: 5 of 5 without compression, 4 of 5 with it. The lost probe is Q-5, from turn 7 (the question whether a scanned letter from the employer counts or the original is required). The state has `open_questions: []`, and nothing about the question appears in `facts`, `decisions` or `constraints`. The assistant had already answered the question in the thread, so the model treated it as closed and dropped it, but its answer ("the record does not say whether a scan is accepted") was not stored either, so the information was lost completely. (The script marked Q-5 as retrieved because its substring check looks for the word "employer", which appears in a reply saying the question was never asked.)

**2. Why must the state be structured rather than a paragraph?**

With a paragraph, the only thing a program can check is that it is a string. With an object with named fields, three things change.

First, the program can validate it. `compress()` checks the state against `memory_state.schema.json`, and if the reply does not parse or does not validate, it keeps the full history instead of replacing it. A paragraph has no shape that could fail this check.

Second, the model has to decide, field by field, where each thing goes. The prompt separates what the applicant stated (`facts`, each written as "Applicant stated…") from what the assistant decided (`decisions`) and from conditions (`constraints`). That separation kept the claim "my income band is 2" apart from the assistant's answer about 150,000 KZT, and it kept "Thursdays" as an exact constraint instead of "limited availability".

Third, a failure becomes visible and testable. I could see why Q-5 failed by looking at one field, `open_questions: []`; in a paragraph the missing sentence would just be absent. Each probe also maps to a field (Q-1 to `applicant_id` and `facts`, Q-4 to `constraints`, Q-5 to `open_questions`), so the compression can be tested per field. A fixed structure can also be merged on later compressions by updating fields, instead of summarising a summary, which blurs details more each time.

**3. What is missing from your state that you would add?**

I would add an `answered_questions` field holding the question and the answer that was given, for example "scanned letter from employer: record lists only transcript and id_card as required and does not say whether a scan or an original is accepted." That is exactly what Q-5 needed. The schema's `open_questions` only covers unanswered questions, and nothing in the schema says what to do with an answered one, so it vanishes. I would also add a `source_turn` for each fact, so that a lost detail can be traced back to the turn it came from.

To pay for it, I would drop or shorten three things in this state:
- the decision "The record does not specify whether the decision would be made on the same day", which is not a decision;
- the constraint "The applicant has lab all week otherwise", which only repeats the reason behind the Thursdays constraint;
- the decision "Aruzhan Nurlan qualifies for 250,000 KZT", which is about a different person (the applicant's sister) and does not belong in A-202's state at all.

**4. When is compression the wrong choice?**

It is the wrong choice when the details of the conversation are exactly what matters and cannot be re-obtained: for example a legal or medical intake, or a negotiation, where an exact amount, a date or a wording was said once. In my program the original turns are thrown away on purpose, so anything the summary leaves out is gone for good.

My program would not notice. The only check is that the state parses and matches the schema, and a state with `open_questions: []` is a perfectly valid object. Q-5 shows this: compression succeeded with no error, and the loss was found only because I asked a probe afterwards. A safer design would keep the full transcript on disk and send only the state, so a lost detail could be recovered, and would run a few probe questions automatically after each compression.

---

## Sublab Hard — stories in, CVs out, the best candidate by code

Model: `gpt-5.6-luna`. The weights come from `candidate_rubric.json` (0.5 / 0.3 / 0.2); the model returns only the three 0–5 scores and the code computes the total and the winner.

### Part 1 — extraction

| Story | Parsed? | Valid? | Fields that came back null | Traps hit |
|---|---|---|---|---|
| story-01 | yes | yes | none | none |
| story-02 | yes | yes | graduation_year, gpa_original, gpa_4_scale | no GPA stated |
| story-03 | yes | yes | none | GPA on another scale (4.6 / 5.0); one paper under review (not counted) |
| story-04 | yes | yes | none | three papers not published (one under review, two in preparation) |
| story-05 | yes | yes | none | one paper not published (not submitted anywhere) |
| story-06 | yes | yes | graduation_year, gpa_original, gpa_4_scale | contradiction (GPA 3.2 vs 3.5; graduated 2024 vs graduating 2026) |

The four traps, for reference: no GPA stated · a GPA on another scale · a paper that is not published · a story that contradicts itself.

Extraction for story-06:

```
{
  "full_name": "Nurzhan Abilov",
  "degree": "BSc in Statistics",
  "graduation_year": null,
  "gpa_original": null,
  "gpa_scale_max": null,
  "gpa_4_scale": null,
  "languages": ["Kazakh", "Russian", "English"],
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
| story-03 | 5 | 2.5 | 2.92 | 3.83 |
| story-04 | 4 | 2.5 | 5 | 3.75 |
| story-05 | 5 | 2.5 | 1.25 | 3.5 |
| story-06 | 1 | 2.5 | 5 | 2.25 |
| story-02 | 0 | 2.5 | 5 | 1.75 |

Winner, computed by my code: **story-01 (Aziza Bekova), total 4.33**. Gap to second place (story-03): 0.5.

The model's prose answer, asked separately ("who should win?"):

> story-01 should win. Aziza has a strong 3.8/4.0 GPA and two published peer-reviewed papers, satisfying the highest research criterion; her eight months of relevant data-team experience is an additional advantage. Although other candidates have longer work histories, none combines her academic record with two confirmed publications.

Prose winner story-01, code winner story-01: they agreed in this run.

Other runs of the same program, same code apart from the scoring-prompt rule described in the answers below, gave different numbers: in one earlier run story-01 got research 2.5 and the code winner was story-03 (3.85) with story-04 second (3.75), while the prose answer still named story-01.

### Part 3 — written answers

**1. Which rule did you have to add, and what broke without it? Name the story that forced it.**

The rule I added to the scoring prompt says that `published_count` and `experience_months` in the record have already been counted under the counting rules, that the scorer must use them as given, and that it must not lower a score because an evidence quote is shortened or mentions only one of the outputs. The story that forced it was story-01, the candidate with two published peer-reviewed papers. Without the rule, the scorer apparently relied on the short evidence quote, which mentions only one of the papers, and gave research 2.5 instead of 5. That one number changed the result: story-01's total dropped by 0.75 (to about 3.58), below story-03's 3.85, so the code named the wrong winner (story-03) while the prose answer still said story-01.

I also had to state that a null field means "not stated", and that this applies equally to a field that is null because the story contradicted itself. That one came from story-02 and story-06, where the model otherwise had no instruction for what to do with a missing or contradicted GPA.

**2. Where did the model guess, and where did your code have to decide? One example of each, from your run.**

The model guessed on story-06's academic score. The story gives a degree but no usable GPA (the two values contradict each other), and the rubric and my own prompt say that no GPA scores 0. The model gave story-06 an academic score of 1, while story-02 (degree stated, no GPA) got 0. Same situation, two different scores; this is a guess the rubric does not support. The model also filled in the middle of the 0–5 scale without a rule: one published paper became 2.5 for story-02, 03, 04, 05 and 06, because the rubric only anchors 0 (none) and 5 (two or more).

The code decided the total and the ranking: for story-03 it computed 0.5 × 5 + 0.3 × 2.5 + 0.2 × 2.92 = 3.83 and put it second. The model never saw the weights. The code also holds the GPA conversion rule: it recomputes `gpa_4_scale` from `gpa_original` and the scale maximum, and sets it to null if there is no original GPA. In the final run that check did not have to override anything (the model's 4.6 / 5 → 3.68 for story-03 already matched), but without it the model's own arithmetic would have gone straight into the scores.

**3. Did your prose ranking and your computed ranking agree? Say which one you trust and why — and if they agreed, what you would need to see before trusting the prose one alone.**

In the final run they agreed: both named story-01. In the earlier run they did not: the code said story-03 and the prose said story-01. I trust the computed ranking more, because I can inspect it: the scores, the record they came from, and the weights are all visible, and when the research score for story-01 was wrong I could find it. The prose answer is one paragraph, with no scores and no way to see how criteria were weighed.

But the computed ranking is only as good as the model's scores, which changed between runs (story-01's research was 5 in one run and 2.5 in another). To trust the prose answer alone I would need to see: the same winner across many repeated runs, the winner's facts in the prose matching the extracted fields (here 3.8 and two papers do match), the same answer when the order of the six stories is shuffled, and a large gap between first and second.

**4. The rubric has no anchor for a contradicted field. The stories say 3.2 and 3.5; the rubric defines a 0 and a 5 and nothing in between for this case. Say what you did and what the rule should be.**

I followed the counting rule: the GPA field is null, the contradiction is written in `ambiguities`, and the scorer treats a null as "not stated", which under the rubric means academic 0. (The model actually gave 1; see answer 2.) This is the harshest possible reading, and it treats a contradiction exactly like an absence, although a contradicted field may only be a typo while an absent one is a real gap.

I think the rule should separate the two cases. A contradicted field should not be scored as 0 silently: the code should flag the candidate as "needs clarification", and ask the candidate which value is right. If the ranking has to be produced without waiting, the code should score both values and report the range. For story-06, an academic score of roughly 4 (the score story-04 got for 3.6) would give 0.5 × 4 + 0.3 × 2.5 + 0.2 × 5 = 3.75, level with story-04 and above story-05, instead of fifth place with 2.25. So the contradiction matters for the ranking and should not be hidden inside a single number.

**5. How close were your top two candidates? If they were within 0.05, say what you would tell the committee and what you would change in the extraction to make that call defensible.**

In my run the top two were story-01 (4.33) and story-03 (3.83), a gap of 0.5, ten times more than 0.05. But the gap is more fragile than it looks: story-01's lead comes entirely from research (5 against 2.5, worth 0.75 in the total), and in the earlier run that single score dropped to 2.5 and story-03 won by about 0.27. So a large gap in one run is not safe if one score can swing it.

If the top two had been within 0.05, I would tell the committee that the model cannot separate them: a difference that small is below the noise between runs, so the winner should be decided by the committee, for example by an interview or by a tie-break rule agreed before looking at the scores (research first, then academic record). To make the call more defensible I would change the extraction and scoring in three ways: check in code that every evidence quote appears verbatim in the story; run scoring several times at a fixed low temperature and use the median score for each criterion; and store the exact counts (published papers, countable months) as fields so the committee can check the inputs behind every score.

---

## Reflection

Next time I will make the program decide everything that can be decided by code, such as sums, conversions, rankings and rule checks, and use the model only for what needs language: reading a story, writing a reason. I will also validate every reply against a schema, check evidence against the source, and run the same call several times before believing a single result, because in this homework the same code gave different winners on different runs.
