# Scientometric LLM Ethics Benchmark Data Release

This repository provides the benchmark prompts, model responses, scoring results, and two experiment-running scripts used in the associated manuscript workflow.

The release contains constructed benchmark materials rather than real institutional evaluation records. Human raters are represented only by anonymized labels, and the files do not include rater identities or API credentials.

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

The scripts use OpenAI-compatible chat-completion endpoints. They do not contain API keys. Configure credentials with environment variables such as `MODEL_API_KEY` / `MODEL_BASE_URL` for target-model response collection and `JUDGE_API_KEY` / `JUDGE_BASE_URL` for judge scoring. If provider-specific variables are not set, the scripts fall back to `OPENAI_API_KEY` and `OPENAI_BASE_URL`.

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

## Citation

Please cite the associated manuscript if you use this dataset.
