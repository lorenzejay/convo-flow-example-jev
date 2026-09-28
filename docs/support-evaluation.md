# Support return readiness: what we checked

The current runnable flow asks Jev three questions per turn against the same conversation and multi-item order: the requested help (`choice`), whether the user asks about returning a particular item (`noul`), and whether exactly one order item is identified (`noul`). The application routes an item-specific return request with an unidentified item to `clarify`; otherwise it follows the Choice route. This uses the [TypeSafe API's](https://docs.typesafe.ai/api) documented map of typed questions. The question keys are response identifiers; their instructions carry the meaning.

In a live four-turn CrewAI run on September 27, 2026, Jev selected `order → returns → clarify → returns`. On the third turn, its raw Choice was `returns`, but the item-identification answer was 0.15, so the application asked for clarification. Once the customer specified the Sport Earbuds, the return-help handler ran. All handlers remain read-only. This gate is a demonstration of conversational readiness, not authorization to create returns or refunds.

We compared Jev with GPT-6 Luna and Astra on 13 authored conversations using the same order and decision contract. The following figures come from one live call per case; labels were authored, not independently adjudicated. Costs use returned usage and configured list rates and exclude handler work.

| Model | Correct final route | Median HTTP round trip | p95 | Estimated USD / 1,000 calls |
| --- | ---: | ---: | ---: | ---: |
| Jev `jev-1.13.0` | 12/13 | 159 ms | 508 ms | $0.0261 |
| GPT-6 Luna, reasoning `none` | 11/13 | 944 ms | 1,193 ms | $0.0470 |
| GPT-6 Astra, reasoning `low` | 13/13 | 1,673 ms | 3,578 ms | $4.7508 |

Jev's miss matters: after the customer discussed two damaged blue items, “Start a return for the blue one” still produced an item-identified answer above 0.5, so the final route was `returns` rather than `clarify`. Luna unnecessarily clarified two general return-policy questions. Astra made no errors in this small set. Raw responses and timings are in git-ignored `eval_results/20260928T020806Z/`. The figures do not justify using this gate alone before a real order mutation; a return action would also need deterministic item selection and explicit confirmation.

Run the current comparison with `uv run --env-file .env --no-project python3 eval_router.py`. Use `--task support_demo` to reproduce the earlier router-only contract below.

## Earlier one-question router

The earlier flow asked one Choice question per customer turn. Jev chose `order`, `returns`, or `clarify`; the matching CrewAI listener supplied a sample reply. The fixed order record was illustrative. No handler changed an order or started a refund.

## Is the Jev request correct?

Yes, that request shape matched the [TypeSafe API reference](https://docs.typesafe.ai/api): `POST /v1/systemone` with `model`, an object-valued `state`, and a `questions` map containing a `choice` question. The `criteria` object mapped each allowed route to its description. TypeSafe's [State guide](https://docs.typesafe.ai/concepts/state) shows a support conversation and related order in one object. The `route` question key identified where to read the answer in `answers`; the choice *instructions and criteria* carried the routing meaning.

`SupportFlow.handle_turn()` appends the latest user message before calling `route_turn()`. The payload contains the conversation so far, including the new message, plus the same sample order each turn. CrewAI uses the nonempty string returned by `route_turn()` to dispatch `@listen("order")`, `@listen("returns")`, or `@listen("clarify")`. The earlier live run selected those three handlers in sequence; the API returned model `jev-1.13.0`.

The earlier code also substituted `clarify` if TypeSafe confidence fell below 0.50. We removed this override in the current flow after it incorrectly clarified a straightforward order question in a live run. Confidence summarizes the Choice distribution and is not a probability that the chosen handler is correct. See [TypeSafe's confidence guide](https://docs.typesafe.ai/confidence).

The payload was **schema-valid and exercised against the live API**. That did not establish that every future support message would reach the right handler. In particular, the old `clarify` criterion mixed unclear intent with an unidentified item; the current flow separates those decisions. The instruction to treat messages as data is useful, but is not a guarantee against adversarial text.

## Small comparison on this exact contract

The [authored case set](../eval_cases.json) contains 20 `support_demo` messages spanning direct questions, follow-ups, corrections, negation, multilingual requests, ambiguity, unsupported requests and embedded routing directives. All three models saw the same conversation, order, route descriptions and instructions. The numbers below are the support-only subset of a 40-case live run on September 27, 2026. It is a diagnostic sample, with one call per case; its labels were not independently adjudicated.

| Model | Correct | Median HTTP round trip | p95 | Estimated USD / 1,000 calls |
| --- | ---: | ---: | ---: | ---: |
| Jev `jev-1.13.0` | 20/20 | 153 ms | 195 ms | $0.0205 |
| GPT-6 Luna, reasoning `none` | 20/20 | 834 ms | 993 ms | $0.0272 |
| GPT-6 Astra, reasoning `low` | 20/20 | 1,523 ms | 2,567 ms | $2.7825 |

Jev was fastest on these cases, but all models reached the ceiling. The sample provides no evidence of a routing-quality difference. No model returned an invalid route or failed a request. Jev's lowest confidence among the 20 was 0.82, so the 0.50 override changed no case. The estimated cost uses returned token usage and [TypeSafe](https://docs.typesafe.ai/models) and [OpenAI](https://developers.openai.com/api/docs/pricing) list prices. It excludes handlers, infrastructure and any provider discounts.

Run the support-only comparison with:

```sh
python3 eval_router.py --check
uv run --env-file .env --no-project python3 eval_router.py --task support_demo
```

The evaluator now selects `return_readiness` by default. `--task support_demo` selects this historical 20-case task; `--task saas_triage` selects the separate SaaS experiment. Raw provider responses, usage and timing for the earlier run are in git-ignored `eval_results/pilot-2026-09-27/`. The wider [40-case](evaluation.md) and [BANKING77](banking77-evaluation.md) studies remain research records; they are not additional use cases in the runnable CrewAI flow.

The earlier router-only set reached a ceiling for all three models. The new readiness set tests a distinct decision inside the same support use case and exposes a consequential ambiguity error. The next quality test should use reviewed support conversations and a defined cost for wrong handoffs before adding any real return action.
