import httpx
from typing import List
from backend.shared.env import settings

async def generate_embedding(text: str) -> List[float]:
    """Generates an embedding vector using local Ollama (e.g. nomic-embed-text)"""
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={
            "model": "nomic-embed-text",
            "prompt": text
        })
        response.raise_for_status()
        return response.json()["embedding"]

async def embed_event_summary(event_id: str, kind: str, company: str, role: str):
    """
    Creates a non-sensitive summary of the event (e.g., 'interview Google SWE Intern')
    and saves its vector embedding to MongoDB. This is used for semantic search.
    """
    from backend.shared.db import get_db
    
    # Strictly non-sensitive fields
    summary = f"{kind} {company or ''} {role or ''}".strip()
    
    vector = await generate_embedding(summary)
    
    db = await get_db()
    await db.events.update_one(
        {"_id": event_id},
        {"$set": {"embedding": vector, "embedding_summary": summary}}
    )
    return vector

# To create the Atlas Vector Search Index via MongoDB Atlas UI or CLI:
# {
#   "mappings": {
#     "dynamic": true,
#     "fields": {
#       "embedding": {
#         "dimensions": 768,
#         "similarity": "cosine",
#         "type": "knnVector"
#       }
#     }
#   }
# }
