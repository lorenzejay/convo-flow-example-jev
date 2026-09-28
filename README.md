# CrewAI Conversational Flows × Jev

A small, runnable example that uses TypeSafe's Jev model to route support turns and check whether an item-specific return request is ready to proceed inside a real CrewAI conversational flow.

![Illustrative routing walkthrough](docs/demo.gif)

**The GIF shows the earlier three-turn, route-only illustration. Its timings, costs, probabilities and confidence scores are authored, not live measurements.** The Python program now makes actual Jev requests for three questions per turn and prints the returned answers, measured request latency and estimated cost.

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

The program sends four support messages in one session. Order #4021 contains three blue products:

1. “Where are my Studio headphones?”
2. “They arrived damaged. Can I return them?”
3. “Can I return one of the other blue items too?”
4. “I mean the Sport Earbuds.”

Each turn makes one request to `https://api.typesafe.ai/v1/systemone` using `jev-latest`. The request sends conversation history, the sample order, a Choice question for `order`/`returns`/`clarify`, and two yes/no questions: whether this is an item-specific return request and whether one order item is identified. A return request with an unidentified item goes to `clarify`. General return-policy questions can reach `returns` without identifying an item.

Handlers return sample replies; they never modify orders or initiate refunds. Replace them with your own read-only tools or agent calls as needed. No OpenAI key is needed for this example's routing or replies.

## Check it without an API key

```sh
uv run python smoke_check.py
```

This runs the real CrewAI lifecycle with mocked HTTP responses. It checks that the ambiguous third turn reaches `clarify` even when Jev chooses `returns`, and that the resolved fourth turn reaches `returns`. No model API requests are made. Installing dependencies still requires network access on the first run.

## Evaluate the router

The [support evaluation](docs/support-evaluation.md) compares Jev with GPT-6 Luna and Astra on 13 authored return-readiness conversations. The earlier 20-case, route-only result remains in that document as historical context.

```sh
# Validate the dataset and scoring without API calls.
python3 eval_router.py --check
# Compare return readiness: requires TYPESAFE_API_KEY and OPENAI_API_KEY.
uv run --env-file .env --no-project python3 eval_router.py
# Jev only:
uv run --env-file .env --no-project python3 eval_router.py --models jev
```

The evaluator defaults to `return_readiness` and saves raw responses, usage, timings and scores under git-ignored `eval_results/`. These authored cases are a diagnostic; they cannot establish production accuracy.

## How routing works

```text
handle_turn(message)
  → route_turn(): history + order + three typed questions → Jev
  → validate Choice and two yes/no answers
  → returns + item-specific request + unidentified item ? clarify : choice
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

These JSON values are illustrative. Confidence is a separate statistic derived by TypeSafe from the probability distribution, not the winning probability or a guarantee of correctness. This demo does not use a route-confidence threshold; the previous 0.50 override incorrectly clarified a straightforward order question in one live run.

The original Choice answer stays in `decision["answer"]`, even when the item check selects a different handler. Missing or invalid answer fields fail before a handler executes.

## Measurement and configuration

- `TYPESAFE_API_KEY`: required for real requests; `.env` is git-ignored.
- `JEV_MODEL`: defaults to `jev-latest`.
- `JEV_INPUT_USD_PER_MILLION`: defaults to `0.042`; update it to your applicable pricing.
- `latency_ms`: wall-clock time for the HTTP request and JSON response.
- `estimated_cost_usd`: reported input tokens multiplied by the configured input rate. Assumes zero output-token cost; excludes tools, infrastructure and handler work.

The flow lifecycle is checked with mocked responses, and the [support evaluation](docs/support-evaluation.md) contains live readiness measurements. The GIF's LLM comparison remains illustrative. `flow.py` calls Jev only. Tracing and CrewAI telemetry are disabled by default unless you explicitly enable them in your environment.

## Files

- `flow.py`: actual CrewAI flow and TypeSafe HTTP call.
- `scenario.json`: sample conversation, order state, and authored visual fixtures.
- `smoke_check.py`: no-key lifecycle and item-readiness check.
- `eval_router.py` and `eval_cases.json`: support readiness comparison and authored cases.
- `docs/support-evaluation.md`: payload audit and live readiness results.
- `docs/demo.gif`: 18-second, 1080p walkthrough.

## References

- [CrewAI conversational flows](https://docs.crewai.com/en/guides/flows/conversational-flows)
- [TypeSafe API](https://docs.typesafe.ai/api)
- [TypeSafe confidence](https://docs.typesafe.ai/confidence)
