"""RED: Document ingestion + BM25 search tests."""

import json
import os

import pytest


@pytest.fixture
def knowledge_dir(tmp_path):
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    return tmp_path


def test_ingest_text_file(knowledge_dir):
    from crypto.src.ingest import DocumentIngester
    raw = knowledge_dir / "raw"
    (raw / "trend_template.txt").write_text(
        "The trend template requires the stock to be in a stage 2 uptrend. "
        "Price must be above the 150-day and 200-day moving averages. "
        "The VCP setup shows volatility contraction before a breakout."
    )
    ingester = DocumentIngester(knowledge_dir=str(knowledge_dir))
    result = ingester.ingest_all()
    assert result["processed"] == 1
    assert result["errors"] == 0
    assert result["new_frameworks"] >= 1


def test_ingest_json_chatgpt_export(knowledge_dir):
    from crypto.src.ingest import DocumentIngester
    raw = knowledge_dir / "raw"
    export = {
        "title": "Trading Discussion",
        "mapping": {
            "1": {
                "message": {
                    "author": {"role": "user"},
                    "content": {"parts": ["What is a pivot point breakout?"]},
                }
            },
            "2": {
                "message": {
                    "author": {"role": "assistant"},
                    "content": {
                        "parts": [
                            "A pivot point breakout occurs when price clears a key resistance level "
                            "on above-average volume. Position sizing should be 1-2% risk per trade. "
                            "Stop loss is placed below the pivot low."
                        ]
                    },
                }
            },
        },
    }
    (raw / "trading_chat.json").write_text(json.dumps(export))
    ingester = DocumentIngester(knowledge_dir=str(knowledge_dir))
    result = ingester.ingest_all()
    assert result["processed"] == 1


def test_ingest_skips_already_processed(knowledge_dir):
    from crypto.src.ingest import DocumentIngester
    raw = knowledge_dir / "raw"
    (raw / "doc.txt").write_text("trend template VCP breakout pivot")
    ingester = DocumentIngester(knowledge_dir=str(knowledge_dir))
    r1 = ingester.ingest_all()
    r2 = ingester.ingest_all()  # second call
    assert r2["processed"] == 0  # nothing new to process


def test_framework_search_returns_results(knowledge_dir):
    from crypto.src.ingest import DocumentIngester, FrameworkIndex
    raw = knowledge_dir / "raw"
    (raw / "rules.txt").write_text(
        "Trend template: price must be above 200MA. "
        "VCP setup: volatility contracts in stages. "
        "Stop loss: placed below pivot low. "
        "Position sizing: risk 1% per trade."
    )
    ingester = DocumentIngester(knowledge_dir=str(knowledge_dir))
    ingester.ingest_all()
    index = FrameworkIndex(knowledge_dir=str(knowledge_dir))
    results = index.search("trend template", limit=5)
    assert len(results) >= 1
    assert any("trend" in r["text"].lower() for r in results)


def test_framework_search_empty_on_no_match(knowledge_dir):
    from crypto.src.ingest import FrameworkIndex
    index = FrameworkIndex(knowledge_dir=str(knowledge_dir))
    results = index.search("xyzzy nonexistent term", limit=5)
    assert results == []
