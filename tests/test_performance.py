import pytest
from tools.performance import log_trace, get_performance_summary, get_system_telemetry

def test_performance_trace_logging():
    trace = log_trace(
        thread_id="test-thread-999",
        user_id="CUST001",
        intent="FAQ",
        total_latency_ms=1150.5,
        node_latencies={"classify_intent": 200.0, "generate_response": 950.5},
        prompt_tokens=400,
        completion_tokens=150,
        status="success"
    )
    assert trace["trace_id"].startswith("TRC-")
    assert trace["total_latency_ms"] == 1150.5

def test_performance_summary_metrics():
    summary = get_performance_summary()
    assert "total_runs" in summary
    assert "avg_latency_ms" in summary
    assert "p95_latency_ms" in summary
    assert summary["total_runs"] > 0

def test_system_telemetry():
    telem = get_system_telemetry()
    assert "cpu_percent" in telem
    assert "memory_percent" in telem
    assert telem["status"] == "Healthy"
