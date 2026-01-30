import asyncio
import json

import utils.llm as llm


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.status_checked = False

    def raise_for_status(self):
        self.status_checked = True
        return None

    def json(self):
        return self._payload


def test_ask_llm_parses_json(monkeypatch):
    content = json.dumps({"Hero": {"easy": ["a"]}})
    payload = {"choices": [{"message": {"content": content}}]}
    response = FakeResponse(payload)

    def fake_post(url, headers=None, json=None):
        return response

    monkeypatch.setattr(llm, "API_KEY_LLM", "key")
    monkeypatch.setattr(llm, "URL_LLM", "http://llm")
    monkeypatch.setattr(llm.requests, "post", fake_post)

    result = asyncio.run(llm.ask_llm("prompt"))
    assert result == {"Hero": {"easy": ["a"]}}
    assert response.status_checked is True
