import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_llm_response():
    """Mock LLM response object for deterministic unit testing."""
    mock = MagicMock()
    mock.content = "Thank you for reaching out! We are glad to help you with your order."
    return mock

@pytest.fixture
def sample_user_state():
    """Sample state dictionary representing customer conversation context."""
    return {
        "user_message": "Where is my order ORD1001?",
        "user_id": "CUST001",
        "thread_id": "test-thread-123",
        "intent": "ORDER",
        "confidence": 0.95,
        "language": "English",
        "node_latencies": {},
        "agent_steps": []
    }
