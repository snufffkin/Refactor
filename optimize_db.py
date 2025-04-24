from sqlalchemy import text
import pandas as pd
from core import get_engine, load_data, risk_score

def optimize_db():
    """Создаёт materialized view, плоскую таблицу, таблицу кэша риска и топ-10 карточек по группам, а также необходимые индексы."""
    engine = get_engine()
    # 1. Materialized View для cards_mv
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_cards_mv;")
        conn.exec_driver_sql(
            """
            CREATE MATERIALIZED VIEW mv_cards_mv AS
            SELECT
                s.program, s.module, s.module_order, s.lesson, s.lesson_order,
                s.gz, s.gz_id, s.card_id, s.card_type, s.card_url,
                m.total_attempts, m.attempted_share, m.success_rate,
                m.first_try_success_rate, m.complaint_rate, m.complaints_total,
                m.discrimination_avg, m.success_attempts_rate,
                COALESCE(st.status,'new') AS status, st.updated_at
            FROM cards_structure s
            JOIN cards_metrics m USING(card_id)
            LEFT JOIN card_status st USING(card_id);
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_program ON mv_cards_mv (program);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_filters ON mv_cards_mv (program, module, lesson, gz);"
        )

    # 2. Плоская таблица cards_flat
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS cards_flat;")
        conn.exec_driver_sql("CREATE TABLE cards_flat AS SELECT * FROM mv_cards_mv;")
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_flat_filters ON cards_flat (program, module, lesson, gz);"
        )

    # 3. Кэш риска: card_risk_cache
    df = load_data(engine)
    df['risk'] = df.apply(risk_score, axis=1)
    df_cache = df[['card_id','risk']].copy()
    df_cache['updated_at'] = pd.Timestamp.utcnow()
    df_cache.to_sql('card_risk_cache', engine, if_exists='replace', index=False)

    # 4. Топ-10 карточек по каждой группе: top10_by_group
    df_top = (
        df[['gz','card_id','risk']]
        .sort_values(['gz','risk'], ascending=[True,False])
        .groupby('gz')
        .head(10)
        .assign(rn=lambda d: d.groupby('gz').cumcount()+1)
    )
    df_top.to_sql('top10_by_group', engine, if_exists='replace', index=False)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_top10_gz_rn ON top10_by_group (gz, rn);"
        )

if __name__ == '__main__':
    optimize_db()
