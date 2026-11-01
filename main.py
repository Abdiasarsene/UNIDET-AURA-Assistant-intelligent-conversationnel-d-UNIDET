# main.py
import logging
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.chat import router as chat_router
from utils.config import settings


logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

APP_ENV = settings.app_env.strip().lower()
IS_PRODUCTION = APP_ENV == "production"


def parse_frontend_origins(value: str) -> list[str]:
    """Parse and validate comma-separated frontend origins from configuration."""
    origins: list[str] = []

    for item in (value or "").split(","):
        origin = item.strip().rstrip("/")
        if not origin:
            continue

        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
        ):
            raise RuntimeError(
                f"Origine frontend invalide dans FRONTEND_ORIGINS : {item!r}. "
                "Utilisez uniquement une origine, par exemple https://aura.unidet.fr."
            )

        origins.append(origin)

    # Supprime les doublons tout en conservant l'ordre.
    return list(dict.fromkeys(origins))


frontend_origins = parse_frontend_origins(settings.frontend_origins)

if IS_PRODUCTION and not frontend_origins:
    raise RuntimeError(
        "FRONTEND_ORIGINS doit être configuré en production, "
        "par exemple https://aura.unidet.fr."
    )

# En développement seulement : autorise les ports locaux habituels.
dev_origin_regex = None if IS_PRODUCTION else r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

app = FastAPI(
    title="UNIDET AURA API",
    description="API de l'assistant intelligent UNIDET",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    frontend_origins,
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "https://unidet.com",
    ],
    allow_origin_regex=dev_origin_regex,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    # À activer uniquement si l'API utilise des cookies ou des sessions navigateur.
    allow_credentials=False,
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(
    chat_router,
    prefix="/api/v1",
    tags=["Chat"],
)

logger.info(
    "UNIDET AURA API initialisée (environnement=%s, origines_frontend=%s)",
    APP_ENV or "non défini",
    frontend_origins,
)