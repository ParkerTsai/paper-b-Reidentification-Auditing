# Disclosure scope and validation

This release implements the four artifact categories stated in the revised manuscript: fixed test inputs, reference answers, scoring specifications, and the world generator. It is not a release of model response logs or statistical results.

## Fixed evaluation data

`Candidate Sets as References for Re-identification Auditing/` is copied byte-for-byte from source commit `e6e9d35ccf84019fd9bdce7e6253df1435ee0ece` in ParkerTsai/reidentification-research. It includes 384 main worlds, both historical message contracts (6,144 message records, not independent worlds), solver-assisted diagnostic inputs for 96 of those worlds, and 192 prompt-diagnostic messages for 48 additional worlds. Reference answers, schema, scoring specification, source hashes, and original validation records are included. Its original README accurately describes that folder alone as excluding generation code; the generator is now supplied in the separate folder below.

## World generator

`world_generator/` contains the disclosed original main-world sources plus an offline portable adapter, original frozen mappings, frozen world data, and validation scripts. Python 3.10+ and the standard library suffice. Run `python generate.py --output NEW_DIRECTORY` from that folder. The output directory must not already exist. No model requests, API credentials, or network connection are needed.

The generator reproduces all 384 main worlds and both coded/lifelike presentation contracts. Previous disclosure validation matched all 384 worlds and 6,144 task payloads exactly and checked 1,536 counterfactual partitions. This packaging does not claim to repeat those expensive checks anew. The original frozen mapping is provided; the historical mapping-selection program was not recovered. The generator is not claimed to reconstruct the additional 48 diagnostic worlds; their frozen test messages and reference answers are supplied in the fixed dataset.

## Boundaries

No raw model responses, result statistics, account ledgers, credentials, unpublished unrelated research, or paid execution code are included. Do not submit reference answers or latent frozen-world truth as model input. Original sources and provenance are preserved, including historical version labels and access-status statements; this repository is public. Public availability does not imply a license beyond any explicit license supplied by the author.

The revised manuscript still cites the older `8ff59e...` repository snapshot. That immutable snapshot does not contain this generator; the author must update the data-availability URL to this repository or its final commit. This release does not edit the manuscript.

## Integrity

The fixed dataset contains its original SHA256SUMS. The generator contains its original SHA256SUMS for its base module; ALL_GENERATOR_SHA256SUMS additionally covers the later public-text solver verification files. These hashes describe exact files, not guarantees of new stochastic model output reproducibility.
