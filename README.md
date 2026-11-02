# xDial Benefits Verification Engine

A small FastAPI service that analyzes a healthcare benefits-verification conversation and returns the next logical question for the agent to ask.

## Current approach

- `POST /next-question` accepts a conversation between an agent and an insurance representative.
- When `OPENAI_API_KEY` is configured, the service uses `gpt-4o-mini`.
- The model returns a structured response validated with Pydantic.
- If the API key is unavailable, the OpenAI package is not installed, or the LLM call fails, the service falls back to deterministic rule-based logic.
- `GET /health` reports whether the application is running in `llm` or `simulated` mode.
- LLM calls are fully asynchronous (`AsyncOpenAI`), so a slow model response never blocks the worker. Each call has a request timeout (`LLM_TIMEOUT_SECONDS`, default 10 s), automatic retries for transient errors (`LLM_MAX_RETRIES`, default 2) and a per-worker concurrency limit (`LLM_MAX_CONCURRENCY`, default 20). Temperature is 0 and output is capped at 100 tokens; empty or unparseable responses trigger the rule-based fallback.

## Installation and running the API

From the project root, install the dependencies, configure the OpenAI API key, and start the FastAPI development server:

```bash
pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env
uvicorn app.main:app --reload --env-file .env
```

Replace `sk-...` with a valid API key. Do not commit the `.env` file or expose the key in source control. If no API key is configured, the application runs in simulated mode and uses its rule-based fallback.

The API will be available at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Testing

With the server running, send a sample request:

```bash
curl -X POST "http://127.0.0.1:8000/next-question" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": [
      {
        "speaker": "agent",
        "text": "Can I verify benefits for John Smith?"
      },
      {
        "speaker": "insurance",
        "text": "Sure."
      },
      {
        "speaker": "agent",
        "text": "Is the deductible met?"
      },
      {
        "speaker": "insurance",
        "text": "No."
      },
      {
        "speaker": "agent",
        "text": "How much remains?"
      },
      {
        "speaker": "insurance",
        "text": "$850."
      }
    ]
  }'
```

Example response:

```json
{
  "next_question": "What is the remaining out-of-pocket maximum for this plan?"
}
```

The exact wording may vary when the LLM mode is enabled.

## How would I reduce hallucinations?

1. **Constrain the model to an approved verification workflow.** Define a fixed checklist—such as eligibility, effective dates, deductible, remaining deductible, copay, coinsurance, out-of-pocket maximum, and prior authorization—and instruct the model to select only the next missing item. This prevents it from inventing unrelated questions.

2. **Use structured output and validation.** The current implementation already parses the model response into a Pydantic schema. I would extend that schema to include an approved question ID, for example `COPAY` or `PRIOR_AUTHORIZATION`, and validate that the ID belongs to the checklist. The API could then render the final question from a trusted template instead of accepting arbitrary model-generated text.

3. **Ground the decision only in the transcript.** The prompt should explicitly state that the model must not assume facts that were not provided. If the conversation is ambiguous or incomplete, it should request clarification rather than infer an answer.

4. **Use deterministic settings and post-processing.** I would use a low temperature, reject empty or malformed responses, prevent repeated questions, and verify that the selected topic has not already been answered. If validation fails, the request should use the rule-based fallback.

5. **Test and monitor the workflow.** I would build a labeled test set containing normal, incomplete, contradictory, and noisy transcripts. In production, I would track invalid outputs, repeated questions, fallback frequency, and sampled conversations with sensitive data removed. Any prompt or model change would be evaluated against this test set before release.

For a healthcare workflow, the model should recommend the next question—not make coverage, eligibility, or clinical decisions. The insurance representative’s response and authoritative plan data remain the source of truth.

## How would I reduce token usage and inference costs?

- Send only the conversation turns needed to determine the next missing field. For long calls, maintain a compact structured state such as `{"deductible": "answered", "copay": "missing"}` and include only that state plus the most recent turns.
- Keep the system prompt short and avoid repeating instructions or examples on every request.
- Set a small maximum output length because the endpoint needs only one concise question.
- Continue using a smaller, lower-cost model such as `gpt-4o-mini` for this classification-style task.
- Use deterministic rules first for common cases and call the LLM only when the transcript is ambiguous. The current fallback can be expanded into this primary fast path.
- Cache results for identical normalized conversations, using a short TTL and an encrypted store appropriate for sensitive data. Do not place raw protected health information in cache keys or logs.
- Track tokens, latency, cost per request, cache hit rate, and the percentage of requests that require an LLM. These measurements show where optimization has the greatest impact.

## What would I change for 10,000 requests per hour?

10,000 requests per hour is about **2.8 requests per second on average**, but the system should be designed for much higher short-term bursts.

Before production deployment, I would:

1. **Keep external calls asynchronous and bounded.** The service already uses the asynchronous OpenAI client with timeouts, retries and a concurrency limit. At this volume I would tune those limits from load tests and add a circuit breaker so requests skip straight to the rule-based path while the provider is unhealthy.

2. **Run multiple stateless API instances.** Package the service in a container and deploy it behind a load balancer with horizontal autoscaling. Configure multiple workers per instance based on load testing rather than CPU count alone.

3. **Add resilience controls.** Set strict connection and response timeouts, retry only transient failures with exponential backoff and jitter, apply a concurrency limit, and use a circuit breaker when the model provider is unhealthy. The deterministic fallback should remain available.

4. **Protect the service.** Add authentication, per-client rate limits, request-size limits, input validation, TLS, secret management, and dependency scanning. Because transcripts may contain PHI, redact sensitive fields from logs and use compliant, encrypted infrastructure with appropriate retention policies and vendor agreements.

5. **Add observability.** Emit structured logs and metrics for request volume, p50/p95/p99 latency, error rate, LLM latency, token usage, fallback rate, and provider rate-limit responses. Add distributed tracing and alerts tied to service-level objectives.

6. **Load-test realistic traffic.** Test normal load, expected bursts, long transcripts, provider latency, and provider outages. Capacity should be based on measured p95 latency and peak concurrency, not only the hourly average.

7. **Separate work when latency allows.** If callers do not require an immediate response, place requests on a durable queue and process them with autoscaled workers. For this interactive voice-agent endpoint, I would normally keep the synchronous request path but use a bounded queue only for overload protection.

These changes keep the API responsive during traffic spikes, limit failures caused by the external LLM provider, and provide a safe fallback when the provider is unavailable.
