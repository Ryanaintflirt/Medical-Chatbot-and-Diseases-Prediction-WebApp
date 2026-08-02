"""Push the locally-built Gemini embeddings into a Pinecone index.

Reads the vectors/chunks produced by ``build_rag_index.py`` and upserts them
into a serverless Pinecone index (created if it does not yet exist). The web
app then queries this index at runtime (see ``src/rag.py``).

    python push_to_pinecone.py

Env:
    PINECONE_API_KEY   (required)
    PINECONE_INDEX     index name        (default: medicalbot-gemini)
    PINECONE_CLOUD     serverless cloud  (default: aws)
    PINECONE_REGION    serverless region (default: us-east-1)
"""
import json
import os
import time

import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

INDEX_PATH = os.path.join('data', 'medical_index.npz')
CHUNKS_PATH = os.path.join('data', 'medical_chunks.json')

API_KEY = (os.getenv('PINECONE_API_KEY') or '').strip()
INDEX_NAME = (os.getenv('PINECONE_INDEX') or 'medicalbot-gemini').strip()
CLOUD = (os.getenv('PINECONE_CLOUD') or 'aws').strip()
REGION = (os.getenv('PINECONE_REGION') or 'us-east-1').strip()
API_VERSION = '2024-07'
CONTROL = 'https://api.pinecone.io'
UPSERT_BATCH = 100

_HEADERS = {'Api-Key': API_KEY, 'X-Pinecone-API-Version': API_VERSION, 'Content-Type': 'application/json'}


def ensure_index(dim):
    """Create the serverless index if missing; return its host, waiting until ready."""
    r = requests.get(f'{CONTROL}/indexes/{INDEX_NAME}', headers=_HEADERS, timeout=30)
    if r.status_code == 404:
        print(f'Creating index {INDEX_NAME} (dim={dim}) ...')
        body = {
            'name': INDEX_NAME,
            'dimension': dim,
            'metric': 'cosine',
            'spec': {'serverless': {'cloud': CLOUD, 'region': REGION}},
        }
        c = requests.post(f'{CONTROL}/indexes', headers=_HEADERS, json=body, timeout=30)
        if c.status_code not in (200, 201, 202):
            raise RuntimeError(f'Create index failed {c.status_code}: {c.text[:300]}')
    elif r.status_code != 200:
        raise RuntimeError(f'Describe index failed {r.status_code}: {r.text[:300]}')

    for _ in range(60):
        d = requests.get(f'{CONTROL}/indexes/{INDEX_NAME}', headers=_HEADERS, timeout=30).json()
        if d.get('status', {}).get('ready'):
            return d['host']
        time.sleep(2)
    raise RuntimeError('Index did not become ready in time')


def main():
    if not API_KEY:
        raise SystemExit('PINECONE_API_KEY is not set (put it in .env).')

    vectors = np.load(INDEX_PATH)['vectors']
    with open(CHUNKS_PATH) as f:
        meta = json.load(f)
    assert len(vectors) == len(meta), 'vectors/chunks length mismatch'
    print(f'Loaded {vectors.shape} vectors and {len(meta)} chunks')

    host = ensure_index(vectors.shape[1])
    upsert_url = f'https://{host}/vectors/upsert'

    for i in range(0, len(vectors), UPSERT_BATCH):
        batch = []
        for j in range(i, min(i + UPSERT_BATCH, len(vectors))):
            text = meta[j]['text'][:4000]  # keep well under Pinecone's metadata limit
            batch.append({
                'id': f'chunk-{j}',
                'values': [float(x) for x in vectors[j]],
                'metadata': {'text': text, 'page': meta[j].get('page') or -1},
            })
        resp = requests.post(upsert_url, headers=_HEADERS, json={'vectors': batch}, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f'Upsert failed {resp.status_code}: {resp.text[:300]}')
        print(f'  upserted {min(i + UPSERT_BATCH, len(vectors))}/{len(vectors)}', flush=True)

    print(f'Done. Index "{INDEX_NAME}" host: {host}')
    print('Set this in the deploy env as PINECONE_HOST (optional; the app can also resolve it by name).')


if __name__ == '__main__':
    main()
