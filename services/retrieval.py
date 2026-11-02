
from functools import lru_cache

from openai import OpenAI

from db.database import search_similar_chunks
from utils.config import settings


openai_client = OpenAI(
    api_key=settings.openai_api_key.get_secret_value()
)


@lru_cache(maxsize=256)
def _cached_embedding(question: str) -> tuple[float, ...]:
    """Calcule et conserve temporairement l'embedding d'une question."""

    response = openai_client.embeddings.create(
        model=settings.openai_embed_model,
        input=question,
        dimensions=settings.openai_embed_dimension,
    )

    if not response.data:
        raise RuntimeError("OpenAI n'a renvoyé aucun embedding.")

    embedding = response.data[0].embedding

    if len(embedding) != settings.openai_embed_dimension:
        raise RuntimeError("La dimension de l'embedding est inattendue.")

    return tuple(embedding)


def embed_query(question: str) -> list[float]:
    """Transforme une question en embedding OpenAI."""

    question = question.strip()

    if not question:
        raise ValueError("La question ne peut pas être vide.")

    return list(_cached_embedding(question))


def retrieve_context(question: str) -> list[dict]:
    """Retourne les passages pertinents pour une question."""

    embedding = embed_query(question)
    chunks = search_similar_chunks(embedding)

    results = []

    for chunk in chunks:
        metadata = chunk.get("metadata") or {}

        if not isinstance(metadata, dict):
            metadata = {}

        title = (
            metadata.get("title")
            or chunk.get("source_name")
            or chunk.get("chunk_name")
            or "Document UNIDET"
        )

        url = metadata.get("url") or metadata.get("source_url")

        results.append({
            "content": chunk["content"],
            "title": title,
            "url": url,
            "similarity": float(chunk["similarity"]),
        })

    return results