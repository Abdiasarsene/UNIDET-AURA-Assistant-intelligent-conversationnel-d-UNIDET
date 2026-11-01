
# services/scope.py

import re
import unicodedata


OUT_OF_SCOPE_PATTERNS = [
    # Programmation
    r"\b(write|debug|fix|generate)\s+(me\s+)?(some\s+)?"
    r"(python|javascript|java|c\+\+)\s+code\b",
    r"\b(code|programme|script)\s+(en|with)\s+"
    r"(python|javascript|java|c\+\+)\b",

    # Cuisine
    r"\b(recipe|recette|cuisiner|cuisine|cook(?:ing)?)\b",

    # Météo
    r"\b(weather|météo|forecast|prévision météo)\b",

    # Sport sans rapport avec UNIDET
    r"\b(match|score|classement|résultat)\s+(de\s+)?"
    r"(football|soccer|basketball|tennis)\b",
    r"\b(meilleur joueur|best player|classement de la liga)\b",
    r"\b(barcelone|barcelona|real madrid)\b",

    # Divertissement
    r"\b(raconte|tell me)\s+(a\s+)?(joke|blague)\b",
    r"\b(écris|write)\s+(moi\s+)?(un|une|a)\s+"
    r"(poème|poem|chanson|song|histoire)\b",

    # Vie personnelle et conversations sans lien avec UNIDET
    r"\b(je suis|i am|i'm)\s+"
    r"(beau|belle|heureux|heureuse|triste|fatigué|fatiguée)\b",
    r"\b(mon signe astrologique|horoscope|compatibilité amoureuse)\b",
    r"\b(raconte-moi une histoire|tell me a story)\b",
]


# Une objection commerciale ou une question sur UNIDET
# ne doit pas être bloquée par les règles générales.
IN_SCOPE_PATTERNS = [
    r"\b(unidet|nos services|vos services|votre entreprise)\b",
    r"\b(recouvrement|créance|créances|débiteur|débiteurs)\b",
    r"\b(facture impayée|factures impayées|impayé|impayés)\b",
    r"\b(tarif|tarifs|prix|commission|frais|honoraires)\b",
    r"\b(concurrent|concurrents|concurrence)\b",
    r"\b(dossier|confier|déposer|suivre mon dossier)\b",
    r"\b(contact|contacter|rendez-vous|espace client)\b",
    r"\b(délai|délais|garantie|garanties|paiement)\b",
]


def normalize_text(text: str) -> str:
    """Normalise le texte pour faciliter les comparaisons."""
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    return "".join(
        char for char in text
        if not unicodedata.combining(char)
    )


def is_obviously_out_of_scope(question: str) -> bool:
    """Détecte certaines demandes manifestement hors périmètre."""
    if not question or not question.strip():
        return False

    normalized = normalize_text(question)

    # Préserver les questions métier et les objections commerciales.
    if any(
        re.search(pattern, normalized, re.IGNORECASE)
        for pattern in IN_SCOPE_PATTERNS
    ):
        return False

    return any(
        re.search(pattern, normalized, re.IGNORECASE)
        for pattern in OUT_OF_SCOPE_PATTERNS
    )


OUT_OF_SCOPE_ANSWER = (
    "Je suis là pour vous renseigner sur les services d’UNIDET. "
    "Je ne peux donc pas traiter cette demande."
)