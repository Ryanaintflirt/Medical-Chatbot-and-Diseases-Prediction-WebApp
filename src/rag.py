"""Runtime Retrieval-Augmented Generation (RAG) helper for the medical chatbot.

At query time this embeds the user's question with a lightweight ONNX
MiniLM model (via fastembed — no torch) and queries the Pinecone index that was
built from the medical reference book (``medicalbot``). The most relevant
passages are injected into the chatbot prompt as grounding context.

Every failure path (missing model, Pinecone error) degrades gracefully to
"no context", so the chatbot keeps working even when retrieval is unavailable.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

_MODEL_NAME = (os.getenv('EMBED_MODEL') or 'sentence-transformers/all-MiniLM-L6-v2').strip()
_INDEX_NAME = (os.getenv('PINECONE_INDEX') or 'medicalbot').strip()
_PINECONE_KEY = (os.getenv('PINECONE_API_KEY') or '').strip()
_API_VERSION = '2024-07'
_PINECONE_HEADERS = {'Api-Key': _PINECONE_KEY, 'X-Pinecone-API-Version': _API_VERSION,
                     'Content-Type': 'application/json'}

_model = None           # fastembed TextEmbedding, lazily loaded and cached
_model_failed = False
_host = None            # resolved Pinecone index host, cached
_host_resolved = False


def _get_model():
    """Lazily load the embedding model once. Returns None if unavailable."""
    global _model, _model_failed
    if _model is not None:
        return _model
    if _model_failed:
        return None
    try:
        from fastembed import TextEmbedding
        _model = TextEmbedding(model_name=_MODEL_NAME)
        logger.info('Loaded embedding model %s', _MODEL_NAME)
        return _model
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning('Could not load embedding model (%s); RAG disabled: %s', _MODEL_NAME, exc)
        _model_failed = True
        return None


def _resolve_host():
    """Resolve (and cache) the Pinecone index host. Returns None if unavailable."""
    global _host, _host_resolved
    if _host_resolved:
        return _host
    _host_resolved = True
    env_host = (os.getenv('PINECONE_HOST') or '').strip()
    if env_host:
        _host = env_host
        return _host
    if not _PINECONE_KEY:
        logger.warning('PINECONE_API_KEY not set; chatbot will run without retrieval.')
        return None
    try:
        resp = requests.get(f'https://api.pinecone.io/indexes/{_INDEX_NAME}',
                            headers=_PINECONE_HEADERS, timeout=10)
        if resp.status_code == 200:
            _host = resp.json().get('host')
            logger.info('Resolved Pinecone index %s -> %s', _INDEX_NAME, _host)
        else:
            logger.warning('Could not resolve Pinecone index %s: %s', _INDEX_NAME, resp.status_code)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning('Pinecone host lookup failed: %s', exc)
    return _host


def _embed_query(text):
    """Embed a query with the local MiniLM model; None on failure."""
    model = _get_model()
    if model is None:
        return None
    try:
        return list(model.embed([text]))[0].tolist()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning('Query embedding error: %s', exc)
        return None


def retrieve(query, k=4, min_score=0.3):
    """Return up to ``k`` relevant passages (dicts with 'text', 'page', 'score').

    De-duplicates identical passages (the source index contains duplicates) and
    returns an empty list if retrieval is unavailable for any reason.
    """
    if not query:
        return []
    host = _resolve_host()
    if not host:
        return []
    vector = _embed_query(query)
    if vector is None:
        return []
    try:
        # Over-fetch so that de-duplication still leaves k distinct passages.
        resp = requests.post(
            f'https://{host}/query',
            headers=_PINECONE_HEADERS,
            json={'vector': vector, 'topK': k * 2, 'includeMetadata': True},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning('Pinecone query failed: %s', resp.status_code)
            return []
        matches = resp.json().get('matches', [])
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning('Pinecone query error: %s', exc)
        return []

    results, seen = [], set()
    for m in matches:
        score = float(m.get('score', 0.0))
        if score < min_score:
            continue
        md = m.get('metadata') or {}
        text = (md.get('text') or '').strip()
        key = text[:120]
        if not text or key in seen:
            continue
        seen.add(key)
        results.append({'text': text, 'page': md.get('page'), 'score': score})
        if len(results) >= k:
            break
    return results


def build_context(query, k=4, char_budget=3000):
    """Retrieve and format passages into a single context string for the prompt.

    Returns '' when nothing relevant is found.
    """
    passages = retrieve(query, k=k)
    if not passages:
        return ''
    parts, used = [], 0
    for p in passages:
        snippet = (p['text'] or '').strip()
        if not snippet:
            continue
        if used + len(snippet) > char_budget:
            snippet = snippet[: char_budget - used]
        parts.append(snippet)
        used += len(snippet)
        if used >= char_budget:
            break
    return '\n\n---\n\n'.join(parts)
