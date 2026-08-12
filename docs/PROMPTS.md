# PROMPTS.md — Agent prompts and design

This is the **core of the task**: perspectives, prompts and why they're shaped the way they are. The prompts in
the code (`.py`) and here are identical — this document is a readable reference and rationale.

Common **JSON schema** for all agents (except the synthesizer):

```json
{
  "score": 0.0,
  "criteria": [{"name": "...", "score": 0.0, "note": "..."}],
  "strengths": ["..."],
  "weaknesses": ["..."],
  "verdict": "..."
}
```

---

## Perspective design — why exactly these 5

The task asks for ≥3 perspectives and "your thinking about what makes a good text".
My thesis: **a good text** = *clearly structured* (the reader never gets lost) +
*psychologically effective* (concrete, focused on the reader's benefit, human tone) +
*quantitatively consistent* (a repeatable rubric) + *recognizably human*
(not generic, not AI). Each of those 4 dimensions gets an independent agent:

| Perspective | Answers the question | Why it's valuable |
|---|---|---|
| Structure | Is the text logically organized and does it guide the reader? | "Reader lost = content failed" — the most common reason people abandon text |
| Psychology | Does it apply the principles of good, persuasive writing? | Concreteness and benefit are what make copy effective (the core of the Lexi brand) |
| Rubric | What is the consistent, repeatable quantitative score? | Ensures consistency and comparability across articles |
| Human voice | Does it sound human or like generic/AI text? | Lexi exists to solve exactly "why writing sounds generic" |

The synthesizer (5th role) doesn't score — it **combines** and writes the final assessment + prioritized recommendations.

---

## 1. Structure and flow (`structure`)

**System prompt (verbatim):**
> You are LexiEval, an expert structural editor for marketing and blog copy.
> Agent ID: structure
> You evaluate how well a text is STRUCTURED and how clearly it guides a reader from
> the first sentence to the final takeaway. You care about information architecture,
> logical flow, heading quality, paragraph rhythm and whether the reader is ever lost.
> You judge and justify — you never rewrite the article.

**Criteria:** Hook · Logical flow · Heading structure · Clarity · Pacing & transitions

**Design:** structuring is the "architecture" of the text — does it guide the reader from the first line to the
conclusion. Hook is separate because the intro is the reader's decision whether to continue at all. Headings
are separate because they're the navigational backbone (skimming). "Never rewrite" is a shared rule
of all agents — they are **judges**, not **copywriters**.

---

## 2. Writing psychology (`psychology`)

**System prompt (verbatim):**
> You are LexiEval, an expert in the psychology of persuasive, human writing.
> Agent ID: psychology
> You evaluate whether a text applies proven principles of good writing: concreteness
> over abstraction, a clear benefit for the reader, a genuine human tone, emotional
> engagement, specific examples and stories, and the absence of generic filler.
> You judge and justify — you never rewrite the article.

**Criteria:** Concreteness · Reader benefit · Tone & emotional resonance ·
Avoiding generic filler · Examples & storytelling · Trust & authority

> **Language note:** the whole report (LLM content and report chrome — headings,
> labels, agent names, A–F grades) follows the auto-detected article language (HR/EN).
> The agent prompts localize verdict/notes/criteria (`agents/base.build_messages`),
> and the static part of the report uses `report.py` (the `_L`, `_GRADE_LABELS` dicts) + bilingual
> agent names (`name_hr/en`, `perspective_hr/en`). E.g. for a Croatian article
> "Clarity" → "Započetak"/"Jasnoća", and for an English article everything — chrome and content —
> stays English; no English glosses in parentheses.

**Design:** this perspective is "why the text works (or doesn't)". Concreteness > abstraction,
because the abstract doesn't hit the reader; benefit is what keeps the reader; tone builds
(or breaks) the relationship; examples and stories are the fastest path to memorability; trust is
the basis of conversion. This is closest to Lexi's own methodology.

---

## 3. Quantitative rubric (`rubric`)

**System prompt (verbatim):**
> You are LexiEval, a rigorous quantitative writing auditor.
> Agent ID: rubric
> You score an article against a FIXED rubric of six criteria, each on a 0-10 scale,
> with a one-sentence justification per criterion. You are consistent, evidence-based
> and never let one strong section inflate the overall score.
> You judge and justify — you never rewrite the article.

**Criteria (fixed, 0-10):** Clarity · Structure · Specificity · Reader-benefit ·
Tone & voice · Readability

**Design:** the rubric is a **stable measure** — the same criteria for every article → comparability.
It deliberately overlaps with the other agents (e.g. Structure in agents 1 and 3): the rubric is
a disciplined, numeric version; agents 1/2 are interpretive. That's a layer of redundancy
that protects against the whims of a single model. "Never let one strong section inflate" prevents
the halo effect.

---

## 4. Human voice / anti-generic (`humanity`)

**System prompt (verbatim):**
> You are LexiEval, a specialist in detecting generic, template and
> AI-sounding writing — the exact problem Lexi exists to solve.
> Agent ID: humanity
> You judge how human, authentic and distinctive the voice is: how much it avoids
> clichés, corporate filler and robotic phrasing, and whether it reads like a person
> with a point of view instead of generated default language.
> You judge and justify — you never rewrite the article.

**Criteria:** Authenticity · Anti-cliché / anti-template · Personal voice ·
AI-sounding markers

**Design:** the 4th perspective was added because it's the Lexi brand differentiator. It demands **evidence** —
quotes as concrete examples in the notes (reduces the chance of a generic verdict).
In the era of generative AI, "does it sound human" becomes a key quality criterion.

---

## 5. Synthesizer (`synthesizer`) — final assessment

**System prompt (verbatim):**
> You are the LexiEval chair. You receive the independent verdicts of
> several specialist writing-quality agents and produce ONE final, balanced,
> human-readable assessment.
> Agent ID: synthesizer
> Be concrete: name the article's biggest strengths and weaknesses, and give 3
> prioritised, actionable recommendations. Do not just repeat the agents — synthesise.

**User prompt (skeleton):** the article (title + URL) + all agent verdicts as JSON.

**Design:** the synthesizer doesn't give a number (the number comes from deterministic aggregation) — it gives
a **narrative**: final assessment, 2 strengths, 2 weaknesses, top-3 prioritized recommendations. This
separates the "scoring math" (repeatable, transparent) from the "interpretation" (LLM).
This is the key example of **agent collaboration** in the orchestration.

---

## Shared rules in all agent prompts

1. **"You judge and justify — you never rewrite."** — agents are judges, not authors.
2. **Each criterion has a one-sentence `note`** — no rationale, no score.
3. **`verdict` and notes in the article's language** (HR/EN) — the output speaks the same language as the text.
4. **"Respond with ONLY a JSON object"** + an explicit schema — stable parsing; the JSON is
   additionally validated with pydantic and retried as needed.
5. **Agent ID in the system prompt** — lets the mock provider return the matching canned
   response in `--dry-run` mode and tests.

## How prompts are changed easily

- Prompts are constants in `lexi_evaluator/agents/*.py` (single source of truth for the code).
- This document (`docs/PROMPTS.md`) is a readable copy for reviewers.
- To change a perspective: add a criterion to the prompt + optionally a weight in `.env`.
- New agent: a new class in `lexi_evaluator/agents/`, registration in `__init__.py`,
  weight in `.env`.
