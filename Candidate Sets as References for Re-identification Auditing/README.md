# Candidate Sets as References for Re-identification Auditing

**Separating Information Retention from Attacker Performance in Controlled Worlds**

Ming-Han Tsai, Feng Chia University. Fixed evaluation dataset accompanying the manuscript, release 2026-11-13.

This release contains the existing evaluation questions, exact frozen model-visible messages, reference candidate sets, conditional identity distributions, and scoring documentation. It supports evaluation on the same test instances. This dataset folder does not contain generation code; the companion world generator is provided separately in [`../world_generator/`](../world_generator/README.md).

## What is included

| Collection | Worlds | Question or message records |
|---|---:|---:|
| Main evaluation | 384 | 3,072 question presentations: 2 presentations × 4 conditions per world |
| Main frozen messages | Same 384 | 6,144 records preserving both Luna/Haiku and DeepSeek prompt contracts |
| Solver-assisted diagnostic | 96 drawn from the main worlds | 384 constraint-extraction messages across D/I/SD/SI |
| Step-checking prompt diagnostic | 48 additional worlds | 192 messages: D/I × standard/step-checking |

The 384 main worlds comprise 124 temporal, 129 directed-relation, and 131 group-condition worlds. Every world has 20 synthetic candidates. D and I identify one candidate; SD and SI retain five candidates with conditional probability 0.2 each. The original source label S is displayed as SD.

The 6,144 main message records are prompt-contract variants, not 6,144 independent questions. Each Luna/Haiku message is shared by those two models, and each DeepSeek message is shared by its none/low settings. The manuscript's main matrix has 12,288 model-condition cells.

## Files

- `inputs/`: gzip-compressed JSON Lines containing frozen messages and request metadata. Each line is one message record.
- `reference_answers/`: reference answers and sampled targets, stored separately from model inputs.
- `examples/`: one readable input example and its separate answer file.
- `DATASET_INDEX.json`: collection counts and data-file inventory.
- `SCHEMA.md`: field descriptions and usage.
- `SCORING.md`: scoring rules and limits of historical reproduction.
- `PROVENANCE.json` and `source_member_hashes.jsonl.gz`: source archive and selected-member checksums.
- `VALIDATION.json`: checks performed for this export.
- `SHA256SUMS`: SHA256 checksums of the release files.

## Reading the data

JSON Lines files are UTF-8; gzip is standard compression, not a proprietary format.

```python
import gzip
import json

with gzip.open("inputs/main_luna_haiku_coded/part-01.jsonl.gz", "rt", encoding="utf-8") as f:
    record = json.loads(next(f))
messages = record["messages"]
```

Submit only `messages` to a model. Join its output to the reference answers by `question_id`. Use `record_id` to distinguish prompt variants. Do not send the reference answers, sampled target, or other conditions from the same world to the model. A new evaluation must record its model settings and its target-independent tie policy.

The inputs preserve the actual system and user message strings. Historical requested model aliases are retained in request metadata; they are not assertions that those API aliases remain available. Recorded resolved versions and providers are described in the manuscript.

## Scope and provenance

The data were extracted from the existing author-review archive `Paper1_Question_Review_Complete_20261031_final.zip`. No worlds, questions, or reference answers were regenerated. No model calls or new scientific comparisons were performed for this release.

The release contains synthetic data only. This folder excludes generation code, API credentials, model response logs, unrelated pilot studies, and unpublished development drafts; the repository provides generation code separately in [`../world_generator/`](../world_generator/README.md). This is an evaluation-input release, not a complete reconstruction package for all original API executions. The validation report records export-integrity and reference-consistency checks; it is not a new independent semantic validation.

Contact: minghtsai@fcu.edu.tw.
