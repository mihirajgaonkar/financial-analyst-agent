from langchain_core.messages import AIMessage

from financial_research.llm.content import extract_text_content, strip_provider_metadata


def test_extract_text_content_discards_provider_extras() -> None:
    content = [
        {
            "type": "text",
            "text": "## Summary\nUseful analysis.",
            "extras": {"signature": "large-provider-metadata"},
        }
    ]

    assert extract_text_content(content) == "## Summary\nUseful analysis."


def test_extract_text_content_supports_plain_text() -> None:
    assert extract_text_content("Plain answer") == "Plain answer"


def test_strip_provider_metadata_preserves_tool_calls() -> None:
    message = AIMessage(
        content=[{"type": "text", "text": "Clean answer", "extras": {"signature": "discard"}}],
        tool_calls=[{"name": "get_interest_rates", "args": {}, "id": "1"}],
    )

    cleaned = strip_provider_metadata(message)
    assert cleaned.content == "Clean answer"
    assert cleaned.tool_calls[0]["name"] == "get_interest_rates"
