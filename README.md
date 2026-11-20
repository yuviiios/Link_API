# Website Link Analysis API

FastAPI analyzes the visible content of a public HTML page and returns brand and competitor insights, five platform-specific search queries, SEO recommendations, up to five services, and target audience segments.

## Setup

Use Python 3.11 or newer.

```shell
python -m venv .venv
```

Activate the environment with `.venv\Scripts\Activate.ps1` on Windows or `source .venv/bin/activate` on macOS or Linux. Install dependencies, copy `.env.example` to `.env`, and set `GEMINI_API_KEY` using a key from [Google AI Studio](https://aistudio.google.com/apikey).

```shell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 4000
```

Open [interactive API documentation](http://localhost:4000/docs).

```shell
curl -X POST http://localhost:4000/link-analysis -H "Content-Type: application/json" -d '{"url":"https://www.python.org/"}'
```

See the [full example JSON response](examples/response.json) for a fictional studio. Status codes are 400 for unsupported or unsafe destinations, 422 for malformed inputs, 502 for unsuccessful fetches or invalid provider results, and 503 for unavailable or unconfigured model access.

## Evidence and scope

The application fetches one HTML page, validates each redirect destination, and resolves hostnames to vetted public addresses before connecting. The fetch is capped at 15 seconds and 1 MB. Extraction removes navigation, scripts, and duplicate text and retains up to 18,000 characters plus the title and meta description. JavaScript-only sites and access restrictions can result in insufficient content.

Gemini receives the extracted page as untrusted evidence and returns schema-constrained JSON, which the API validates with Pydantic. Services labeled as website-derived must contain a matching excerpt. Competitor suggestions and competitive hypotheses need independent verification. Search queries describe relevance and intent. Search volumes and ranking metrics are omitted.

## Model comparison

Published paid text pricing checked on November 20, 2026. USD per million tokens. Speed and task fit are qualitative estimates based on provider documentation. Website-analysis accuracy and latency require a representative live benchmark.

| Provider and model | Input / output | Context or input limit | Structured JSON | Expected speed and task fit |
| --- | ---: | ---: | --- | --- |
| Google Gemini 3.5 Flash-Lite | $0.30 / $2.50 | 1,048,576 | JSON Schema | Low-latency tier designed for extraction. First choice for the combined analysis. [Model](https://aistudio.google.com/docs/models/gemini-3.5-flash-lite) · [Pricing](https://aistudio.google.com/docs/pricing#gemini-3.5-flash-lite) · [JSON](https://aistudio.google.com/docs/structured-output) |
| Mistral Small 4 | $0.15 / $0.60 | 256K | Structured outputs | Low-cost candidate for extraction and generation. Check competitor relevance and SEO specificity on the same pages. [Model and pricing](https://docs.mistral.ai/models/mistral-small-4-0-26-03) |
| Anthropic Claude Sonnet 5.5 | $2.00 / $10.00 | 1M | Structured outputs | Higher-cost candidate for ambiguous pages. Measure response time and whether extra reasoning improves evidence fidelity. [Model and pricing](https://platform.claude.com/docs/en/models/sonnet-5-5/overview) · [JSON](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) |

Gemini 3.5 Flash-Lite is the initial default for its structured output, document extraction focus, and low-latency positioning. At an estimated 5,000 input tokens and 2,000 billable output tokens, standard model charges are approximately **$0.0065 per request**. A provisional planning estimate is **5–20 seconds end to end**, depending on website and model latency. The configured fetch and model budgets are 15 and 35 seconds respectively. Set `GEMINI_MODEL=gemini-3.1-flash-lite` to select the same-provider fallback manually. [Fallback model](https://aistudio.google.com/docs/models/gemini-3.1-flash-lite)

For production selection, run all three models against the same pages across industries and content lengths. Record p50 and p95 latency, valid-response rate, token charges, service evidence accuracy, competitor relevance, and human ratings of SEO specificity. Start with one request per analysis, limit output size, and cache validated results by extracted content hash plus model and prompt versions when repeat traffic justifies it.

## Verification and deployment

```shell
python -m pip install pytest
python -m pytest -q
```

Tests exercise the API with fixture-backed website and provider responses and cover unsafe addresses and upstream errors. [Verification log](examples/verification.txt). For a live smoke test, run the example request after configuring the Gemini key and verify that all five analysis sections are returned.

For a hosted Python service, install `requirements.txt`, store `GEMINI_API_KEY` as a secret environment variable, and start `uvicorn app.main:app --host 0.0.0.0 --port "$PORT"` on a Linux host. Enable TLS and apply rate limiting and private-network egress restrictions at the hosting boundary before exposing the endpoint publicly. Verify the deployed `/docs` and `/link-analysis` using the assigned public hostname.
