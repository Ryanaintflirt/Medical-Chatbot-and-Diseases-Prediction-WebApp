"""Runtime Retrieval-Augmented Generation (RAG) helper for the medical chatbot.

At query time this embeds the user's question with the Gemini embedding API and
queries a Pinecone vector index (built offline from the medical reference book)
for the most relevant passages, which the chatbot injects into the model prompt
as grounding context.

Only ``requests`` is needed at runtime (no torch / no local model), so this
stays deployable on a small instance. Every failure path (missing config,
embedding or Pinecone error) degrades gracefully to "no context", so the
chatbot keeps working even when retrieval is unavailable.
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)

# --- Embedding (Gemini) -----------------------------------------------------
_EMBED_MODEL = (os.getenv('EMBED_MODEL') or 'gemini-embedding-001').strip()
_EMBED_DIM = int(os.getenv('EMBED_DIM', '768'))
_GEMINI_KEY = (os.getenv('GEMINI_API_KEY') or os.getenv('AiApi_Key') or '').strip()
_EMBED_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{_EMBED_MODEL}:embedContent'

# --- Vector store (Pinecone) ------------------------------------------------
_PINECONE_KEY = (os.getenv('PINECONE_API_KEY') or '').strip()
_INDEX_NAME = (os.getenv('PINECONE_INDEX') or 'medicalbot-gemini').strip()
_API_VERSION = '2024-07'
_PINECONE_HEADERS = {'Api-Key': _PINECONE_KEY, 'X-Pinecone-API-Version': _API_VERSION,
                     'Content-Type': 'application/json'}

_host = None            # resolved index host, cached for the process lifetime
_host_resolved = False


def _resolve_host():
    """Resolve (and cache) the Pinecone index host. Returns None if unavailable."""
    global _host, _host_resolved
    if _host_resolved:
        return _host
    _host_resolved = True
    # Allow an explicit host override to skip the control-plane lookup.
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
    """Embed a query with the Gemini embedding API; None on failure."""
    if not _GEMINI_KEY:
        return None
    try:
        resp = requests.post(
            _EMBED_URL,
            headers={'x-goog-api-key': _GEMINI_KEY, 'Content-Type': 'application/json'},
            json={
                'model': f'models/{_EMBED_MODEL}',
                'content': {'parts': [{'text': text}]},
                'taskType': 'RETRIEVAL_QUERY',
                'outputDimensionality': _EMBED_DIM,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning('Query embedding failed: %s', resp.status_code)
            return None
        return resp.json()['embedding']['values']
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning('Query embedding error: %s', exc)
        return None


def retrieve(query, k=4, min_score=0.5):
    """Return up to ``k`` relevant passages (dicts with 'text', 'page', 'score').

    Returns an empty list if retrieval is unavailable for any reason, so callers
    can always fall back to answering without grounding context.
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
        resp = requests.post(
            f'https://{host}/query',
            headers=_PINECONE_HEADERS,
            json={'vector': vector, 'topK': k, 'includeMetadata': True},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning('Pinecone query failed: %s', resp.status_code)
            return []
        matches = resp.json().get('matches', [])
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning('Pinecone query error: %s', exc)
        return []

    results = []
    for m in matches:
        score = float(m.get('score', 0.0))
        if score < min_score:
            continue
        md = m.get('metadata') or {}
        results.append({
            'text': md.get('text', ''),
            'page': md.get('page'),
            'score': score,
        })
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
