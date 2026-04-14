"""Unit tests for SummarizationService._parse_json_list — JSON parsing robustness."""

from unittest.mock import MagicMock

import pytest

from app.llm.client import LLMClient
from app.services.summarization import SummarizationService


@pytest.fixture
def service():
    """Return a SummarizationService with a mocked LLMClient."""
    llm = MagicMock(spec=LLMClient)
    return SummarizationService(llm_client=llm)


def test_parse_raw_json_array(service):
    result = service._parse_json_list('[{"description": "Do something"}]', "action items")
    assert result == [{"description": "Do something"}]


def test_parse_dict_wrapped_array(service):
    result = service._parse_json_list(
        '{"action_items": [{"description": "Do something"}]}', "action items"
    )
    assert result == [{"description": "Do something"}]


def test_parse_markdown_fenced_json(service):
    raw = '```json\n[{"description": "Do something"}]\n```'
    result = service._parse_json_list(raw, "action items")
    assert result == [{"description": "Do something"}]


def test_parse_invalid_json_returns_empty_list(service):
    result = service._parse_json_list("this is not json at all", "action items")
    assert result == []


def test_parse_empty_string_returns_empty_list(service):
    result = service._parse_json_list("", "action items")
    assert result == []


def test_parse_filters_out_non_dict_items(service):
    result = service._parse_json_list('[{"ok": true}, "bad", 42, null]', "items")
    assert result == [{"ok": True}]


def test_parse_empty_array(service):
    result = service._parse_json_list("[]", "action items")
    assert result == []


def test_parse_regex_fallback_recovers_embedded_array(service):
    """If JSON is embedded in prose, the regex fallback should extract it."""
    raw = 'Here are your items: [{"description": "Recovered item"}] end of response.'
    result = service._parse_json_list(raw, "action items")
    assert result == [{"description": "Recovered item"}]
