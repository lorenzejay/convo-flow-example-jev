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
        turn = flow.SCENARIO["turns"][len(history_lengths) - 1]
        answer = {
            "type": "choice", "choice": turn["route"],
            "probabilities": turn["probabilities"], "confidence": turn["confidence"],
        }
        if len(history_lengths) == 3:
            # Highest-probability choice differs from the policy's final route.
            answer = {
                "type": "choice", "choice": "returns",
                "probabilities": {"order": 0.38, "returns": 0.40, "clarify": 0.22},
                "confidence": 0.12,
            }
        return io.BytesIO(json.dumps({
            "model": "mock-jev", "answers": {"route": answer},
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
            assert history_lengths == [1, 3, 5], history_lengths
            assert [d["route"] for d in support.state.decisions] == ["order", "returns", "clarify"]
            assert support.state.decisions[-1]["answer"]["choice"] == "returns"
            assert support.state.decisions[-1]["confidence"] == 0.12
            assert len(support.conversation_messages) == 6
            assert support.conversation_messages[-1]["content"] == flow.SCENARIO["turns"][2]["reply"]
        finally:
            support.finalize_session_traces()
    print("PASS: three handlers, six messages, raw answer preserved, low-confidence clarification; no model API calls.")


if __name__ == "__main__":
    main()
