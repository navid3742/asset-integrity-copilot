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


# Trimmed from a real live answer to "Is PV-120 safe to restart?". The bracket-only
# pattern used before found none of these citations, so nothing was being checked.
PV120_ANSWER = (
    "Minimum allowable thickness is unknown (INSP-PV-120-01 to INSP-PV-120-03). There is an "
    "open high-severity incident (INC-012). Follow-up actions are pending (WO-PV-120-01 and "
    "WO-PV-120-02). No restart criteria were found [SOP-PV-005, SOP-PV-006, CASE-INC-012]."
)
PV120_SOURCES = {
    f"{doc}:1": {"doc_id": doc} for doc in ("CASE-INC-012", "SOP-PV-005", "SOP-PV-006")
}


def _history_record_ids(sdk_runtime, tag):
    state = sdk_runtime.AssetRunContext()
    sdk_runtime._record_tool(FakeContext(state), "get_asset_history", {"asset_id": tag})
    return state.record_ids


def test_guardrail_accepts_grounded_live_answer(client, monkeypatch):
    install_fake_sdk(monkeypatch, lambda *a, **k: None)
    from app import sdk_runtime

    record_ids = _history_record_ids(sdk_runtime, "PV-120")
    assert {"INC-012", "WO-PV-120-02", "INSP-PV-120-03"} <= record_ids
    verdict = sdk_runtime.check_final_answer(PV120_ANSWER, PV120_SOURCES, record_ids)
    assert not verdict["blocked"], verdict


def test_guardrail_checks_citations_in_lists_and_parentheses(client, monkeypatch):
    install_fake_sdk(monkeypatch, lambda *a, **k: None)
    from app import sdk_runtime

    record_ids = _history_record_ids(sdk_runtime, "PV-120")
    missing_one = {k: v for k, v in PV120_SOURCES.items() if v["doc_id"] != "SOP-PV-006"}
    verdict = sdk_runtime.check_final_answer(PV120_ANSWER, missing_one, record_ids)
    assert verdict["blocked"] and verdict["unsupported_document_citations"] == ["SOP-PV-006"]
    assert sdk_runtime.check_final_answer("Per the pump SOP (SOP-PMP-001).", {})["blocked"]


def test_guardrail_blocks_record_ids_no_tool_returned(client, monkeypatch):
    install_fake_sdk(monkeypatch, lambda *a, **k: None)
    from app import sdk_runtime

    record_ids = _history_record_ids(sdk_runtime, "PV-120")
    verdict = sdk_runtime.check_final_answer("See incident INC-099.", {}, record_ids)
    assert verdict["unsupported_record_ids"] == ["INC-099"]
    # A record from a different asset than the one looked up is also rejected.
    assert sdk_runtime.check_final_answer("See WO-P-204-02.", {}, record_ids)["blocked"]
    # "CASE-INC-007" is a document ID; it must not be read as record INC-007.
    case_doc = {"CASE-INC-007:0": {"doc_id": "CASE-INC-007"}}
    assert not sdk_runtime.check_final_answer("See [CASE-INC-007].", case_doc)["blocked"]


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
