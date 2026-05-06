# Submission Checklist

Use this checklist when recording screenshots and packaging the repo.

## Required Screenshots

Save screenshots under `evidence/screenshots/` with these exact names:

1. Localhost web demo home page
   - File: `evidence/screenshots/01-localhost-overview.jpg`
   - URL: `http://127.0.0.1:8000`
   - Show query input, `Run Comparison`, `Load Last Run`, benchmark metric cards.

2. Web demo baseline vs multi-agent comparison
   - File: `evidence/screenshots/02-localhost-baseline-vs-multi-agent.jpg`
   - Show both answer panels in the same screenshot.
   - Show baseline route as direct and multi-agent route as `researcher -> analyst -> writer -> done`.

3. Web demo flow graph and tool calls
   - File: `evidence/screenshots/03-localhost-flow-graph-tools.jpg`
   - Show baseline flow: `User Query -> Baseline LLM -> Answer`.
   - Show multi-agent flow: `User Query -> Researcher -> Analyst -> Writer -> Answer`.
   - Show tools: OpenAI Responses API and OpenAI `web_search_preview`.

4. Web demo sources and benchmark/report area
   - File: `evidence/screenshots/04-localhost-sources-report.jpg`
   - Show citation/source cards.
   - Show benchmark/report preview.

5. Langfuse trace list
   - File: `evidence/screenshots/05-langfuse-trace-list.jpg`
   - Show latest `baseline benchmark`.
   - Show latest `multi-agent benchmark`.
   - Show child spans `researcher`, `analyst`, `writer`.

6. Langfuse multi-agent trace detail
   - File: `evidence/screenshots/06-langfuse-multi-agent-trace-detail.jpg`
   - Show input query, output answer, metadata:
     - `trace_event_count`
     - `source_count`
     - `route_history`
   - Latest multi-agent URL:
     `https://cloud.langfuse.com/trace/a2762a67dfb58fd993b1f94c2f69ce52`

7. Langfuse baseline trace detail
   - File: `evidence/screenshots/07-langfuse-baseline-trace-detail.jpg`
   - Show input query, baseline output, and `route_history: []`.
   - Latest baseline URL:
     `https://cloud.langfuse.com/trace/b3813b9b1beb1ea1292317865b359b49`

8. Benchmark report file
   - File: `evidence/screenshots/08-benchmark-report.jpg`
   - Open `reports/benchmark_report.md`.
   - Show baseline row and multi-agent row.
   - Show Agent Trace Summary.

## Files To Submit

- Source repo.
- `reports/benchmark_report.md`
- `reports/final_submission_report.md`
- `reports/last_trace.json`
- `reports/hosted_trace_exports.json`
- Screenshots listed above.

## Demo Commands

Run localhost demo:

```powershell
cd D:\AI_thucchien\Day20
C:\Users\mnquyen26\anaconda3\envs\vin_deploy\python.exe -m multi_agent_research_lab.cli web --host 127.0.0.1 --port 8000
```

Run benchmark:

```powershell
C:\Users\mnquyen26\anaconda3\envs\vin_deploy\python.exe -m multi_agent_research_lab.cli benchmark --query "What are current production guardrails for LLM agents?"
```

## Completion Status

| README/Lab requirement | Status |
|---|---|
| Single-agent baseline | Done |
| Supervisor/router | Done |
| Researcher agent | Done |
| Analyst agent | Done |
| Writer agent | Done |
| Shared state | Done |
| Trace/logging | Done |
| Benchmark single vs multi-agent | Done |
| Hosted trace screenshot/link | Done with Langfuse |
| Failure mode explanation | Done in final report |
| Localhost visual demo | Extra, done |
