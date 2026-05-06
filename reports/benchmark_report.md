# Benchmark Report

| Run | Latency (s) | Cost (USD) | Quality | Citation Coverage | Notes |
|---|---:|---:|---:|---:|---|
| baseline | 11.70 | 0.0001 | 5.0 | N/A | routes=0 sources=0 input_tokens=45 output_tokens=212 |
| multi-agent | 60.93 | 0.0006 | 10.0 | 100% | routes=4 sources=5 input_tokens=1323 output_tokens=731 |

## Agent Trace Summary

| Agent | Duration (s) | Input Tokens | Output Tokens | Notes |
|---|---:|---:|---:|---|
| researcher | 25.94 | N/A | N/A | sources=5 |
| analyst | 20.89 | 482 | 380 | N/A |
| writer | 14.11 | 841 | 351 | N/A |
