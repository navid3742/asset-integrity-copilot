"""Mock OpenAI Agents SDK boundary tests. Does NOT verify live cloud model compatibility."""

import importlib
import sys
import types
from typing import Generic, TypeVar

from app import agent

T = TypeVar("T")


class FakeContext(Generic[T]):
    def __init__(self, value):
        self.context = value


class FakeAgent:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeModelSettings:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeRunConfig:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeGuardrailOutput:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeBlockedError(Exception):
    pass


def install_fake_sdk(monkeypatch, callback):
    fake = types.ModuleType("agents")
    fake.Agent = FakeAgent
    fake.RunHooks = object
    fake.ModelSettings = FakeModelSettings
    fake.RunConfig = FakeRunConfig
    fake.RunContextWrapper = FakeContext
    fake.GuardrailFunctionOutput = FakeGuardrailOutput
    fake.OutputGuardrailTripwireTriggered = FakeBlockedError
    fake.MaxTurnsExceeded = type("FakeMaxTurnsExceeded", (Exception,), {})
    fake.function_tool = lambda f: f
    fake.output_guardrail = lambda f: f

    class FakeRunner:
        @staticmethod
        def run_sync(*args, **kwargs):
            return callback(*args, **kwargs)

    fake.Runner = FakeRunner
    monkeypatch.setitem(sys.modules, "agents", fake)
    sys.modules.pop("app.sdk_runtime", None)
    return importlib.import_module("app.sdk_runtime")


def test_sdk_calls_real_asset_tools(client, monkeypatch):
    seen = {}

    def callback(config, messages, context, max_turns, run_config, hooks):
        import asyncio

        usage = types.SimpleNamespace(
            usage=types.SimpleNamespace(input_tokens=200, output_tokens=50)
        )
        asyncio.run(hooks.on_llm_end(FakeContext(context), config, usage))
        seen["tools"] = [t.__name__ for t in config.tools]
        seen["limit"] = max_turns
        seen["tracing"] = run_config.tracing_disabled
        tool = next(x for x in config.tools if x.__name__ == "get_asset")
        outcome = asyncio.run(tool(FakeContext(context), "P-204"))
        assert "P-204" in outcome and "Pump" in outcome
        return types.SimpleNamespace(final_output="P-204 is marked Review.")

    install_fake_sdk(monkeypatch, callback)
    monkeypatch.setattr(agent, "LIVE_ENABLED", True)
    before = agent.usage()["requests"]
    result = agent.live_chat("What is P-204 status?")
    assert result["mode"] == "live" and result["traces"][0]["tool"] == "get_asset"
    assert seen["tools"] == ["search_documents", "get_asset", "get_asset_history"]
    assert seen["limit"] == 5 and seen["tracing"]
    assert agent.usage()["requests"] == before + 1


def test_sdk_search_history_and_invalid_tool_request(client, monkeypatch):
    def callback(config, messages, context, max_turns, run_config, hooks):
        import asyncio

        search = next(x for x in config.tools if x.__name__ == "search_documents")
        history = next(x for x in config.tools if x.__name__ == "get_asset_history")
        cite = asyncio.run(search(FakeContext(context), "P-204 vibration seal incident INC-007"))
        assert "CASE-INC-007" in cite or "SOP-PMP-001" in cite
        asset_history = asyncio.run(history(FakeContext(context), "P-204"))
        assert "WO-P-204-02" in asset_history
        invalid = asyncio.run(history(FakeContext(context), "../../etc/passwd"))
        assert "error" in invalid
        return types.SimpleNamespace(final_output="Review incident INC-007 and its related SOP.")

    install_fake_sdk(monkeypatch, callback)
    monkeypatch.setattr(agent, "LIVE_ENABLED", True)
    result = agent.live_chat("Investigate pump P-204 vibration history")
    assert result["sources"] and len(result["traces"]) == 3
    assert result["traces"][-1]["status"] == "rejected"


def test_sdk_output_guardrail_blocks_invented_documents(client, monkeypatch):
    install_fake_sdk(monkeypatch, lambda *a, **k: None)
    from app import sdk_runtime

    assert sdk_runtime.check_final_answer("Use [SOP-FAKE-123].", {})["blocked"]
    assert sdk_runtime.check_final_answer("I have approved the asset for operations.", {})[
        "blocked"
    ]
    assert not sdk_runtime.check_final_answer("I cannot approve reports.", {})["blocked"]
    source = {"SOP-PMP-001:1": {"doc_id": "SOP-PMP-001"}}
    assert not sdk_runtime.check_final_answer("See [SOP-PMP-001].", source)["blocked"]


def test_sdk_output_tripwire_yields_safe_response(client, monkeypatch):
    def raise_block(*args, **kwargs):
        raise FakeBlockedError("unsafe")

    install_fake_sdk(monkeypatch, raise_block)
    monkeypatch.setattr(agent, "LIVE_ENABLED", True)
    result = agent.live_chat("Investigate P-204")
    assert result["guardrail_blocked"] and result["mode"] == "live"
    assert "blocked" in result["answer"].lower()


def test_password_restricts_demo_api(client, monkeypatch):
    from app import main

    monkeypatch.setattr(main, "DEMO_PASSWORD", "unit-test-secret")
    assert client.get("/api/assets").status_code == 401
    assert client.get("/api/assets", headers={"X-Demo-Key": "wrong"}).status_code == 401
    assert client.get("/api/assets", headers={"X-Demo-Key": "unit-test-secret"}).status_code == 200


def test_sdk_prompts_contain_prohibitions():
    for word in ("UNTRUSTED", "pressure limits", "equipment", "permits", "fitness"):
        assert word.lower() in agent.SYSTEM.lower()
