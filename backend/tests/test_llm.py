import json
from types import SimpleNamespace

from app.services.llm import LLMError, generate_json

SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}}


class FakeClient:
    def __init__(self, output_text='{"ok": true}'):
        self.output_text, self.calls = output_text, []
        self.interactions = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


def raises_llm_error(**kwargs):
    try:
        generate_json("hello", SCHEMA, model="test-model", api_key="k", **kwargs)
    except LLMError:
        return True
    return False


def test_a_good_answer_comes_back_as_a_dict():
    client = FakeClient('{"ok": true}')
    assert generate_json("hello", SCHEMA, client=client, model="test-model") == {"ok": True}


def test_the_request_asks_for_a_json_schema_and_sends_no_sampling_settings():
    client = FakeClient()
    generate_json("hello", SCHEMA, client=client, model="test-model", thinking_level="")
    call = client.calls[0]
    assert call["model"] == "test-model"
    assert call["input"] == "hello"
    assert call["response_format"] == {
        "type": "text",
        "mime_type": "application/json",
        "schema": SCHEMA,
    }
    assert "generation_config" not in call
    assert "temperature" not in call


def test_a_thinking_level_is_sent_only_when_one_is_set():
    client = FakeClient()
    generate_json("hello", SCHEMA, client=client, model="test-model", thinking_level="low")
    assert client.calls[0]["generation_config"] == {"thinking_level": "low"}


def test_missing_setup_raises_without_calling_anything():
    try:
        generate_json("hello", SCHEMA, model="", api_key="")
    except LLMError as exc:
        assert "not set up" in str(exc)
    else:
        raise AssertionError("expected LLMError")


def test_unusable_answers_raise():
    assert raises_llm_error(client=FakeClient("not json"))
    assert raises_llm_error(client=FakeClient(None))
    assert raises_llm_error(client=FakeClient("[1, 2]"))
    assert json.loads('{"ok": true}') == {"ok": True}  # sanity check on the helper above


def test_a_slow_call_times_out():
    class SlowClient(FakeClient):
        def create(self, **kwargs):
            import time

            time.sleep(0.3)
            return super().create(**kwargs)

    assert raises_llm_error(client=SlowClient(), timeout=0.05)