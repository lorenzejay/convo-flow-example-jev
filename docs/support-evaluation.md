# Support return-readiness evaluation

The runnable CrewAI flow asks Jev three questions against the same conversation and multi-item order: a `choice` for support intent, a `noul` for whether the customer requests help with a particular item, and a `choice` for the exact item or `unresolved`. The application asks for clarification when an item-specific return request has no uniquely selected item or the item Choice confidence is below 0.60. It does not start a return or refund. The request follows the [TypeSafe API's typed-question format](https://docs.typesafe.ai/api); question keys identify response fields, while instructions and criteria define the decisions.

In the four-turn live demo, the final routes were `order → returns → clarify → returns`. The third turn had a clear return intent but two possible remaining blue items, so the item Choice was `unresolved`. The follow-up identified the Sport Earbuds.

The authored set now has 31 return-readiness cases: 13 original development cases, 8 added after the first ambiguity miss, and 10 added after trying explicit item selection. Cases include clear items, ambiguous references, unsupported attributes, corrections, general policy questions, and follow-up resolution. Each case labels the expected raw route, item-action answer, exact item, and final route. The later groups are **exploratory validation**, not a blind holdout. Labels have not been independently adjudicated.

One live request per case on September 27, 2026 produced:

| Model | Correct final route | Raw item Choice | Median HTTP round trip | p95 | Estimated USD / 1,000 calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Jev `jev-1.13.0` | 31/31 | 30/31 | 163 ms | 208 ms | $0.0308 |
| GPT-6 Luna, reasoning `none` | 31/31 | 31/31 | 924 ms | 1,459 ms | $0.0552 |
| GPT-6 Astra, reasoning `low` | 31/31 | 31/31 | 1,887 ms | 3,024 ms | $5.5158 |

Jev also made 93/93 correct **final-route** decisions across three repeats of the 31 cases, with no request errors. Its raw item Choice still selected the Sport Earbuds for “the smaller one” three times even though the order had no size data; Choice confidence was low enough for the application's 0.60 abstention rule to ask for clarification. This threshold was selected after inspecting these synthetic cases, so the 93/93 result is a tuned replay, not an unbiased estimate of future accuracy. On this set, all three models hit the final-route ceiling; it supports a latency and estimated-cost comparison, not a quality ranking.

## Where Jev fits in a CrewAI flow

**Turn-level decisions with a small set of answers are the demonstrated fit.** CrewAI's [conversational flow lifecycle](https://docs.crewai.com/en/guides/flows/conversational-flows) adds the user message to session history before routing, then dispatches the selected `@listen` handler. Here Jev reads that history and the order once, answers three [typed questions](https://docs.typesafe.ai/api), and the flow combines them into a handler route. This is useful when a follow-up changes intent or names an item indirectly, and when an unresolved reference should pause item-specific help. On our authored cases, Jev matched the frontier models' final routes with lower measured request latency and estimated cost; the fixture shows no quality advantage.

**An abstention path matters more than a forced answer.** The explicit `unresolved` item option makes ambiguity visible, and the flow asks for clarification when item Choice confidence is below 0.60. The “smaller one” failure shows why recording the raw item answer alongside the final route matters. [TypeSafe describes confidence as a summary of the Choice distribution](https://docs.typesafe.ai/confidence), so this cutoff is a demo policy to test on new conversations, not a probability that an item match is correct.

The same pattern is worth evaluating at other bounded CrewAI decision points, such as choosing a specialist, deciding whether a request has enough information for a tool, or deciding whether to ask for human review. Those are candidates, not results measured here. Keep order IDs, return-window arithmetic, policy enforcement, and any actual mutation in deterministic code with explicit confirmation; use a generative handler when the flow needs a customer-facing answer. TypeSafe's [Jev 1.13 limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) likewise recommend code for numeric/date work and a generative model for writing text.

The earlier yes/no item-identification check scored 12/13 on the original cases at a 0.50 cutoff. Repeated testing exposed another ambiguity pattern and showed that changing its threshold could make the existing fixture perfect without improving the underlying model. Explicit item selection makes the answer auditable; the stricter abstention rule limits when the flow proceeds with item-specific help.

The evaluator stores raw responses, usage, errors, component scores, final routes, and timing under git-ignored `eval_results/`. The final one-pass comparison is `eval_results/20260928T031102Z/`; the three-repeat Jev run is `eval_results/20260928T031031Z/`. Estimated cost uses returned token usage and the configured [TypeSafe](https://docs.typesafe.ai/models) and [OpenAI](https://developers.openai.com/api/docs/pricing) list rates, excluding handler work and provider discounts. Request errors are counted separately from accuracy on completed responses.

Run the checks and comparison with:

```sh
python3 eval_router.py --check
uv run --env-file .env --no-project python3 eval_router.py --task return_readiness
```

The next useful evaluation is a reviewed sample of real support conversations, especially cases with several plausible items and missing order attributes. Freeze the decision rules before collecting that set, report false-ready returns and unnecessary clarifications separately, and retain the raw item labels so a correct final route cannot hide a wrong item selection.
