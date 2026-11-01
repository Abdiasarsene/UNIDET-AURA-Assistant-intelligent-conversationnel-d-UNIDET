import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL est absente du fichier .env")

try:
    with psycopg.connect(database_url, connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), version()")
            database, version = cur.fetchone()

            cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            result = cur.fetchone()

            print("Connexion PostgreSQL réussie.")
            print("Base :", database)
            print("Serveur :", version.split(",")[0])
            print(
                "Version pgvector :",
                result[0] if result else "Extension non activée"
            )

except psycopg.Error as exc:
    print("Échec de la connexion PostgreSQL :", exc)