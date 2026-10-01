# HW2 submission

**Name:** Ruskulbek Makpal
**Student ID:** S23067710
**Group:** 9
**Repository:** https://github.com/makpalrus/ai-2026-hw2

Model for all three sublabs: `gpt-5.6-luna`. No `.env` or key was committed (`git log --all -- .env` returns nothing). No key was leaked.

All numbers below come from one run of each program (raw replies are in `last_run.json`). No temperature was set, so runs are not deterministic; I say where that matters.

---

## Sublab Easy — one task, four roles

The user message (records, rule, shape description, enquiry text) is identical for all four roles; only the system message changes. The `expected` field is never sent to the model.

### Decisions per role

OK = all four structured fields agree with `expected`; X = at least one differs.

| Enquiry | policy_officer | front_desk | auditor | bilingual_clerk |
|---|---|---|---|---|
| E-01 | granted OK | granted OK | more_info X | granted OK |
| E-02 | more_info OK | more_info OK | refused X | more_info OK |
| E-03 | refused OK | more_info X | refused OK | refused OK |
| E-04 | refused OK | more_info X | refused OK | refused OK |
| E-05 | granted OK | granted OK | more_info X | granted OK |
| E-06 | granted OK | granted OK | more_info X | granted OK |
| E-07 | granted OK | granted OK | more_info X | granted OK |
| E-08 | not_found OK | not_found OK | not_found OK | not_found OK |
| E-09 | refused OK | more_info X | refused OK | refused OK |
| E-10 | more_info OK | more_info OK | refused X | refused X |
| **agrees with `expected`** | 10/10 | 7/10 | 4/10 | 9/10 |
| **parsed** | 10/10 | 10/10 | 10/10 | 10/10 |
| **schema-valid** | 10/10 | 10/10 | 10/10 | 10/10 |

### Which field moved (vs policy_officer), on which enquiry, under which role

| Field | Enquiries that moved | Role(s) |
|---|---|---|
| `found` | none | none |
| `decision` | E-01, E-02, E-03, E-04, E-05, E-06, E-07, E-09, E-10 | auditor (E-01, E-02, E-05, E-06, E-07, E-10); front_desk (E-03, E-04, E-09); bilingual_clerk (E-10) |
| `amount` | E-01, E-05, E-06, E-07 | auditor |
| `missing_documents` | none | none |

Language of `reason` for the bilingual clerk vs the language of the enquiry: it matched on all ten (English for every enquiry except E-07, which is Kazakh and got a Kazakh reason).

### Raw replies

Auditor on E-01 (the policy officer said `granted`):

```
{
  "applicant_id": "A-201",
  "found": true,
  "decision": "more_info",
  "amount": 0,
  "missing_documents": [],
  "reason": "The record for Aigerim Serik (A-201) shows GPA 3.4, income band 1, and both required documents under the Need-based study grant 2026 rule. The rule's criteria appear satisfied, but this first reading is referred for a second review; no grant is issued at this stage."
}
```

Bilingual clerk on E-07 (the Kazakh enquiry):

```
{
  "applicant_id": "A-201",
  "found": true,
  "decision": "granted",
  "amount": 250000,
  "missing_documents": [],
  "reason": "Сіздің GPA көрсеткіші 3.4, табыс санатыңыз 1, сондай-ақ транскрипт пен жеке куәлік құжаттарыңыз бар. Сондықтан сізге 250 000 теңге мөлшерінде грант беріледі."
}
```

### Written answers

**1. Which fields are role-sensitive and which are not?**

`decision` is the role-sensitive field, and `amount` follows it. `found` and `missing_documents` are not role-sensitive.

- `found` moved on no enquiry: whether a person is on file is a lookup, and E-08 is `not_found` under all four roles.
- `missing_documents` moved on no enquiry under any role, including E-10, where two roles changed the decision.
- `decision` moved on nine of ten enquiries (every row except E-08): the auditor on six (E-01, E-02, E-05, E-06, E-07, E-10), the front desk on three (E-03, E-04, E-09), the bilingual clerk on one (E-10).
- `amount` moved on E-01, E-05, E-06, E-07, under the auditor only. It is not independent: it changed exactly on the rows where the auditor turned a `granted` into `more_info`, because no grant means 0.

The role that moves `decision` is the **auditor** (4/10 agreement) and, more mildly, the **front desk** (7/10). The role expected to move only `reason` is the **bilingual clerk**: in nine of ten rows it kept the policy officer's decision, amount and documents and only changed the language of the reason. The exception is E-10, where it returned `refused` instead of `more_info`. One possible cause is that the clerk paragraph says "decide exactly as the policy officer would", but the model never sees the policy officer's paragraph, so that sentence points at nothing. Because I set no temperature, part of it could also be sampling variation. I did not test which, so this is a hypothesis, not a result. <!-- optional: re-run Easy 3–5 times and report how often E-10 flips -->

**2. Which enquiries are most sensitive to the role, and why those?**

The rows that move are the ones where the outcome is exactly what a role paragraph is written about.

- The auditor's rule is "never grant on a first reading", and it flipped all four enquiries where the policy officer granted: E-01, E-05, E-06, E-07 (with `amount` going to 0).
- The front desk's rule is "never refuse", and it flipped all three refusals: E-03, E-04, E-09. These are clean refusals with nothing to ask for, so they test whether a role softens a refusal. Only the front desk did.
- E-07 is a grant in Kazakh. It tests whether the language of the enquiry changes the decision. It did not: the policy officer, the front desk and the clerk all granted it, and the clerk answered in Kazakh. Only the auditor's rule moved it.
- E-10 is the case where the applicant claims a document that the record does not show (the record wins, so the expected answer is `more_info`). It is the only row where two roles, the auditor and the bilingual clerk, left the reference, in both cases to `refused`. They correctly did not accept the claim as evidence, but they treated the missing document as a failed application instead of an incomplete one.
- E-02 shows that the auditor's effect is not only "grants become more_info": there it changed `more_info` to `refused`.
- E-08 is the least sensitive: a name that is not in the records gives `not_found` under every role, because there is nothing to interpret.

**3. Where does discretion belong — the role paragraph, or code that reads `decision` afterwards?**

In code. The role paragraph only shifts what the model is likely to write, and the table shows the shift is imperfect: the auditor's "never grant" held on 4 of 4 grants, but it also leaked into E-02 and E-10, which it was not written for, and the clerk's "same as the policy officer" did not fully hold on E-10. Code that reads `decision` applies a rule exactly every time.

A downstream program that gets the six-field JSON can check that it parses, matches the schema, that `amount` is non-zero only when `decision` is `granted`, and that `found` agrees with the records. It cannot tell which role produced a record: there is no role field in the contract, and the same reply can come from several roles (E-10 `refused` came from two different roles). The `reason` text sometimes hints at the role, but it is free text a program cannot rely on. If the role matters, the program has to record it itself next to the reply.

**4. Is a role a boundary?**

No. In Week 2 terms, the role paragraph is a few dozen tokens in the same context as the records and the enquiry. The model is continuing a document, and there is no separate channel in which system text binds and applicant text does not. The auditor mostly followed its paragraph, but E-02 and E-10 show how it misfires on cases it was not written for.

If a wrong decision were expensive, I would move the decision into code:
- compute `decision` and `missing_documents` from `records.json` and `policy.json` (GPA threshold, income band, documents on file) in plain Python, and compare them with the model's reply; on a mismatch, flag it or use the code's value;
- derive `amount` from the policy table in code, never take it from the model;
- require a human second reader for every `granted` before it is issued;
- treat claims in the enquiry text as untrusted input that never changes what the code checks;
- log which role and prompt version produced each record.

---

## Sublab Medium — memory you choose

The system message holds the assistant instruction, the rule and the records, so call 1 already costs 687 tokens. Both runs send the same twelve turns; in run A the `<compress>` turn (turn 10) is skipped.

### Tokens sent per call

| Call | A — never compressed | B — compressed |
|---|---|---|
| 1 | 687 | 687 |
| 2 | 772 | 776 |
| 3 | 842 | 853 |
| 4 | 912 | 909 |
| 5 | 965 | 961 |
| 6 | 1043 | 1016 |
| 7 | 1120 | 1093 |
| 8 | 1198 | 1173 |
| 9 | 1286 | 1247 |
| 10 | — (`<compress>` skipped) | 1647 (the compress call itself) |
| 11 | 1363 | 994 |
| 12 | 1445 | 1054 |
| **peak** | **1445** | **1647** |
| **total** | **11633** | **12410** |

### Probes

| Probe | A | B |
|---|---|---|
| Q-1 | retrieved | retrieved |
| Q-2 | retrieved | retrieved |
| Q-3 | retrieved | retrieved |
| Q-4 | retrieved | retrieved |
| Q-5 | retrieved | retrieved |
| **retrieved** | **5/5** | **5/5** |

Answers (shortened):

- Q-1: both — "You are Daniyar Qoshan, applicant A-202."
- Q-2: A — "Your file is missing the id_card."; B — "Your id card is still missing from your file."
- Q-3: A — income band 2, which corresponds to 150,000 KZT if all requirements are met; B — income band 2, 150,000 KZT, and the id card is missing.
- Q-4: A — "You said you can come on Thursday", adding that the office's opening days are not confirmed; B — "You can come to the office on Thursdays."
- Q-5: A — you asked whether a scanned employer letter would count or the original is required, and the scheme information does not say; B — the scanned employer letter, and it remains unclear whether a scan is accepted or the original is required.

### The state my compression produced

```
{
  "applicant_id": "A-202",
  "topic": "Study grant eligibility",
  "facts": [
    "Applicant stated their name is Daniyar Qoshan.",
    "Applicant stated their applicant ID is A-202.",
    "Applicant stated they sent their transcript last week.",
    "Applicant stated their income band is 2 and that their family's certificate says so.",
    "Applicant stated they could not upload their id_card because the scanner at home broke.",
    "Applicant stated they can only come to the office on Thursdays because they have lab all week otherwise.",
    "Applicant mentioned a scanned letter from their employer.",
    "Applicant stated that their sister Aruzhan applied last year and is on file."
  ],
  "decisions": [
    "The assistant stated that the applicant currently does not qualify because the id_card is missing.",
    "The assistant stated that the applicant would qualify for 150,000 KZT if the id_card is added to the record.",
    "The assistant stated that Aruzhan Nurlan's current record qualifies for 250,000 KZT."
  ],
  "constraints": [
    "The id_card must be added to the record for eligibility.",
    "The applicant can only come to the office on Thursday.",
    "The applicant has lab all week otherwise."
  ],
  "open_questions": [
    "Whether a scanned employer letter is accepted or the original is required remains unspecified.",
    "Whether the grant decision will be made on the same day the id_card is submitted remains unspecified."
  ],
  "language": "kk+en"
}
```

### Written answers

**1. What did compression buy?**

On this twelve-turn script it did not buy a lower token count. The peak was 1445 tokens uncompressed and 1647 compressed, because the compress call itself is the most expensive call in run B: it sends the whole history plus the summarising instruction, and run A has no such call. The total was also higher with compression, 12410 against 11633 (+777).

What it did buy is cheaper calls afterwards. Call 11 cost 994 instead of 1363 (−369) and call 12 cost 1054 instead of 1445 (−391), and the gap widens every turn, because the uncompressed history keeps growing and the state does not. From these numbers, the extra 777 tokens would be paid back about two turns after turn 12, so compression starts to pay for itself in a conversation of roughly fourteen turns or longer.

Probes retrieved: 5 of 5 uncompressed and 5 of 5 compressed. No probe was lost, so there is no turn to blame. In this run the answers after compression were as complete as before; Q-4 and Q-5 were even stated more directly in run B.

**2. Why must the state be structured rather than a paragraph?**

First, a program can validate an object. `compress()` checks the state against `memory_state.schema.json`, and if it does not parse or validate, the history is kept instead of replaced. A paragraph has no shape that could fail this check.

Second, named fields force the model to decide where each thing goes. My state keeps what the applicant stated (`facts`, each starting "Applicant stated…") apart from what the assistant concluded (`decisions`) and from conditions (`constraints`), so a claim like "my income band is 2" is not blended with the assistant's answer about 150,000 KZT, and "Thursdays" stays an exact constraint instead of a vague "limited availability".

Third, a loss becomes inspectable. Each probe maps to a field (Q-1 to `applicant_id`/`facts`, Q-2 to `constraints`/`decisions`, Q-5 to `open_questions`), so I can see where a detail lives or is missing. And a later compression can update fields instead of summarising a summary.

**3. What is missing from your state that you would add?**

- A field for document status (transcript sent, id_card missing, scanned letter unclear), so the thing the decision depends on is its own field and not a sentence inside `facts`.
- A `source_turn` for each fact, so a wrong or missing fact can be traced to the turn it came from.
- An `answered_questions` field. `open_questions` only holds unanswered questions; a question the assistant already answered would disappear from the state.

To pay for them I would drop: the decision about the sister, "Aruzhan Nurlan's current record qualifies for 250,000 KZT" and the fact about her, which concern a third person and do not belong in A-202's state; the constraint "The applicant has lab all week otherwise", which repeats the reason inside the Thursday constraint and fact; and the open question about same-day decisions, which the applicant never really asked.

**4. When is compression the wrong choice?**

When the exact details are what matters and cannot be re-obtained: a legal or medical conversation, or a negotiation, where an amount, a date or a wording was said once. Compression throws the original turns away on purpose, so whatever the summary leaves out is gone for good.

My program would not notice. It checks that the state parses and matches the schema, not that it is complete or accurate. In my run 5 of 5 probes were retrieved, but the probes test only five things, and a detail nobody probes could be lost without any signal. A safer design keeps the full transcript on disk and sends only the state, so a lost detail can be recovered, and runs probe questions automatically after each compression.

**Interactive mode.** <!-- FILL IN: type `compress` in `python -m sublab_medium.chat_memory --interactive` and write 2–3 sentences: what `tokens` printed before and after, and what the summary dropped that you noticed. -->

---

## Sublab Hard — stories in, CVs out, the best candidate by code

### Part 1 — extraction

| Story | Parsed? | Valid? | Fields that came back null | Traps hit |
|---|---|---|---|---|
| story-01 | yes | yes | none | none |
| story-02 | yes | yes | graduation_year, gpa_original, gpa_4_scale | no GPA; ambiguity flagged |
| story-03 | yes | yes | none | GPA on another scale (/5); 1 unpublished paper |
| story-04 | yes | yes | none | 3 unpublished papers |
| story-05 | yes | yes | none | 1 unpublished paper |
| story-06 | yes | yes | graduation_year, gpa_original, gpa_4_scale | contradiction: GPA 3.2 vs 3.5 and graduation 2024 vs 2026; ambiguity flagged |

Rules in the extraction prompt: a fact the story does not state is `null` and never estimated; a GPA on another scale is converted to a 4.0 scale with the original scale recorded beside it; a paper counts as published only when the story says published or accepted (submitted, under review, in preparation and in press are recorded separately and not counted); a contradiction is not resolved or averaged: the field is `null` and the contradiction is recorded in `ambiguities`.

Extraction for story-06 (the contradiction case):

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
  "experience_notes": "The stated duration is approximate: \"which is about forty months.\"",
  "ambiguities": [
    "Graduation status/year is contradictory: the story says \"I graduated in 2024\" and also says \"I am currently a final-year student graduating in 2026.\"",
    "GPA is contradictory: the story gives both 3.2 and 3.5, and does not state the grading scale."
  ],
  "evidence": {
    "full_name": "Nurzhan Abilov",
    "degree": "I graduated in 2024 with a BSc in Statistics.",
    "languages": "Languages: Kazakh, Russian, English.",
    "published_count": "one paper published, in a peer-reviewed proceedings",
    "experience_months": "I have been at an insurance analytics team since February 2023, which is about forty months.",
    "experience_notes": "which is about forty months"
  },
  "candidate_id": "story-06"
}
```

### Part 2 — scores by the model, totals by the code

Weights from `candidate_rubric.json`: academic 0.5, research 0.3, experience 0.2. The model returns only the three 0–5 scores; my code computes `0.5·academic + 0.3·research + 0.2·experience`.

| Rank | Candidate | academic | research | experience | total (code) |
|---|---|---|---|---|---|
| 1 | story-01 | 5 | 5 | 1.7 | 4.34 |
| 2 | story-04 | 4 | 3 | 5 | 3.9 |
| 3 | story-03 | 4.5 | 2.5 | 3.0 | 3.6 |
| 4 | story-05 | 5 | 2.5 | 1.25 | 3.5 |
| 5 | story-02 | 0 | 2.5 | 5 | 1.75 |
| 6 | story-06 | 0 | 2.5 | 5 | 1.75 |

**Winner computed by code: story-01 (Aziza Bekova), total 4.34.** Gap to second place (story-04): 0.44.

The model's prose answer, asked in a separate call that did not see the scores:

> story-01 should win the funded place. Aziza has a strong, clearly stated 3.8/4.0 GPA and two published peer-reviewed research outputs, satisfying the highest academic and research standards; she also has eight months of relevant data-team experience. Although some candidates have longer work histories, none match this combination of excellent academic performance and two qualifying publications.

Prose winner story-01, code winner story-01: they **agreed**.

### Part 3 — written answers

**1. Which rule did you have to add, and what broke without it?**

The rule that a contradiction must not be resolved: the field becomes `null` and the contradiction goes into a separate `ambiguities` list. Story-06 forced it, because it says both "I graduated in 2024" and "graduating in 2026" and gives a GPA of both 3.2 and 3.5 with no scale. Without the rule, the model has two easy ways out: pick one value or average them. Either would make the record look clean while hiding the problem. Story-04 (three unpublished papers) forced the second rule, the separate record of papers that are not counted, so `published_count` stays honest while the unpublished work is still visible. <!-- CHECK: if a different story or rule forced a change in your own prompt iterations, replace this answer with what you actually saw. -->

**2. Where did the model guess, and where did your code have to decide?**

The model guessed on story-06's experience: the story says "since February 2023, which is about forty months", and the extraction returned `experience_months: 40` as a counted figure, with only a note saying it is approximate. That is an estimate from a vague phrase, the kind of thing the "never estimated" rule is meant to catch, and it earned story-06 a score of 5 on experience. The model's experience scores of 1.7 and 1.25 also look like arithmetic it did itself.

My code decided the weighted totals, the ranking and the winner, and the order of story-02 and story-06, which both totalled exactly 1.75 (the order between them comes from my sort, not from evidence).

**3. Did your prose ranking and your computed ranking agree?**

They agreed on the winner, story-01. I trust the computed ranking more, because its inputs are visible fields (scores and weights) that I can check and reproduce. The prose answer is one paragraph that argues for story-01 and does not compare her to the other five candidates, so it does not show that the ranking holds.

Before trusting the prose answer alone, I would need to see: the same winner across many repeated runs, a comparison of candidates criterion by criterion with evidence quotes from the extraction, the same answer when the order of the stories is shuffled, and a clear gap between first and second.

**4. The rubric has no anchor for a contradicted field.**

What happened: story-06's GPA field is `null` (contradicted) and story-02's is `null` (missing), and the model scored academic 0 for both, so a contradiction was treated exactly like an absence and the two candidates tied at 1.75. That is unfair, because a contradiction may be a typo while an absence is a real gap.

What the rule should be: a contradicted criterion should not silently become 0. The code should flag the candidate as "needs clarification" and ask the candidate which value is right. If a ranking has to be produced anyway, the code should score both stated values and report a range instead of one number. For illustration: if story-06 had been scored academic 4, its total would be 0.5·4 + 0.3·2.5 + 0.2·5 = 3.75, which would put it third instead of fifth. So the contradiction decides the ranking, and a single number hides that.

**5. The top two candidates: how close were they?**

Story-01 (4.34) and story-04 (3.9): a gap of 0.44, far more than 0.05. I would tell the committee that story-01 leads clearly on this rubric, but that this is one run with model-assigned scores, so it is a recommendation and not a measurement. Story-01's lead rests on academic and research (5 and 5), while she scored only 1.7 on experience, so the experience criterion could still move the totals.

If the top two had been within 0.05, I would say the model cannot separate them: a gap that small is below the noise between runs, so the committee should decide, using a tie-break rule agreed before looking at the scores. To make the call more defensible I would change the extraction and scoring: check in code that every evidence quote appears verbatim in the story, run the scoring several times and use the median for each criterion, store the exact counts (published papers, countable months) as fields so the committee can check the inputs, and add anchored examples to the rubric for the middle scores, since the model filled in 2.5 for research on five different candidates without a rule for it.

---

Next time I will let the code decide everything that can be decided by code — sums, conversions, rankings, rule checks — and use the model only for what needs language: reading a story, writing a reason. I will validate every reply against a schema, check evidence against the source, and run a call more than once before believing a single result, because the scores and the roles both moved in ways I did not expect.
