# Privacy Symposium paper: synthetic world generator

Companion to **Candidate Sets as References for Re-identification Auditing: Separating Information Retention from Attacker Performance in Controlled Worlds**.

This is an offline, study-specific source disclosure. It generates the paper's 384 main synthetic worlds and their paired coded/lifelike presentations. It does not call models, access credentials, or execute any paid requests. No real persons' records are included.

## Reproduce

Python 3.10+; standard library only:

```sh
python generate.py --output generated
```

The output directory must not exist. Runtime includes counterfactual partition checks and may take a few minutes. Outputs: `worlds.json`, `payloads.jsonl` (DeepSeek paired contract), `luna_haiku_payloads.jsonl` (original Luna/Haiku contract), `validation.json`. There are 1,536 paired rows (384 worlds × D/I/S/SI), corresponding to 3,072 presentations, not independent observations. Paper display SD corresponds to source S. These payloads are task content, not a current API execution configuration.

## Provenance and scope

`source_original/core_v85.py` and `payloads_v85.py` are byte-preserved sources from the original v8.5.4 freeze. Their internal older module descriptions/version strings are retained, not silently rewritten. `narrative_candidate.py` is the byte-preserved later lifelike presentation generator; its historical absolute paths are retained for provenance. **Do not run that original script directly.** The new portable `generate.py` imports only the original presentation functions and performs no historical executor operations.

The master seed is `v8.5-confirmatory-20261019-v1`, phase `confirmatory`; exact world IDs and original generated worlds are in `data/frozen_worlds.json`. Worlds include synthetic latent truth and target/tie-break information for offline verification. These fields must never be included in an attacker prompt; only `coded_payload` or `lifelike_payload` is the task presentation. `MAPPINGS.json` is the original mapping artifact, not a newly invented mapping. This package reproduces presentations from that frozen mapping; it does not claim regeneration of the mapping-selection history.

The included solver and utility modules are historical offline verification dependencies. `test_revision.py` is a historical test file; its original environment dependencies are not all included, so the supported portable validation entry point is `generate.py`.

This package does **not** reproduce stochastic model responses, original API usage/costs, or paper result tables. Historical model/routing fields inside original source describe old request templates, not promises of current availability. The main 384-world materials are the scope; additional prompt-diagnostic worlds and the model-output archive are not silently claimed to be included. Refer to the paper's separate evaluation dataset for frozen messages and reference answers.

## Release policy

Only this paper's offline source and synthetic inputs are included. No secrets, API executors, credentials, ledger, account settings, other research, or model response archive is bundled. No change to the existing private research repository is required. Public availability does not itself supply an open-source license; the author should choose licensing explicitly.

See `PROVENANCE.json` and `SHA256SUMS` for source identities and byte checks. See `VALIDATION_REPORT.json` for checks actually run for this disclosure, distinguished from historical checks.

## Verified disclosure build

All 384 frozen worlds were regenerated exactly (canonical equality). All 3,072 DeepSeek paired payloads and 3,072 Luna/Haiku coded/lifelike payloads matched the final review archive, total 6,144 exact task-payload matches. The contracts differ in the system sentence about aliases; the adapter preserves both rather than homogenizing historical prompts. Complete API-message serialization and stochastic outputs are not implied by payload equality. All 1,536 coded/lifelike counterfactual partitions matched and have support 1 for D/I and 5 for S/SI.
