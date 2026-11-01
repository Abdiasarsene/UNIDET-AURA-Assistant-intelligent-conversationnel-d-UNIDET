# api/chat.py
import json
import logging
from collections.abc import Iterator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from services.retrieval import retrieve_context
from services.faq_retrieval import retrieve_faq_context
from services.llm import generate_answer_stream
from schemas.chat import ChatRequest
from services.scope import (
    is_obviously_out_of_scope,
    OUT_OF_SCOPE_ANSWER,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def sse_event(event: str, data: dict) -> str:
    """Formate un événement Server-Sent Events."""
    return (
        f"event: {event}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    )


@router.post("/chat")
def chat(request: ChatRequest) -> StreamingResponse:
    # 1. Contrôle du périmètre avant tout appel externe.
    if is_obviously_out_of_scope(request.question):

        def reject() -> Iterator[str]:
            yield sse_event("sources", {"sources": []})
            yield sse_event(
                "token",
                {"text": OUT_OF_SCOPE_ANSWER},
            )
            yield sse_event("done", {"status": "completed"})

        return StreamingResponse(
            reject(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    # 2. Recherche documentaire uniquement si nécessaire.
    try:
        chunks = retrieve_context(request.question)
        faq_context = retrieve_faq_context(request.question)
    except Exception:
        logger.exception(
            "Échec de la recherche documentaire ou de la récupération FAQ."
        )
        raise HTTPException(
            status_code=503,
            detail="Le service est temporairement indisponible.",
        ) from None

    # 3. Préparation des sources.
    sources = []
    seen_sources = set()

    for chunk in chunks:
        title = chunk.get("title") or "Document UNIDET"
        url = chunk.get("url")
        key = url or title

        if key in seen_sources:
            continue

        seen_sources.add(key)
        sources.append({
            "title": title,
            "url": url,
        })

    # 4. Génération progressive de la réponse.
    def generate() -> Iterator[str]:
        yield sse_event("sources", {"sources": sources})

        try:
            for delta in generate_answer_stream(
                request.question,
                chunks,
                faq_context=faq_context,
            ):
                yield sse_event("token", {"text": delta})

            yield sse_event("done", {"status": "completed"})

        except Exception:
            logger.exception("Échec du streaming de la réponse.")
            yield sse_event(
                "error",
                {
                    "message": (
                        "Une erreur est survenue pendant la génération."
                    )
                },
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )