"""Tests for the RAG retrieval logic.

These run fully offline: we stub the query embedding and the Pinecone HTTP
query, so no network, API keys, or live index are required.
"""
from src import rag


class _FakeResp:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


def _stub_retrieval(monkeypatch, matches):
    """Make host resolution and embedding succeed, and return the given matches."""
    monkeypatch.setattr(rag, '_resolve_host', lambda: 'fake-host')
    monkeypatch.setattr(rag, '_embed_query', lambda q: [0.1, 0.2, 0.3])
    monkeypatch.setattr(rag.requests, 'post',
                        lambda *a, **k: _FakeResp(200, {'matches': matches}))


def test_retrieve_returns_passages_above_threshold(monkeypatch):
    _stub_retrieval(monkeypatch, [
        {'score': 0.91, 'metadata': {'text': 'Heart disease information', 'page': 5}},
        {'score': 0.80, 'metadata': {'text': 'Diabetes information', 'page': 9}},
    ])
    results = rag.retrieve('chest pain', k=2)
    assert [r['text'] for r in results] == ['Heart disease information', 'Diabetes information']
    assert results[0]['page'] == 5


def test_retrieve_filters_low_scores(monkeypatch):
    _stub_retrieval(monkeypatch, [
        {'score': 0.90, 'metadata': {'text': 'relevant', 'page': 1}},
        {'score': 0.10, 'metadata': {'text': 'irrelevant', 'page': 2}},
    ])
    results = rag.retrieve('q', k=5, min_score=0.5)
    assert [r['text'] for r in results] == ['relevant']


def test_retrieve_empty_when_no_host(monkeypatch):
    monkeypatch.setattr(rag, '_resolve_host', lambda: None)
    assert rag.retrieve('anything') == []


def test_retrieve_empty_when_embedding_unavailable(monkeypatch):
    monkeypatch.setattr(rag, '_resolve_host', lambda: 'fake-host')
    monkeypatch.setattr(rag, '_embed_query', lambda q: None)
    assert rag.retrieve('anything') == []


def test_retrieve_empty_on_pinecone_error(monkeypatch):
    monkeypatch.setattr(rag, '_resolve_host', lambda: 'fake-host')
    monkeypatch.setattr(rag, '_embed_query', lambda q: [0.1, 0.2])
    monkeypatch.setattr(rag.requests, 'post', lambda *a, **k: _FakeResp(500, {}))
    assert rag.retrieve('anything') == []


def test_build_context_respects_char_budget(monkeypatch):
    _stub_retrieval(monkeypatch, [
        {'score': 0.9, 'metadata': {'text': 'A' * 100, 'page': 1}},
        {'score': 0.8, 'metadata': {'text': 'B' * 100, 'page': 2}},
    ])
    context = rag.build_context('general', k=2, char_budget=50)
    assert 0 < len(context) <= 50 + len('\n\n---\n\n')


def test_build_context_empty_when_nothing_found(monkeypatch):
    monkeypatch.setattr(rag, '_resolve_host', lambda: None)
    assert rag.build_context('q') == ''
