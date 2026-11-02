
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Iterator

from openai import OpenAI

from utils.config import settings

logger = logging.getLogger(__name__)

openai_client = OpenAI(
    api_key=settings.openai_api_key.get_secret_value(),
    timeout=30.0,
    max_retries=2,
)

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

ALLOWED_PROMPTS = {
    "fiche-identite.txt",
    "official-link.txt",
    "system_prompt.txt",
    "qa_prompt.txt",
    "summary_prompt.txt",
}

REQUIRED_PROMPTS = ALLOWED_PROMPTS.copy()

FALLBACK_ANSWER = (
    "Je ne dispose pas d'informations suffisantes dans la base de connaissances "
    "d'UNIDET pour répondre avec certitude. Je vous recommande de contacter "
    "l'équipe UNIDET sur pour obtenir une confirmation."
)

GENERATION_ERROR_ANSWER = (
    "Je rencontre une difficulté pour formuler la réponse. Veuillez réessayer."
)


@lru_cache(maxsize=len(ALLOWED_PROMPTS))
def load_prompt(filename: str) -> str:
    """Charge et conserve en mémoire un prompt autorisé."""

    if filename not in ALLOWED_PROMPTS:
        raise ValueError(f"Fichier de prompt non autorisé : {filename}")

    prompt_path = PROMPT_DIR / filename

    try:
        prompt = prompt_path.read_text(encoding="utf-8").strip()

    except OSError as exc:
        logger.error(
            "Impossible de lire le prompt %s : %s",
            prompt_path,
            exc,
        )
        raise RuntimeError(
            f"Impossible de charger le prompt {filename}."
        ) from exc

    if not prompt:
        raise RuntimeError(f"Le prompt {filename} est vide.")

    return prompt


def validate_prompt_resources() -> None:
    """Vérifie les ressources obligatoires au démarrage."""

    for filename in REQUIRED_PROMPTS:
        load_prompt(filename)

    logger.info(
        "Toutes les ressources de prompts sont disponibles (%s fichiers).",
        len(REQUIRED_PROMPTS),
    )


# Vérification au démarrage.
validate_prompt_resources()


@lru_cache(maxsize=2)
def build_instructions(task_prompt: str) -> str:
    """Combine et conserve les instructions système et métier."""

    return (
        f"{load_prompt('system_prompt.txt')}\n\n"
        f"{load_prompt(task_prompt)}"
    )


def _format_vector_context(
    chunks: list[dict],
) -> list[dict[str, str | None]]:
    """Normalise les passages issus de la recherche vectorielle."""

    formatted_chunks = []

    for chunk in chunks or []:
        content = chunk.get("content")

        if not isinstance(content, str) or not content.strip():
            continue

        formatted_chunks.append({
            "titre": chunk.get("title") or "Document UNIDET",
            "url": chunk.get("url"),
            "contenu": content.strip(),
        })

    return formatted_chunks


def generate_answer_stream(
    question: str,
    chunks: list[dict],
    web_context: str = "",
    faq_context: str = "",
    identity_context: str = "",
    official_links_context: str = "",
) -> Iterator[str]:
    """Génère une réponse progressive à partir des sources disponibles."""

    question = (question or "").strip()

    if not question:
        raise ValueError("La question ne peut pas être vide.")

    # Ressources institutionnelles conservées en mémoire.
    identity_context = load_prompt("fiche-identite.txt")
    official_links_context = load_prompt("official-link.txt")

    vector_context = _format_vector_context(chunks)
    web_context = (web_context or "").strip()
    faq_context = (faq_context or "").strip()

    if not vector_context and not web_context and not faq_context:
        yield FALLBACK_ANSWER
        return

    user_message = (
        f"QUESTION DU VISITEUR :\n{question}\n\n"
        "IDENTITÉ INSTITUTIONNELLE UNIDET :\n"
        f"{identity_context}\n\n"
        "LIENS OFFICIELS UNIDET :\n"
        f"{official_links_context}\n\n"
        "CONTEXTE DOCUMENTAIRE UNIDET — RECHERCHE VECTORIELLE :\n"
        f"{json.dumps(vector_context, ensure_ascii=False)}\n\n"
        "CONTEXTE WEB — RECHERCHE LIMITÉE À unidet.fr :\n"
        f"{web_context or 'Aucun résultat web exploitable.'}\n\n"
        "CONTEXTE FAQ UNIDET — FICHIER LOCAL :\n"
        f"{faq_context or 'Aucun résultat FAQ exploitable.'}\n"
    )

    try:
        stream = openai_client.responses.create(
            model=settings.openai_model,
            instructions=build_instructions("qa_prompt.txt"),
            input=user_message,
            max_output_tokens=5000,
            stream=True,
        )

        received_text = False
        completion_status = None
        incomplete_reason = None

        for event in stream:
            event_type = event.type

            if event_type == "response.output_text.delta":
                received_text = True
                yield event.delta

            elif event_type == "response.completed":
                completion_status = event.response.status

            elif event_type == "response.incomplete":
                completion_status = event.response.status
                details = event.response.incomplete_details

                incomplete_reason = (
                    details.reason if details else "inconnue"
                )

                logger.warning(
                    "Génération incomplète : raison=%s",
                    incomplete_reason,
                )

            elif event_type in (
                "response.failed",
                "response.error",
                "error",
            ):
                logger.error(
                    "Événement d'erreur OpenAI : %s",
                    event,
                )
                raise RuntimeError(
                    "Erreur reçue pendant la génération de la réponse."
                )

        if completion_status == "incomplete":
            raise RuntimeError(
                "Génération interrompue : "
                f"{incomplete_reason or 'raison inconnue'}."
            )

        if completion_status != "completed":
            raise RuntimeError(
                "Fin de génération non confirmée : "
                f"{completion_status!r}."
            )

        if not received_text:
            logger.error(
                "Le modèle n'a retourné aucun texte pour la question."
            )
            yield GENERATION_ERROR_ANSWER

    except Exception:
        logger.exception("Échec de la génération de réponse UNIDET.")
        raise


def generate_summary(
    content: str,
    language: str | None = None,
) -> str:
    """Résume fidèlement un contenu dans la langue demandée."""

    content = (content or "").strip()

    if not content:
        raise ValueError("Le contenu à résumer ne peut pas être vide.")

    language_instruction = (
        f"Rédige le résumé en {language.strip()}.\n\n"
        if language and language.strip()
        else ""
    )

    user_message = (
        f"{language_instruction}"
        "Résume fidèlement le contenu suivant. "
        "N'ajoute aucune information absente du texte.\n\n"
        f"CONTENU À RÉSUMER :\n{content}"
    )

    try:
        response = openai_client.responses.create(
            model=settings.openai_model,
            instructions=build_instructions("summary_prompt.txt"),
            input=user_message,
            max_output_tokens=2000,
        )

        summary = (response.output_text or "").strip()

        if not summary:
            raise RuntimeError("Le modèle n'a retourné aucun résumé.")

        return summary

    except Exception:
        logger.exception("Échec de la génération du résumé UNIDET.")
        raise