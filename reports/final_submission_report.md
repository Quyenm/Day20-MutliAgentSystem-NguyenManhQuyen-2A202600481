# Final Submission Report

## Project Summary

This repo implements a runnable multi-agent research system for Lab 20. The system compares a
single-agent baseline against a supervisor-orchestrated multi-agent workflow. It includes OpenAI
LLM calls, OpenAI web search, local trace export, benchmark reporting, Langfuse hosted tracing,
and a localhost web demo for live presentation.

## Implemented Components

### Baseline

- Runs a direct single-agent OpenAI Responses API call.
- Produces a concise answer without web search.
- Records token metadata in trace payload.
- Appears as `baseline benchmark` in Langfuse when hosted tracing keys are configured.

### Multi-Agent Workflow

Route:

```text
researcher -> analyst -> writer -> done
```

Agents:

- `SupervisorAgent`: routes through the workflow and stops at `done`.
- `ResearcherAgent`: calls OpenAI `web_search_preview` and returns URL-backed sources.
- `AnalystAgent`: uses OpenAI Responses API to analyze evidence and identify weak/missing evidence.
- `WriterAgent`: uses OpenAI Responses API to write the final cited answer.
- `CriticAgent`: optional lightweight citation/final-answer review metadata.

### Shared State

`ResearchState` carries:

- request
- route history
- sources
- research notes
- analysis notes
- final answer
- agent results
- trace events
- errors

This makes handoffs and debugging visible.

### Trace And Observability

Local artifacts:

- `reports/last_trace.json`
- `reports/web_demo_last_run.json`

Hosted artifacts:

- `reports/hosted_trace_exports.json`
- Langfuse baseline trace:
  `https://cloud.langfuse.com/trace/b3813b9b1beb1ea1292317865b359b49`
- Langfuse multi-agent trace:
  `https://cloud.langfuse.com/trace/a2762a67dfb58fd993b1f94c2f69ce52`

Trace metadata includes:

- route history
- source count
- trace event count
- per-agent token metadata where available
- researcher source count

### Benchmark

Benchmark command:

```powershell
C:\Users\mnquyen26\anaconda3\envs\vin_deploy\python.exe -m multi_agent_research_lab.cli benchmark --query "What are current production guardrails for LLM agents?"
```

Benchmark output:

- `reports/benchmark_report.md`
- baseline row
- multi-agent row
- citation coverage
- route/source notes
- Agent Trace Summary

Latest benchmark metrics for query
`What are current production guardrails for LLM agents?`:

| Run | Latency (s) | Cost (USD) | Quality | Citation Coverage | Routes | Sources |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 11.70 | 0.0001 | 5.0 | N/A | 0 | 0 |
| multi-agent | 60.93 | 0.0006 | 10.0 | 100% | 4 | 5 |

The multi-agent run is slower because it performs web search plus separate analyst and writer
LLM calls. It provides citations and traceable role separation, which the baseline does not.

## Localhost Web Demo

Run:

```powershell
cd D:\AI_thucchien\Day20
C:\Users\mnquyen26\anaconda3\envs\vin_deploy\python.exe -m multi_agent_research_lab.cli web --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

Demo features:

- one query input
- `Run Comparison` for live baseline + multi-agent execution
- `Load Last Run` for fast presentation without spending new API calls
- side-by-side answers
- benchmark metric cards
- baseline and multi-agent flow graph
- tool call cards
- source cards
- report preview
- Langfuse/export evidence links

## What Was Added Beyond The Starter Requirements

- OpenAI Responses API LLM client with local fallback.
- OpenAI `web_search_preview` search client with local fallback.
- Analyst and writer LLM-based synthesis.
- Hosted trace exporters for Langfuse and LangSmith.
- Langfuse baseline and multi-agent trace exports.
- Agent-level `agent.start` and `agent.end` trace spans with duration and metadata.
- Citation coverage metric.
- Localhost web demo dashboard.
- TDD tests for LLM, search, analyst, writer, workflow, benchmark CLI, hosted tracing,
  critic review, and web demo.

## Failure Modes And Fixes

### Missing OpenAI API key

Failure mode:

- The app cannot call real OpenAI LLM/search.

Fix:

- The clients fall back to deterministic local behavior when no key is present.
- For real demo, fill `OPENAI_API_KEY` in `.env`.

### Missing Langfuse/LangSmith keys

Failure mode:

- Hosted tracing cannot export to dashboard.

Fix:

- Local trace artifacts are still written.
- `reports/hosted_trace_exports.json` records `skipped`.
- Fill `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` to export to Langfuse.

### Multi-agent latency is higher

Failure mode:

- Multi-agent workflow costs more time than baseline because it runs search, analyst, and writer.

Fix:

- The web demo and benchmark report show latency explicitly.
- The design favors traceability/citations over raw speed for research tasks.

### Weak or sparse web sources

Failure mode:

- Search may return fewer sources for niche or ambiguous queries.

Fix:

- Source count and citation coverage are surfaced in metrics.
- Researcher output preserves provider metadata and URLs for inspection.

## Exit Ticket

### When should multi-agent be used?

Use multi-agent when the task benefits from role separation: current research, evidence gathering,
critical analysis, final synthesis, traceability, and citation checking. The workflow is easier to
debug because every handoff is visible and every agent has a clear responsibility.

### When should multi-agent not be used?

Do not use multi-agent for simple direct questions where no search, evidence analysis, or audit
trail is needed. A single-agent baseline is faster and cheaper for straightforward answers.

## Verification Evidence

Commands used:

```powershell
conda run -n vin_deploy python -m pytest -q --basetemp .pytest_tmp
conda run -n vin_deploy python -m ruff check src tests
conda run -n vin_deploy python -m compileall src
```

Latest full verification after the final report metric refresh:

- `pytest`: 24 passed.
- `ruff`: all checks passed.
- `compileall`: exit 0.
