# CrewAI Conversational Flows × Jev

A small, runnable example that uses TypeSafe's Jev model to choose a route inside a real CrewAI conversational flow.

![Illustrative routing walkthrough](docs/demo.gif)

**The GIF uses authored example timings, costs, probabilities and confidence scores. It is not a live benchmark.** The Python program makes actual Jev requests when you supply a key and prints the returned answer, measured request latency and estimated cost.

## Run with Jev

Requires Python 3.11–3.13, [uv](https://docs.astral.sh/uv/getting-started/installation/), and a TypeSafe API key.

```sh
git clone https://github.com/lorenzejay/convo-flow-example-jev.git
cd convo-flow-example-jev
uv sync
cp .env.example .env
# Set TYPESAFE_API_KEY in .env using your editor.
uv run --env-file .env python flow.py
```

The program sends three support messages in one session:

1. “Where are my headphones?”
2. “They arrived damaged. Can I return them?”
3. “What about the other one?”

Each turn makes one request to `https://api.typesafe.ai/v1/systemone` using `jev-latest`. It sends the conversation history, sample order data, and three allowed routes: `order`, `returns`, and `clarify`. Live model choices can differ from the illustrative replay.

Handlers return sample replies; they never modify orders or initiate refunds. Replace them with your own read-only tools or agent calls as needed. No OpenAI key is needed for this example's routing or replies.

## Check it without an API key

```sh
uv run python smoke_check.py
```

This runs the real CrewAI lifecycle with mocked HTTP responses. It checks that all three handlers execute, history is retained, provider output is preserved, and low confidence routes to clarification even when Jev's highest-probability choice is another route. No model API requests are made. Installing dependencies still requires network access on the first run.

## How routing works

```text
handle_turn(message)
  → route_turn(): history + allowed routes → Jev
  → validate choice, probabilities and confidence
  → confidence < 0.50 ? clarify : choice
  → @listen(selected_route)
  → append assistant reply and retain session state
```

Returning a non-empty route from `route_turn()` bypasses CrewAI's built-in LLM router. The `@listen` handler appends the assistant message; all turns share one session ID.

A Jev Choice answer contains:

```json
{
  "type": "choice",
  "choice": "returns",
  "probabilities": {"order": 0.01, "returns": 0.97, "clarify": 0.02},
  "confidence": 0.92
}
```

These JSON values are illustrative. Confidence is a separate statistic derived by TypeSafe from the probability distribution, not the winning probability or a guarantee of correctness. The `0.50` floor is this demo's policy; evaluate thresholds on your own data.

The original answer stays in `decision["answer"]`, even when the application policy selects a different handler. Missing or invalid answer fields fail before a handler executes.

## Measurement and configuration

- `TYPESAFE_API_KEY`: required for real requests; `.env` is git-ignored.
- `JEV_MODEL`: defaults to `jev-latest`.
- `JEV_INPUT_USD_PER_MILLION`: defaults to `0.042`; update it to your applicable pricing.
- `latency_ms`: wall-clock time for the HTTP request and JSON response.
- `estimated_cost_usd`: reported input tokens multiplied by the configured input rate. Assumes zero output-token cost; excludes tools, infrastructure and handler work.

The source was checked with mocked responses, not a live provider benchmark. The GIF's LLM comparison is illustrative; this repository's Python example calls Jev only. Tracing and CrewAI telemetry are disabled by default unless you explicitly enable them in your environment.

## Files

- `flow.py`: actual CrewAI flow and TypeSafe HTTP call.
- `scenario.json`: sample conversation, order state, and authored visual fixtures.
- `smoke_check.py`: no-key lifecycle and confidence-policy check.
- `docs/demo.gif`: 18-second, 1080p walkthrough.

## References

- [CrewAI conversational flows](https://docs.crewai.com/en/guides/flows/conversational-flows)
- [TypeSafe API](https://docs.typesafe.ai/api)
- [TypeSafe confidence](https://docs.typesafe.ai/confidence)
