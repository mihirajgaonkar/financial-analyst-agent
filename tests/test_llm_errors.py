import pytest
from langchain_core.messages import AIMessage

from financial_research.llm.errors import LLMQuotaError, invoke_with_quota_handling


class FailingModel:
    def __init__(self, message: str):
        self.message = message

    def invoke(self, messages):
        raise RuntimeError(self.message)


class RetryThenSuccessModel:
    def __init__(self):
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("429 RESOURCE_EXHAUSTED {'error': {'details': [{'retryDelay': '2s'}]}}")
        return AIMessage(content="Recovered.")


def test_daily_gemini_quota_error_is_actionable_without_retrying() -> None:
    model = FailingModel(
        "Error calling model 'gemini-3.6-flash' (RESOURCE_EXHAUSTED): 429 RESOURCE_EXHAUSTED. "
        "Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, "
        "limit: 20, model: gemini-3.6-flash quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier "
        "retryDelay: '49s'"
    )

    with pytest.raises(LLMQuotaError) as exc_info:
        invoke_with_quota_handling(model, [])

    message = str(exc_info.value)
    assert "gemini-3.6-flash" in message
    assert "daily/free-tier quota" in message
    assert "LLM_PROVIDER" in message


def test_short_transient_rate_limit_retries_once() -> None:
    slept = []
    model = RetryThenSuccessModel()

    response = invoke_with_quota_handling(model, [], sleep_fn=slept.append)

    assert response.content == "Recovered."
    assert model.calls == 2
    assert slept == [2.0]
