"""Offline RAG ingestion: build the medical knowledge index for the chatbot.

Reads the medical reference PDF, splits it into chunks with LangChain, embeds
each chunk with the Gemini embedding API, and writes a compact index the web
app loads at runtime:

    data/medical_index.npz    - L2-normalised float32 matrix [n_chunks, dim]
    data/medical_chunks.json  - the chunk texts + page numbers, index-aligned

Run once (locally) whenever the source PDF changes, then commit the two output
files so the deployed app needs no heavy ML dependencies:

    python build_rag_index.py
"""
import json
import os
import time

import numpy as np
import requests
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

PDF_PATH = os.path.join('data', 'Medical_book.pdf')
INDEX_PATH = os.path.join('data', 'medical_index.npz')
CHUNKS_PATH = os.path.join('data', 'medical_chunks.json')

EMBED_MODEL = os.getenv('EMBED_MODEL', 'gemini-embedding-001')
EMBED_DIM = int(os.getenv('EMBED_DIM', '768'))  # Matryoshka truncation keeps it light
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
# The free-tier embedding quota is a per-minute rate limit, so we send single
# calls at a steady pace instead of bursting batches (which trip 429s).
EMBED_PAUSE = float(os.getenv('EMBED_PAUSE', '0.8'))  # seconds between calls
CKPT_EVERY = 25  # checkpoint frequency (chunks)
CKPT_PATH = os.path.join('data', '_rag_ckpt.npy')  # resume progress if interrupted

API_KEY = (os.getenv('GEMINI_API_KEY') or os.getenv('AiApi_Key') or '').strip()
EMBED_URL = f'https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}:embedContent'
HEADERS = {'x-goog-api-key': API_KEY, 'Content-Type': 'application/json'}


def embed_one(text, task_type='RETRIEVAL_DOCUMENT', max_retries=8):
    """Embed a single text, returning its vector (with retry/backoff on 429)."""
    body = {
        'model': f'models/{EMBED_MODEL}',
        'content': {'parts': [{'text': text}]},
        'taskType': task_type,
        'outputDimensionality': EMBED_DIM,
    }
    for attempt in range(max_retries):
        resp = requests.post(EMBED_URL, headers=HEADERS, json=body, timeout=60)
        if resp.status_code == 200:
            return resp.json()['embedding']['values']
        if resp.status_code in (429, 500, 503):
            wait = min(2 ** attempt, 60)
            print(f'  rate/limit {resp.status_code}; retrying in {wait}s', flush=True)
            time.sleep(wait)
            continue
        raise RuntimeError(f'Embedding failed {resp.status_code}: {resp.text[:300]}')
    raise RuntimeError('Embedding failed after retries')


def main():
    if not API_KEY:
        raise SystemExit('GEMINI_API_KEY is not set (put it in .env).')

    print(f'Loading {PDF_PATH} ...')
    docs = PyPDFLoader(PDF_PATH).load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = [c for c in splitter.split_documents(docs) if c.page_content.strip()]
    print(f'{len(docs)} pages -> {len(chunks)} chunks')

    texts = [c.page_content for c in chunks]
    meta = [{'text': c.page_content, 'page': c.metadata.get('page')} for c in chunks]

    # Resume from a checkpoint if a previous run was interrupted (e.g. quota).
    vectors = []
    if os.path.exists(CKPT_PATH):
        vectors = list(np.load(CKPT_PATH))
        print(f'Resuming from checkpoint: {len(vectors)} chunks already embedded')

    for i in range(len(vectors), len(texts)):
        vectors.append(embed_one(texts[i]))
        if (i + 1) % CKPT_EVERY == 0 or i + 1 == len(texts):
            np.save(CKPT_PATH, np.asarray(vectors, dtype=np.float32))  # checkpoint
            print(f'  embedded {i + 1}/{len(texts)}', flush=True)
        time.sleep(EMBED_PAUSE)

    mat = np.asarray(vectors, dtype=np.float32)
    # Normalise so cosine similarity is a plain dot product at query time.
    mat /= (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8)

    np.savez_compressed(INDEX_PATH, vectors=mat)
    with open(CHUNKS_PATH, 'w') as f:
        json.dump(meta, f)
    if os.path.exists(CKPT_PATH):
        os.remove(CKPT_PATH)
    print(f'Saved {mat.shape} index to {INDEX_PATH} and chunks to {CHUNKS_PATH}')


if __name__ == '__main__':
    main()
