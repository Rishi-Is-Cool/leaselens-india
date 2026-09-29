"""Offline tests for Phase 4's reply-parsing logic (no LLM calls)."""

import pytest

from app.explain.cross_clause import parse_reply as parse_cross_clause_reply
from app.explain.generate import parse_reply as parse_explanation_reply


def test_parse_explanation_reply_happy_path():
    content = (
        '{"document_says": "The tenant pays rent monthly.", "concern": "", '
        '"statute_support": [{"entry_id": "MH_SEC_001", "how_it_applies": "caps deposits"}]}'
    )
    result = parse_explanation_reply(content, "c001", "GREEN")
    assert result.document_says == "The tenant pays rent monthly."
    assert result.statute_support == [{"entry_id": "MH_SEC_001", "how_it_applies": "caps deposits"}]


def test_parse_explanation_reply_tolerates_surrounding_text():
    content = 'Sure, here is the answer:\n{"document_says": "x", "concern": "y", "statute_support": []}\nDone.'
    result = parse_explanation_reply(content, "c002", "YELLOW")
    assert result.document_says == "x"


def test_parse_explanation_reply_rejects_empty_document_says():
    with pytest.raises(ValueError):
        parse_explanation_reply('{"document_says": "", "concern": "y", "statute_support": []}', "c003", "GREEN")


def test_parse_explanation_reply_rejects_non_list_statute_support():
    with pytest.raises(ValueError):
        parse_explanation_reply(
            '{"document_says": "x", "concern": "y", "statute_support": "MH_SEC_001"}', "c004", "GREEN"
        )


def test_parse_explanation_reply_drops_malformed_statute_entries():
    content = '{"document_says": "x", "concern": "y", "statute_support": [{"how_it_applies": "no id"}, {"entry_id": "OK_1"}]}'
    result = parse_explanation_reply(content, "c005", "GREEN")
    assert result.statute_support == [{"entry_id": "OK_1", "how_it_applies": ""}]


def test_parse_explanation_reply_no_json_raises():
    with pytest.raises(ValueError):
        parse_explanation_reply("I think this is fine.", "c006", "GREEN")


def test_parse_cross_clause_reply_happy_path():
    data = parse_cross_clause_reply('{"related": true, "relationship_type": "x", "explanation": "y"}')
    assert data["related"] is True


def test_parse_cross_clause_reply_missing_related_raises():
    with pytest.raises(ValueError):
        parse_cross_clause_reply('{"relationship_type": "x"}')
