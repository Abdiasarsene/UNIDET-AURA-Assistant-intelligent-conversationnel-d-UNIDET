
import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FAQ_FILE = PROJECT_ROOT / "data" / "faq_unidet.txt"


def _comparison_text(value: str) -> str:
    """Prépare uniquement le texte utilisé pour la comparaison."""
    value = unicodedata.normalize("NFKD", value.lower())
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


@lru_cache(maxsize=1)
def load_faqs() -> tuple[dict, ...]:
    """Charge et prépare les FAQ une seule fois."""

    if not FAQ_FILE.is_file():
        raise FileNotFoundError(
            f"Fichier FAQ introuvable : {FAQ_FILE}"
        )

    text = FAQ_FILE.read_text(encoding="utf-8")

    pattern = re.compile(
        r"QUESTION:\s*(.*?)\s*REPONSE:\s*(.*?)(?=\n\s*QUESTION:|\Z)",
        flags=re.IGNORECASE | re.DOTALL,
    )

    faqs = []

    for question, answer in pattern.findall(text):
        question = question.strip()
        answer = answer.strip()

        if not question or not answer:
            continue

        faqs.append({
            "question": question,
            "answer": answer,
            "comparison_question": _comparison_text(question),
            "comparison_answer": _comparison_text(answer),
        })

    return tuple(faqs)


def search_faq(
    question: str,
    top_k: int = 3,
    min_score: float = 0.25,
) -> list[dict]:

    if not question or not question.strip():
        return []

    if top_k < 1:
        raise ValueError("top_k doit être supérieur à zéro.")

    query = _comparison_text(question)

    if not query:
        return []

    query_words = set(query.split())
    results = []

    for faq in load_faqs():

        faq_question = faq["comparison_question"]
        faq_answer = faq["comparison_answer"]

        question_similarity = SequenceMatcher(
            None, query, faq_question
        ).ratio()

        faq_words = set(
            (faq_question + " " + faq_answer).split()
        )

        overlap_score = (
            len(query_words & faq_words) / len(query_words)
        )

        score = max(question_similarity, overlap_score)

        if score >= min_score:
            results.append({
                "question": faq["question"],
                "answer": faq["answer"],
                "score": round(score, 3),
                "source": "faq_unidet.txt",
            })

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:top_k]


def retrieve_faq_context(
    question: str,
    top_k: int = 3,
) -> str:

    matches = search_faq(
        question,
        top_k=top_k,
    )

    if not matches:
        return ""

    return "\n\n".join(
        f"Question FAQ : {item['question']}\n"
        f"Réponse FAQ : {item['answer']}"
        for item in matches
    )