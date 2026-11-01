# db/database.py
import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from utils.config import settings 

def search_similar_chunks(
    query_embedding: list[float],
    top_k: int | None = None,
) -> list[dict]:
    """Recherche les segments les plus proches par distance cosinus."""

    dimension = settings.openai_embed_dimension

    if len(query_embedding) != dimension:
        raise ValueError(
            f"Dimension incorrecte : {len(query_embedding)} "
            f"au lieu de {dimension}."
        )

    limit = top_k if top_k is not None else settings.retrieval_top_k

    if limit < 1:
        raise ValueError("top_k doit être supérieur à zéro.")

    sql = """
        SELECT
            dc.id AS chunk_id,
            dc.content,
            dc.chunk_name,
            dc.chunk_index,
            pd.id AS document_id,
            pd.source_name,
            pd.source_type,
            pd.project,
            pd.metadata,
            1 - (ce.embedding <=> %s) AS similarity
        FROM chunk_embeddings AS ce
        JOIN document_chunks AS dc
            ON dc.id = ce.chunk_id
        JOIN processed_documents AS pd
            ON pd.id = dc.document_id
        WHERE ce.model_name = %s
        ORDER BY ce.embedding <=> %s
        LIMIT %s;
    """

    vector = Vector(query_embedding)

    with psycopg.connect(
        settings.database_url.get_secret_value(),
        row_factory=dict_row,
    ) as conn:
        register_vector(conn)

        with conn.cursor() as cursor:
            cursor.execute(
                sql,
                (
                    vector,
                    settings.openai_embed_model,
                    vector,
                    limit,
                ),
            )
            return [dict(row) for row in cursor.fetchall()]
