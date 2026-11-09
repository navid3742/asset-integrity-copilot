"""OpenAI Agents SDK implementation of the Asset Integrity Copilot live agent.

This module imports the optional SDK only when live mode is used; the offline
preview and its tests remain usable before an API key or SDK is configured.

Docs: https://openai.github.io/openai-agents-python/
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Annotated

from pydantic import Field
from agents import (
    Agent, Runner, RunConfig, RunContextWrapper, ModelSettings, RunHooks,
    GuardrailFunctionOutput, OutputGuardrailTripwireTriggered, MaxTurnsExceeded, function_tool,
    output_guardrail,
)

from . import agent as foundation
from .config import MODEL, MAX_TOOL_ROUNDS, ENABLE_SDK_TRACING


@dataclass
class AssetRunContext:
    """Data held by Python, not entrusted to the model as instructions."""
    sources: dict = field(default_factory=dict)
    traces: list = field(default_factory=list)


def _record_tool(context: RunContextWrapper[AssetRunContext], name: str, arguments: dict) -> str:
    """Execute only foundation.dispatch_tool and record user-visible activity.

    The tool outputs are DATA. The agent's system instructions warn it never to
    treat instructions embedded in tool outputs as commands.
    """
    outcome = foundation.dispatch_tool(name, arguments)
    state = context.context
    if name == 'search_documents':
        for source in outcome.get('results', []):
            state.sources[source['id']] = source
    state.traces.append({
        'tool': name,
        'args': arguments,
        'status': 'rejected' if 'error' in outcome else 'completed',
    })
    return json.dumps(outcome, ensure_ascii=False)[:14000]


@function_tool
async def search_documents(
    ctx: RunContextWrapper[AssetRunContext],
    query: Annotated[str, Field(min_length=1, max_length=500, description='Oil & Gas procedure or quality topic to search')],
) -> str:
    """Search the synthetic oil-and-gas mechanical integrity SOPs and case studies. Returns source IDs and excerpts."""
    return _record_tool(ctx, 'search_documents', {'query': query})


@function_tool
async def get_asset(
    ctx: RunContextWrapper[AssetRunContext],
    asset_id: Annotated[str, Field(pattern=r'^(?:P|CV|PV)-\d{3}$', description='Exact equipment tag such as P-204, CV-310, or PV-120')],
) -> str:
    """Retrieve one synthetic oil and gas equipment record by its exact equipment tag."""
    return _record_tool(ctx, 'get_asset', {'asset_id': asset_id})


@function_tool
async def get_asset_history(
    ctx: RunContextWrapper[AssetRunContext],
    asset_id: Annotated[str, Field(pattern=r'^(?:P|CV|PV)-\d{3}$', description='Exact equipment tag such as P-204, CV-310, or PV-120')],
) -> str:
    """Retrieve synthetic inspection records, maintenance work orders and incidents for one asset."""
    return _record_tool(ctx, 'get_asset_history', {'asset_id': asset_id})


_DOCUMENT_REFERENCE = re.compile(r'\[((?:SOP|CASE|GUIDE|POL)-[A-Z0-9-]+)\]')
_UNAUTHORIZED_CLAIM = re.compile(
    r"\b(?:I|we|Asset Integrity Copilot)\s+(?:have\s+)?(?:already\s+)?"
    r"(?:approved|deleted|modified|changed|overridden)\b",
    re.IGNORECASE,
)


def check_final_answer(answer: str, sources: dict) -> dict:
    """Simple deterministic verification, not a complete grounding validator.

    Block invented *document* IDs and statements that the assistant performed
    write operations. Inspection and incident IDs from database tools are not
    document citations and are not validated by this particular check.
    """
    cited = set(_DOCUMENT_REFERENCE.findall(answer))
    available = {record['doc_id'] for record in sources.values()}
    unsupported = sorted(cited - available)
    illegal_action = bool(_UNAUTHORIZED_CLAIM.search(answer))
    return {'unsupported_document_citations': unsupported,
            'claimed_unauthorized_action': illegal_action,
            'blocked': bool(unsupported or illegal_action)}


class AssetUsageHooks(RunHooks):
    """Count completed model calls, including runs that fail output checks."""

    async def on_llm_start(self, context, agent, system_prompt, input_items):
        # The limit is approximate and per process, not a provider-side cap.
        foundation._budget_guard()

    async def on_llm_end(self, context, agent, response):
        usage = getattr(response, 'usage', None)
        foundation._record_sdk_usage({
            'requests': 1,
            'input_tokens': getattr(usage, 'input_tokens', 0) or 0,
            'output_tokens': getattr(usage, 'output_tokens', 0) or 0,
        })


@output_guardrail
async def verify_final_output(
    ctx: RunContextWrapper[AssetRunContext],
    current_agent: Agent,
    output: str,
) -> GuardrailFunctionOutput:
    """Reject invented doc references and claims that the agent wrote records."""
    verdict = check_final_answer(str(output), ctx.context.sources)
    return GuardrailFunctionOutput(output_info=verdict, tripwire_triggered=verdict['blocked'])


def build_agent() -> Agent:
    """Configure one SDK agent. Runner owns the execution loop and tool routing."""
    return Agent(
        name='Asset Integrity Copilot – Oil & Gas',
        instructions=foundation.SYSTEM,
        model=MODEL,
        tools=[search_documents, get_asset, get_asset_history],
        model_settings=ModelSettings(
            tool_choice='required',          # at least one retrieval before answering
            parallel_tool_calls=False,      # predictable ordering for the small demo
            max_tokens=900,
        ),
        reset_tool_choice=True,           # after first tool, SDK switches to auto
        output_guardrails=[verify_final_output],
    )


def _messages(question: str, history: list | None) -> list[dict]:
    """Only user/assistant plaintext history may be carried into an SDK run."""
    messages = []
    for turn in (history or [])[-6:]:
        if not isinstance(turn, dict):
            continue
        role, content = turn.get('role'), turn.get('content')
        if role in ('user', 'assistant') and isinstance(content, str):
            messages.append({'role': role, 'content': content[:2000]})
    messages.append({'role': 'user', 'content': question[:2000]})
    return messages


def run_agent(question: str, history: list | None = None) -> dict:
    """Run the agent and maintain compatibility with the existing frontend API.

    The SDK automatically calls tools, loops, validates tool schemas, and
    enforces max_turns. We preserve tool traces/citations using run context.
    """
    context = AssetRunContext()
    configured_agent = build_agent()
    try:
        result = Runner.run_sync(
            configured_agent,
            _messages(question, history),
            context=context,
            max_turns=MAX_TOOL_ROUNDS + 1,
            hooks=AssetUsageHooks(),
            run_config=RunConfig(
                workflow_name='Asset Integrity Copilot - Synthetic Oil & Gas Demo',
                tracing_disabled=not ENABLE_SDK_TRACING,
                trace_include_sensitive_data=False,
            ),
        )
    except OutputGuardrailTripwireTriggered:
        return {
            'answer': 'The generated answer was blocked by a safety check. It may contain unsupported document citations or claim an action the agent cannot perform. Please ask a more specific question.',
            'sources': list(context.sources.values()),
            'traces': context.traces,
            'mode': 'live',
            'guardrail_blocked': True,
        }
    except MaxTurnsExceeded:
        return {
            'answer': 'The agent reached its configured turn limit before it could complete the investigation. Please ask a narrower question.',
            'sources': list(context.sources.values()),
            'traces': context.traces,
            'mode': 'live',
            'guardrail_blocked': False,
        }

    return {
        'answer': str(result.final_output or 'The agent did not produce an answer.'),
        'sources': list(context.sources.values()),
        'traces': context.traces,
        'mode': 'live',
        'guardrail_blocked': False,
    }
