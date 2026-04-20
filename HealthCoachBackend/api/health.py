from fastapi import APIRouter
from sqlalchemy import text, inspect
from database import engine

router = APIRouter()


@router.get("/health/db")
def db_health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"db": "ok"}


@router.get("/debug/tables")
def list_tables():
    inspector = inspect(engine)
    return inspector.get_table_names()


@router.post("/admin/deduplicate-run-sessions")
def deduplicate_run_sessions():
    with engine.begin() as conn:
        before = conn.execute(text("SELECT COUNT(*) FROM run_sessions")).scalar() or 0

        conn.execute(
            text(
                """
                WITH ranked AS (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY user_id, start_time
                            ORDER BY id
                        ) AS rn
                    FROM run_sessions
                )
                DELETE FROM run_sessions rs
                USING ranked r
                WHERE rs.id = r.id
                  AND r.rn > 1
                """
            )
        )

        after = conn.execute(text("SELECT COUNT(*) FROM run_sessions")).scalar() or 0
        removed = before - after

        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'uq_run_user_start'
                    ) THEN
                        ALTER TABLE run_sessions
                        ADD CONSTRAINT uq_run_user_start UNIQUE (user_id, start_time);
                    END IF;
                END $$;
                """
            )
        )

    return {
        "status": "ok",
        "before_count": int(before),
        "after_count": int(after),
        "removed_duplicates": int(removed),
        "constraint": "uq_run_user_start",
    }


@router.get("/admin/run-sessions-duplicate-candidates")
def duplicate_candidates(limit: int = 50):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    user_id::text AS user_id,
                    DATE(start_time) AS day,
                    ROUND(COALESCE(distance_km, 0)::numeric, 2) AS distance_km_2d,
                    ROUND(COALESCE(duration_min, 0)::numeric, 1) AS duration_min_1d,
                    COUNT(*) AS cnt
                FROM run_sessions
                GROUP BY
                    user_id,
                    DATE(start_time),
                    ROUND(COALESCE(distance_km, 0)::numeric, 2),
                    ROUND(COALESCE(duration_min, 0)::numeric, 1)
                HAVING COUNT(*) > 1
                ORDER BY cnt DESC, day DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()

    return {"status": "ok", "rows": [dict(r) for r in rows], "count": len(rows)}


@router.post("/admin/deduplicate-run-sessions-fuzzy")
def deduplicate_run_sessions_fuzzy():
    """
    Dédoublonne les quasi-doublons (même user, même jour, distance/durée quasi identiques).
    Garde la ligne la plus ancienne (id minimum).
    """
    with engine.begin() as conn:
        before = conn.execute(text("SELECT COUNT(*) FROM run_sessions")).scalar() or 0

        conn.execute(
            text(
                """
                WITH ranked AS (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY
                                user_id,
                                DATE(start_time),
                                ROUND(COALESCE(distance_km, 0)::numeric, 2),
                                ROUND(COALESCE(duration_min, 0)::numeric, 1)
                            ORDER BY id
                        ) AS rn
                    FROM run_sessions
                )
                DELETE FROM run_sessions rs
                USING ranked r
                WHERE rs.id = r.id
                  AND r.rn > 1
                """
            )
        )

        after = conn.execute(text("SELECT COUNT(*) FROM run_sessions")).scalar() or 0
        removed = before - after

    return {
        "status": "ok",
        "before_count": int(before),
        "after_count": int(after),
        "removed_duplicates": int(removed),
        "mode": "fuzzy(day + rounded distance/duration)",
    }
