# Lab 20: Multi-Agent Research System

Runnable multi-agent research lab with a single-agent baseline, OpenAI web search,
OpenAI LLM analysis/writing, local trace artifacts, Langfuse hosted tracing, benchmark
reporting, and a localhost web demo.

## What This Repo Implements

- Single-agent baseline using OpenAI Responses API.
- Supervisor-orchestrated multi-agent workflow:
  - Researcher: OpenAI `web_search_preview` with URL citations.
  - Analyst: OpenAI Responses API for evidence analysis.
  - Writer: OpenAI Responses API for final cited answer.
  - Optional Critic: lightweight citation/final-answer review metadata.
- Shared `ResearchState` with route history, sources, agent results, trace events, and errors.
- Local trace export:
  - `reports/last_trace.json`
  - `reports/web_demo_last_run.json`
- Benchmark report:
  - `reports/benchmark_report.md`
- Hosted observability:
  - Langfuse export for baseline and multi-agent traces.
  - LangSmith exporter is implemented but skipped unless `LANGSMITH_API_KEY` is configured.
- Localhost web demo:
  - Side-by-side baseline vs multi-agent answers.
  - Benchmark metrics.
  - Flow graph.
  - Tool calls.
  - Sources and trace/report evidence.

## Architecture

```text
User Query
   |
   +--> Baseline LLM ---------------------------> baseline answer
   |
   +--> Supervisor
          |
          +--> Researcher -> web_search_preview -> sources/research notes
          +--> Analyst    -> OpenAI LLM         -> analysis notes
          +--> Writer     -> OpenAI LLM         -> final cited answer
          |
          +--> Trace + Benchmark + Langfuse export
```

## Setup

Use the existing conda environment:

```powershell
cd D:\AI_thucchien\Day20
conda run -n vin_deploy python -m pip install -e ".[dev,llm]"
```

Create `.env` from `.env.example` if needed and fill keys:

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini

LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com

# Optional
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=multi-agent-research-lab
TAVILY_API_KEY=
```

`TAVILY_API_KEY` is not required because the researcher uses OpenAI web search.

## Run Commands

Single-agent baseline:

```powershell
C:\Users\mnquyen26\anaconda3\envs\vin_deploy\python.exe -m multi_agent_research_lab.cli baseline --query "What are current production guardrails for LLM agents?"
```

Multi-agent workflow:

```powershell
C:\Users\mnquyen26\anaconda3\envs\vin_deploy\python.exe -m multi_agent_research_lab.cli multi-agent --query "What are current production guardrails for LLM agents?"
```

Benchmark baseline vs multi-agent:

```powershell
C:\Users\mnquyen26\anaconda3\envs\vin_deploy\python.exe -m multi_agent_research_lab.cli benchmark --query "What are current production guardrails for LLM agents?"
```

Localhost web demo:

```powershell
C:\Users\mnquyen26\anaconda3\envs\vin_deploy\python.exe -m multi_agent_research_lab.cli web --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

Use `Load Last Run` for a fast demo without spending new API calls. Use `Run Comparison`
to run baseline and multi-agent live from the same query.

## Generated Evidence

- `reports/benchmark_report.md`: benchmark table and agent trace summary.
- `reports/last_trace.json`: local multi-agent trace.
- `reports/hosted_trace_exports.json`: Langfuse/LangSmith export status and URLs.
- `reports/web_demo_last_run.json`: latest web demo payload.
- `reports/final_submission_report.md`: final write-up for submission.
- `docs/submission_checklist.md`: screenshot and submission checklist.
- `evidence/screenshots/`: renamed screenshot evidence for web demo, Langfuse, and benchmark views.

Screenshot evidence included:

- `evidence/screenshots/01-localhost-overview.jpg`
- `evidence/screenshots/02-localhost-baseline-vs-multi-agent.jpg`
- `evidence/screenshots/03-localhost-flow-graph-tools.jpg`
- `evidence/screenshots/04-localhost-sources-report.jpg`
- `evidence/screenshots/05-langfuse-trace-list.jpg`
- `evidence/screenshots/06-langfuse-multi-agent-trace-detail.jpg`
- `evidence/screenshots/07-langfuse-baseline-trace-detail.jpg`
- `evidence/screenshots/08-benchmark-report.jpg`

Latest Langfuse traces from the verified guardrails run:

- Baseline: `https://cloud.langfuse.com/trace/b3813b9b1beb1ea1292317865b359b49`
- Multi-agent: `https://cloud.langfuse.com/trace/a2762a67dfb58fd993b1f94c2f69ce52`

## How The README Requirements Are Met

| Requirement | Status | Evidence |
|---|---|---|
| Clear agent roles | Done | `agents/researcher.py`, `agents/analyst.py`, `agents/writer.py` |
| Shared handoff state | Done | `core/state.py`, `reports/last_trace.json` |
| Supervisor routing | Done | `agents/supervisor.py`, `graph/workflow.py` |
| Real LLM baseline | Done | `cli baseline`, `web/backend.py::run_baseline` |
| Real researcher/search | Done | OpenAI `web_search_preview`, source URLs in reports |
| Real analyst/writer | Done | OpenAI Responses API with token metadata |
| Trace/logging | Done | local trace JSON, Langfuse hosted traces |
| Benchmark | Done | `reports/benchmark_report.md` |
| Failure mode explanation | Done | `reports/final_submission_report.md` |
| Localhost demo | Extra | `cli web`, `src/multi_agent_research_lab/web/` |

## Verification

Fresh verification command set:

```powershell
conda run -n vin_deploy python -m pytest -q --basetemp .pytest_tmp
conda run -n vin_deploy python -m ruff check src tests
conda run -n vin_deploy python -m compileall src
```

Latest verified output:

- `pytest`: 24 passed.
- `ruff`: all checks passed.
- `compileall`: exit 0.
