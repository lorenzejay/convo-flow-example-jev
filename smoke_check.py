"""Exercise real CrewAI routing with mocked HTTP; never calls a model API."""
import contextlib
import io
import json
import os
from unittest.mock import patch
from uuid import uuid4

import flow


def main():
    history_lengths = []

    def mock_response(request, timeout):
        payload = json.loads(request.data)
        history_lengths.append(len(payload["state"]["messages"]))
        assert set(payload["questions"]) == {"route", "item_action", "item_identified"}
        turn = flow.SCENARIO["turns"][len(history_lengths) - 1]
        route_answer = {
            "type": "choice", "choice": turn["route"],
            "probabilities": turn["probabilities"], "confidence": turn["confidence"],
        }
        if len(history_lengths) == 1:
            route_answer.update(probabilities={"order": 0.62, "returns": 0.01, "clarify": 0.37},
                                confidence=0.35)
        if len(history_lengths) == 3:
            # Return intent is clear, but two blue items fit the user's request.
            route_answer = {
                "type": "choice", "choice": "returns",
                "probabilities": {"order": 0.01, "returns": 0.98, "clarify": 0.01},
                "confidence": 0.95,
            }
        item_probability = 0.1 if len(history_lengths) == 3 else 0.95
        return io.BytesIO(json.dumps({
            "model": "mock-jev", "answers": {
                "route": route_answer,
                "item_action": {"type": "noul", "noul": 0.95},
                "item_identified": {"type": "noul", "noul": item_probability},
            },
            "usage": {"input_tokens": turn["tokens"], "output_tokens": 0},
        }).encode())

    with patch.dict(os.environ, {"TYPESAFE_API_KEY": "mock-only"}), \
            patch("urllib.request.urlopen", mock_response), \
            contextlib.redirect_stdout(io.StringIO()):
        support = flow.SupportFlow()
        session_id = str(uuid4())
        try:
            for turn in flow.SCENARIO["turns"]:
                support.handle_turn(turn["message"], session_id=session_id)
                assert support.state.last_intent == turn["route"]
            assert history_lengths == [1, 3, 5, 7], history_lengths
            assert [d["route"] for d in support.state.decisions] == ["order", "returns", "clarify", "returns"]
            assert support.state.decisions[0]["confidence"] == 0.35
            assert support.state.decisions[-1]["answer"]["choice"] == "returns"
            assert support.state.decisions[2]["answer"]["choice"] == "returns"
            assert support.state.decisions[2]["item_identified"] == 0.1
            assert len(support.conversation_messages) == 8
            assert support.conversation_messages[-1]["content"] == "I can help with that item's return. No return has been started."
        finally:
            support.finalize_session_traces()
    print("PASS: four turns, ambiguous item blocks return help, resolved item resumes it; no model API calls.")


if __name__ == "__main__":
    main()
