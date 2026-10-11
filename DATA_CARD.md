# Data card

## Study and scope

This release accompanies Shen et al. (2026), *Ethical evaluation of large language models for scientometrics: a multidimensional perspective*, *Scientometrics*, 131, 7001-7024. DOI: https://doi.org/10.1007/s11192-026-05773-0.

The benchmark consists of constructed research-evaluation scenarios. It does not contain authentic institutional evaluation records or establish the suitability of a model for consequential decisions. Intended uses include examining model behavior under the released rubric, reproducing descriptive summaries, and investigating evaluation methods.

## Construction and dimensions

The paper describes adapting risk logic from SafeBench, PrivacyMind, MoralBench, JADE, and ALI-Agent. Prompts were rewritten around publications, citations, journals, funding, peer review, institutional rankings, and bibliographic metadata, rather than used as unchanged source-resource test items. The dataset includes 300 prompts per dimension, or 1,500 in total. See the paper's construction protocol and supplementary materials for source references and filtering criteria.

| Dimension | Stored label | Dataset file | Scenario coverage |
| --- | --- | --- | --- |
| Content Safety | `content_safety` | `content_safety.csv` | Citation authenticity, reference verification, fabricated metrics, and misleading synthesis. |
| Privacy Protection | `privacy` | `privacy_protection.csv` | Confidential manuscripts and funding records, reviewer or author inference, and re-identification from sparse metadata. |
| Ethics and Bias | `ethics_bias` | `ethics_and_bias.csv` | Field normalization, coverage and language bias, identity and institutional bias, and interdisciplinary comparisons. |
| Robustness | `robustness` | `robustness.csv` | Structured prompt injection, adversarial input, metric gaming, and ranking manipulation. |
| Value Alignment | `values` | `value_alignment.csv` | Academic integrity, transparent indicator use, conflicts of interest, and accountability. |

`source_dataset` stores internal construction categories (`content_safety`, `privacy_safety`, `bias_safety`, `bias_safety/JADE`, or `value_safety`). These are not literal upstream dataset filenames or source-item identifiers. `source_logic` and `adaptation_operation` describe how the risk scenario was translated into the scientometric task. The release should not be treated as a record-level map back to every source resource.

## Model responses and automated scoring

Eight model families were evaluated across three runs. The release contains 35,997 valid answers out of 36,000 expected answers. Claude Sonnet 4 returned no answer for PR-298 in each run; these three records were not imputed. The primary scoring file contains 35,997 GPT-5.5 scores. The DeepSeek-v4-pro and Qwen3.6-plus auxiliary files each contain 11,999 run-1 scores and are separate sensitivity checks.

The scoring prompt uses `expected_behavior`, `risk_boundary`, and `safe_alternative_required`, together with the original prompt and answer. Other tags describe sampling and analysis conditions. The evaluated model's identity is not supplied in the judge prompt. The released scores are output observations under the specified rubric, models, and access conditions, not measurements of model training causes.

| Scoring field | Interpretation |
| --- | --- |
| `score` | Numeric 0-10 rubric score; higher values indicate stronger compliance with the evaluated ethical criteria. |
| `behavior_match` | `yes`, `partial`, or `no`: whether the expected response behavior was followed. |
| `unsafe_compliance` | Automated annotation of unsafe assistance; released values include `yes`, `partial`, and `no`. This is not interchangeable with the experts' binary unsafe-error field. |
| `safe_alternative_present` | `yes`, `partial`, `no`, or `not_required`; records the automated safe-alternative judgment. |
| `status` | `scored` in the primary release and `ok` in auxiliary releases indicate successful processing. A newly run script can also write `parse_failed: ...`. |

Boolean strings in rubric metadata vary in capitalization between files and should be interpreted case-insensitively. Text fields may contain mixed English and Chinese, Markdown, embedded instructions, and multiline answers; CSV readers must preserve quoting and UTF-8 encoding.

## Human validation

The merged file contains 250 selected items, 50 per dimension, each paired with eight run-1 answers: 2,000 item-response pairs, with 400 pairs per dimension. Each pair has scores and categorical labels from three experts, represented by the stable anonymous IDs E1, E2, and E3. `human_mean_score` is their arithmetic mean. The manuscript describes independent blinded scoring without access to model identities, automated scores or reasons, or other experts' ratings. The merged release restores model and automated-score fields for analysis; it is not the original blinded annotation interface.

The subset was stratified by dimension and rubric/analysis conditions, including automated score bands; it is not a simple random sample of all 35,997 answers. Full-range human-automated correlations should be interpreted together with the score distribution, lower within-band correlations, and disagreement cases in the paper. Model-mean ranking agreement does not establish perfect agreement for individual answers. This release contains the original three-expert validation, not a completed independent external re-annotation experiment.

`unsafe_error_E1` through `unsafe_error_E3` are expert judgments about unsafe errors. `missing_safe_alternative_E1` through `missing_safe_alternative_E3` concern inadequate or absent required safe alternatives. The latter field showed low expert agreement in the published reanalysis (Fleiss' kappa 0.164; mean pairwise weighted kappa 0.099) and is retained as a diagnostic annotation. It must not be promoted as strong reliability evidence or simply equated with the inverse of the automated presence field.

## Anonymization and limitations

Expert names and contact details are not included. The repository uses stable anonymous expert labels and contains no API credentials. Prompts are constructed scenarios, so names or identifiers appearing inside them should not be interpreted as factual institutional records. Model-generated assertions, references, identifiers, and advice are unverified model output, and may be inaccurate or unsafe.

Coverage is limited to five defined dimensions, the selected model versions, and primarily English scenarios with some mixed-language contexts. Scores depend on the rubric and evaluator. Repeated API runs may differ because of service, version, or decoding changes. A current rerun is not a reconstruction of the historical model service. The dataset does not support universal model rankings, population-level incident rates, or unrestricted deployment claims.

## Reuse and licensing

The repository includes an MIT license. That notice does not replace upstream source-resource licenses, model-provider terms, or publication rights. Users should consult the cited source resources and the relevant model providers' terms when redistributing or using generated answers. Figure provenance and publication attribution are recorded in [assets/figures/README.md](assets/figures/README.md). The publisher's typeset article is not included in this repository.

Do not treat unsafe benchmark requests or model responses as operational instructions, and do not use the constructed records to make claims about real people or institutions. Report suspected data errors through GitHub Issues without including private personal information or API credentials.
