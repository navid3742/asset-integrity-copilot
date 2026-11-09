# OpenAI Agents SDK — beginner's walkthrough

## Start with one question

> Investigate P-204. Summarize vibration inspections, maintenance work orders and the related SOP.

`frontend/src/App.tsx` receives the question; `api.ts` POSTs `/api/chat`; `main.py` calls `agent.live_chat()`. With the key+password configured, `agent.py` calls `sdk_runtime.run_agent()`.

## The `Agent` is a configured assistant, not the model alone

`build_agent()` creates one `Agent(name, instructions, model, tools, model_settings, output_guardrails)`. The system instruction is defined in `agent.py`. The default model is configurable (`gpt-4.1-mini`). There is **one agent**, with **three function tools**. This is not a multiagent workflow.

## `@function_tool` turns Python functions into model-callable tools

1. `search_documents(query)` calls the bounded Python dispatcher, which searches `documents.json` using BM25 and optionally embeddings.
2. `get_asset(asset_id)` looks up one asset in SQLite.
3. `get_asset_history(asset_id)` retrieves its inspections, maintenance work orders and incidents.

The model requests tools; the SDK invokes their registered Python functions. The model does **not** obtain SQL, shell access or permission to change equipment.

## `Runner.run_sync()` coordinates execution

The Runner sends the question to the model, receives tool-call requests, invokes registered tools, returns tool output to the model, and repeats until it gets a final answer or reaches the configured turn limit. This replaces v2's hand-written tool-calling loop.

The project uses `tool_choice='required'` initially and SDK `reset_tool_choice=True`, allowing the model to finish after tool use. `parallel_tool_calls=False` makes tool ordering easier to inspect in this small demo.

## Why a `RunContext`?

`AssetRunContext` stores `sources` and `traces` **in Python**, separately from model instructions. `_record_tool()` collects retrieved SOP source IDs and records allowed/rejected tool calls. After the run, the backend returns the answer, sources and trace to React.

## Output guardrail

`verify_final_output()` calls `check_final_answer()`. It blocks some invented document IDs in brackets (e.g., `[SOP-FAKE-123]`) that were not actually retrieved, and some statements claiming writes or approvals. It does **not** prove that every engineering claim is grounded, and isn't a full prompt-injection detector.

## Offline mode is not the SDK agent

Without both `OPENAI_API_KEY` and `DEMO_PASSWORD`, Python's `offline_chat()` produces deterministic document/database summaries. This is useful for no-cost demos, but it is not the model selecting tools.

## Model and token budget

`AssetUsageHooks` reads model usage after SDK calls, and `agent.py` computes an **estimated**, in-memory amount. A $3 estimate threshold is only a demo-level cutoff; it is not a hard account-wide payment limit and embedding costs are not counted.

## Interview-ready distinction

> I used the OpenAI Agents SDK, rather than LangChain, to coordinate a single agent and three read-only function tools. I wrote the domain-specific Python retrieval and SQLite functions, and the SDK manages the model/tool execution cycle. I kept safety-critical actions out of the tool set and use a separate user-confirmation endpoint for fictional report approval.

Be accurate about which code you personally wrote, reviewed or adapted, and which live SDK behaviors you have actually tested.
