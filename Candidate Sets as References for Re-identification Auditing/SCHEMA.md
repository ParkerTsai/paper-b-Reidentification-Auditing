# Data schema

## Input records

| Field | Meaning |
|---|---|
| record_id | Original stable ID for a frozen message variant |
| question_id | Join key for the corresponding reference answer |
| world_id | Original world identifier; shared across conditions |
| family | temporal, graph, or boolean; boolean denotes group-condition worlds |
| presentation | coded or lifelike |
| condition | D, I, SD, or SI |
| source_condition | Original condition label, including S for SD |
| task | identity_inference or constraint_extraction |
| prompt_variant | Original variant label; null where the source does not define one |
| messages | Exact original system/user messages; only this field is model input |
| messages_sha256 | SHA256 of canonical JSON serialization of messages |
| requested_settings | Original model alias, reasoning parameters, output cap and request ID |

The message hash uses UTF-8 and Python JSON settings `ensure_ascii=False, sort_keys=True, separators=(",", ":")`. The strings within messages remain unchanged.

The user-message content is a JSON string containing the public information, candidate list, release and response schema. The system instruction is preserved as a separate system message. Read the original messages instead of synthesizing a new payload from reference metadata.

## Reference answers

| Field | Meaning |
|---|---|
| question_id | Join key shared with input records |
| world_id, family, presentation, condition | Experimental identifiers |
| candidate_ids | The full 20-person roster in its original order |
| compatible_ids | Complete supported candidate set |
| probabilities | Reference conditional probability for every candidate ID |
| sampled_target_id | Actual sampled target, used only by the evaluator |
| expected_ast | Reference constraint AST, present only in the solver diagnostic |

The main answers cover 3,072 world/presentation/condition combinations. Both model-specific prompt contracts join to these answers. The solver diagnostic has 384 reference answers. The prompt diagnostic has 96 reference answers shared by its standard and step-checking prompt variants.

All reference probabilities assume the stated uniform target prior and deterministic observation mechanism. A sampled target is one realized identity; it must not replace the complete compatible set as the answer to a multi-candidate question.

## Diagnostic tasks

The solver diagnostic asks the model to extract constraints into an AST. Its `expected_ast` is the appropriate extraction reference; its compatible set is the downstream solver reference. Do not score the extraction response as if the model had been asked to output candidate probabilities.

The prompt diagnostic uses two prompt variants per D/I observation. Preserve the variant labels and do not count the two variants as independent worlds.
