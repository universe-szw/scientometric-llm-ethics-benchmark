# Scientometric LLM Ethics Benchmark Data Release

This repository provides the benchmark prompts, model responses, scoring results, and two experiment-running scripts for the published study [Ethical evaluation of large language models for scientometrics: a multidimensional perspective](https://doi.org/10.1007/s11192-026-05773-0).

The release contains constructed benchmark materials rather than real institutional evaluation records. Human raters are represented only by anonymized labels, and the files do not include rater identities or API credentials.

## Maintenance

Zhewei Shen ([universe-szw](https://github.com/universe-szw)) has been responsible for and has maintained this project since its inception. During the initial paper data-release phase, commits used anonymous metadata, `The authors <authors@example.com>`. Following publication, Zhewei Shen continues public maintenance and engineering improvements under his own GitHub identity. The original commit history is preserved.

Please use GitHub issues to report problems with the data, scripts, or documentation.

## Directory structure

- `dataset/`: benchmark prompt CSV files for the five ethical dimensions.
- `model_responses/`: model response CSV files organized by ethical dimension.
- `scoring_results/`: AI-judge scoring files and the merged human-validation scoring file.
- `code/`: two Python scripts for generating model responses from a benchmark CSV and scoring model responses with a judge model.

## Contents

- Benchmark prompts: 1,500 items across five ethical dimensions.
- Model responses: 35,997 valid responses from eight model families across three runs.
- Scoring results: GPT-5.5 main judge scores, two auxiliary judge score files for run-one sensitivity checks, and 2,000 merged human-validation item-response pairs.
- Code: `run_model_responses.py` for collecting model responses and `run_judge_scoring.py` for scoring responses.

## Code usage

Run the commands from the repository root with Python 3.10 or later. Both scripts use only the Python standard library; no additional Python packages are required. Replace model identifiers with values supported by your API provider.

The scripts use OpenAI-compatible chat-completion endpoints. They do not contain API keys. Configure credentials with environment variables such as `MODEL_API_KEY` / `MODEL_BASE_URL` for target-model response collection and `JUDGE_API_KEY` / `JUDGE_BASE_URL` for judge scoring. If provider-specific variables are not set, the scripts fall back to `OPENAI_API_KEY` and `OPENAI_BASE_URL`.

For example, configure credentials in PowerShell for the current terminal session:

```powershell
$env:MODEL_API_KEY = Read-Host "Model API key"
$env:MODEL_BASE_URL = Read-Host "Model API base URL, including /v1 if required"
$env:JUDGE_API_KEY = Read-Host "Judge API key"
$env:JUDGE_BASE_URL = Read-Host "Judge API base URL, including /v1 if required"
```

The multiline examples below use Bash syntax. In PowerShell, enter each command on one line, omitting the backslashes.

Generate responses for one dataset CSV:

```bash
python code/run_model_responses.py \
  --dataset-csv dataset/content_safety.csv \
  --output-csv model_responses/example_model_responses.csv \
  --model <provider-model-id> \
  --evaluated-model-id <public-model-id> \
  --evaluated-model-name "<public model name>" \
  --run-id 1
```

Score a response CSV:

```bash
python code/run_judge_scoring.py \
  --responses-csv model_responses/example_model_responses.csv \
  --output-csv scoring_results/example_scores.csv \
  --judge-model <provider-judge-model-id> \
  --judge-model-id <public-judge-id>
```

Add `--dry-run --limit 1` to either command to check its input without making API requests or writing results. Use `--help` to inspect all options. To resume an interrupted run, use the same output file and identifiers with `--resume`; existing keys in that file are skipped.

Write new runs to separate output files to preserve the published results. Sampling settings are configurable through `--temperature`, `--top-p`, and `--max-tokens`; consult the paper and supplementary materials for the reported experimental conditions. New API runs may differ from the released responses and scores as model versions and service behavior change.

## Citation

Please cite the published article if you use this dataset or code:

Shen, Z., Liu, Y., Liu, Y., Wang, Z., & Yuan, S. (2026). Ethical evaluation of large language models for scientometrics: a multidimensional perspective. *Scientometrics, 131*, 7001-7024. https://doi.org/10.1007/s11192-026-05773-0
