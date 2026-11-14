# Scoring specification

This document summarizes the rules in the accompanying manuscript. It does not include a generator or executable scoring implementation.

## Separate checks

The identity-inference response has two fields: `compatible_ids` and `probabilities`. Check set validity and probability validity separately. In particular, a correct set does not establish that the probability vector is correct.

A valid set field contains known candidate IDs without duplicates. Exact-set recovery is 1 only when it equals the reference compatible set; valid omissions, extra candidates, wrong sets and empty sets score 0.

A legal probability vector contains every candidate ID exactly once, finite numerical values in [0,1], and a total within 0.001 of 1. Invalid vectors are decision failures and are excluded from probability-error means. Report the number of legal vectors and all unavailable outcomes.

## Probability errors

For SD/SI, let C be the five-person reference support and p the raw legal probability vector:

- MSE5 = sum over i in C of (p_i - 0.2)^2 / 5.
- Outside-support mass = sum over i not in C of p_i.
- Full-distribution squared error R = sum over all 20 candidates of (p_i / s - q_i)^2, where s is the sum of p and q is the reference distribution. Only in-tolerance vectors are normalized for R.

Do not assign zero error to unavailable responses. An aggregate RMSE5, if reported, is the square root of the mean MSE5.

## Top-1 decisions

Top-1 is derived from the largest reported probability; the model is not asked for an additional single-person answer. The paper uses a world-specific priority fixed independently of the target to resolve ties. Unusable probabilities count as decision failures.

The historical tie-priority arrays are not present in the source question-review export and are not reconstructed here. To conduct a new evaluation, fix and document a target-independent tie policy before scoring, and use it consistently across paired conditions. The dataset supports such new evaluations, but it does not reproduce the paper's exact historical tie-resolved hit counts by itself. Do not assume that candidate order or lexicographic ID order was the original tie policy.

The optimal conditional single-guess success probability under q is max(q): 1 for D/I and 0.2 for SD/SI. This is distinct from the realized top-1 hit fraction in a finite set of worlds.

## Historical unavailable values

The original coded Luna/Haiku pipeline retained unscorable set fields as unknown. Three Luna cases were affected: world 0109 D and 0372 I contained prose before JSON, and 0269 D was truncated at the 1,200-token cap. The later lifelike and DeepSeek pipelines scored unscorable sets as zero. Preserve these distinctions when interpreting published results; a new evaluation should declare its own handling rules explicitly.

The paper averages exact-set scores within each world before paired comparisons. Do not treat multiple conditions, prompt variants, or model settings from the same world as independent samples.

## Limits

This question-bank release contains no original model response logs or per-response score tables. It supports rerunning evaluation on fixed inputs and checking outputs against the reference answers. Reproducing the published API responses, historical tie decisions and all statistical tables requires the original execution records.
