from pathlib import Path

import pytest

from whywiki.services.ask import ask_project
from whywiki.services.ingest import ingest_path
from whywiki.services.wiki_engine import build_project
from whywiki.services.workspace import create_project


def build_messy_fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("WHYWIKI_DATA_DIR", str(tmp_path / "data"))
    project = create_project("Fixture Project")
    root = Path(__file__).resolve().parent / "fixtures" / "messy-project"
    ingest_path(project["id"], root)
    build_project(project["id"])
    return project


def test_ask_returns_structured_evidence(tmp_path, monkeypatch):
    project = build_messy_fixture(tmp_path, monkeypatch)

    result = ask_project(project["id"], "接口是什么？")

    assert result["evidence"]
    assert {"kind", "id", "path", "score"}.issubset(result["evidence"][0])
    assert "证据" in result["answer"]


def test_ask_returns_evidence_for_exact_docker_term(tmp_path, monkeypatch):
    project = build_messy_fixture(tmp_path, monkeypatch)

    result = ask_project(project["id"], "Docker")

    assert result["evidence"]
    assert "证据" in result["answer"]


def test_ask_returns_evidence_for_exact_post_term(tmp_path, monkeypatch):
    project = build_messy_fixture(tmp_path, monkeypatch)

    result = ask_project(project["id"], "POST")

    assert result["evidence"]
    assert "证据" in result["answer"]


def test_ask_returns_detected_conflicts_for_conflict_question(tmp_path, monkeypatch):
    project = build_messy_fixture(tmp_path, monkeypatch)

    result = ask_project(project["id"], "这个项目当前有哪些冲突？")

    assert any(item["kind"] == "conflict" for item in result["evidence"])
    assert "当前检测到以下待审查冲突" in result["answer"]
    assert "多个材料都声称自己是最新版或最终版" in result["answer"]
    assert "证据" in result["answer"]


def test_ask_refuses_method_without_matching_evidence(tmp_path, monkeypatch):
    project = build_messy_fixture(tmp_path, monkeypatch)

    result = ask_project(project["id"], "GET")

    assert result["evidence"] == []
    assert "没有找到足够证据" in result["answer"]


def test_ask_refuses_without_evidence(tmp_path, monkeypatch):
    project = build_messy_fixture(tmp_path, monkeypatch)

    result = ask_project(project["id"], "火星基地预算是多少？")

    assert result["evidence"] == []
    assert "没有找到足够证据" in result["answer"]


@pytest.mark.parametrize("question", ["用户预算是多少？", "用户收费是多少？", "模型预算是多少？"])
def test_ask_refuses_unsupported_pricing_intent_with_known_terms(tmp_path, monkeypatch, question):
    project = build_messy_fixture(tmp_path, monkeypatch)

    result = ask_project(project["id"], question)

    assert result["evidence"] == []
    assert "没有找到足够证据" in result["answer"]
