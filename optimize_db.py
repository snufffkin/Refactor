from sqlalchemy import text
import pandas as pd
from core import get_engine, load_raw_data, process_data, risk_score

def optimize_db():
    """Создаёт materialized view, плоскую таблицу, таблицу кэша риска и топ-10 карточек по группам, а также необходимые индексы."""
    engine = get_engine()
    
    # Сначала удаляем все зависимые материализованные представления в правильном порядке
    with engine.begin() as conn:
        # Сначала удаляем представления с риском, которые зависят от статистик
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_gz_risk;")
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_lesson_risk;")
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_module_risk;")
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_program_risk;")
        
        # Затем удаляем представления со статистиками, которые зависят от базового представления
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_gz_stats;")
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_lesson_stats;")
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_module_stats;")
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_program_stats;")
        
        # Теперь можно безопасно удалить базовое представление
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_cards_mv;")
        
        # 1. Создаем базовое материализованное представление mv_cards_mv
        conn.exec_driver_sql(
            """
            CREATE MATERIALIZED VIEW mv_cards_mv AS
            SELECT
                s.program, s.module, s.module_order, s.lesson, s.lesson_order,
                s.gz, s.gz_id, s.card_id, s.card_type, s.card_url,
                m.total_attempts, m.attempted_share, m.success_rate,
                m.first_try_success_rate, m.complaint_rate, m.complaints_total,
                m.discrimination_avg, m.success_attempts_rate,
                m.time_median, m.complaints_text,
                COALESCE(st.status,'new') AS status, st.updated_at
            FROM cards_structure s
            JOIN cards_metrics m USING(card_id)
            LEFT JOIN card_status st USING(card_id);
            """
        )
        # Основные индексы для mv_cards_mv
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_program ON mv_cards_mv (program);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_filters ON mv_cards_mv (program, module, lesson, gz);"
        )
        # Дополнительные индексы для mv_cards_mv
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_card_id ON mv_cards_mv (card_id);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_program_module ON mv_cards_mv (program, module);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_program_module_lesson ON mv_cards_mv (program, module, lesson);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_module ON mv_cards_mv (module);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_lesson ON mv_cards_mv (lesson);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_gz ON mv_cards_mv (gz);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_module_order ON mv_cards_mv (module_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_lesson_order ON mv_cards_mv (lesson_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_status ON mv_cards_mv (status);"
        )
        # Составные индексы для сортировки
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_mv_program_module_orders ON mv_cards_mv (program, module_order, lesson_order);"
        )
        
        # Создаем материализованные представления для каждого уровня навигации
        
        # 2. Уровень программ (program)
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_program_stats;")
        conn.exec_driver_sql(
            """
            CREATE MATERIALIZED VIEW mv_program_stats AS
            SELECT 
                program,
                COUNT(DISTINCT card_id) AS card_count,
                AVG(success_rate) AS avg_success_rate,
                AVG(complaint_rate) AS avg_complaint_rate,
                AVG(attempted_share) AS avg_attempted_share,
                AVG(discrimination_avg) AS avg_discrimination,
                SUM(total_attempts) AS total_attempts_sum,
                AVG(time_median) AS avg_time_median,
                SUM(time_median) AS total_time_median,
                COUNT(DISTINCT module) AS module_count,
                COUNT(DISTINCT lesson) AS lesson_count,
                COUNT(DISTINCT gz) AS gz_count,
                MAX(updated_at) AS last_updated
            FROM mv_cards_mv
            GROUP BY program;
            """
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_program_stats ON mv_program_stats (program);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_program_stats_success ON mv_program_stats (avg_success_rate);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_program_stats_complaint ON mv_program_stats (avg_complaint_rate);"
        )
        
        # 3. Уровень модулей (module)
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_module_stats;")
        conn.exec_driver_sql(
            """
            CREATE MATERIALIZED VIEW mv_module_stats AS
            SELECT 
                program,
                module,
                module_order,
                COUNT(DISTINCT card_id) AS card_count,
                AVG(success_rate) AS avg_success_rate,
                AVG(complaint_rate) AS avg_complaint_rate,
                AVG(attempted_share) AS avg_attempted_share,
                AVG(discrimination_avg) AS avg_discrimination,
                SUM(total_attempts) AS total_attempts_sum,
                AVG(time_median) AS avg_time_median,
                SUM(time_median) AS total_time_median,
                COUNT(DISTINCT lesson) AS lesson_count,
                COUNT(DISTINCT gz) AS gz_count,
                MAX(updated_at) AS last_updated
            FROM mv_cards_mv
            GROUP BY program, module, module_order
            ORDER BY program, module_order;
            """
        )
        # Основные индексы для mv_module_stats
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_module_stats_program ON mv_module_stats (program);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_module_stats_module ON mv_module_stats (module);"
        )
        # Дополнительные индексы для mv_module_stats
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_module_stats_program_module ON mv_module_stats (program, module);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_module_stats_module_order ON mv_module_stats (module_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_module_stats_program_order ON mv_module_stats (program, module_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_module_stats_success ON mv_module_stats (avg_success_rate);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_module_stats_complaint ON mv_module_stats (avg_complaint_rate);"
        )
        
        # 4. Уровень уроков (lesson)
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_lesson_stats;")
        conn.exec_driver_sql(
            """
            CREATE MATERIALIZED VIEW mv_lesson_stats AS
            SELECT 
                program,
                module,
                module_order,
                lesson,
                lesson_order,
                COUNT(DISTINCT card_id) AS card_count,
                AVG(success_rate) AS avg_success_rate,
                AVG(complaint_rate) AS avg_complaint_rate,
                AVG(attempted_share) AS avg_attempted_share,
                AVG(discrimination_avg) AS avg_discrimination,
                SUM(total_attempts) AS total_attempts_sum,
                AVG(time_median) AS avg_time_median,
                SUM(time_median) AS total_time_median,
                COUNT(DISTINCT gz) AS gz_count,
                MAX(updated_at) AS last_updated
            FROM mv_cards_mv
            GROUP BY program, module, module_order, lesson, lesson_order
            ORDER BY program, module_order, lesson_order;
            """
        )
        # Основные индексы для mv_lesson_stats
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_stats_program_module ON mv_lesson_stats (program, module);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_stats_lesson ON mv_lesson_stats (lesson);"
        )
        # Дополнительные индексы для mv_lesson_stats
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_stats_program_module_lesson ON mv_lesson_stats (program, module, lesson);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_stats_module_order ON mv_lesson_stats (module_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_stats_lesson_order ON mv_lesson_stats (lesson_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_stats_orders ON mv_lesson_stats (module_order, lesson_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_stats_program_orders ON mv_lesson_stats (program, module_order, lesson_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_stats_success ON mv_lesson_stats (avg_success_rate);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_stats_complaint ON mv_lesson_stats (avg_complaint_rate);"
        )
        
        # 5. Уровень групп заданий (gz)
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_gz_stats;")
        conn.exec_driver_sql(
            """
            CREATE MATERIALIZED VIEW mv_gz_stats AS
            SELECT 
                program,
                module,
                module_order,
                lesson,
                lesson_order,
                gz,
                gz_id,
                COUNT(DISTINCT card_id) AS card_count,
                AVG(success_rate) AS avg_success_rate,
                AVG(complaint_rate) AS avg_complaint_rate,
                AVG(attempted_share) AS avg_attempted_share,
                AVG(discrimination_avg) AS avg_discrimination,
                SUM(total_attempts) AS total_attempts_sum,
                AVG(time_median) AS avg_time_median,
                SUM(time_median) AS total_time_median,
                COUNT(DISTINCT card_type) AS card_type_count,
                MAX(updated_at) AS last_updated
            FROM mv_cards_mv
            GROUP BY program, module, module_order, lesson, lesson_order, gz, gz_id
            ORDER BY program, module_order, lesson_order, gz;
            """
        )
        # Основные индексы для mv_gz_stats
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_stats_program_module_lesson ON mv_gz_stats (program, module, lesson);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_stats_gz ON mv_gz_stats (gz);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_stats_gz_id ON mv_gz_stats (gz_id);"
        )
        # Дополнительные индексы для mv_gz_stats
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_stats_program_module ON mv_gz_stats (program, module);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_stats_module_order ON mv_gz_stats (module_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_stats_lesson_order ON mv_gz_stats (lesson_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_stats_orders ON mv_gz_stats (module_order, lesson_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_stats_program_orders ON mv_gz_stats (program, module_order, lesson_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_stats_all_filter ON mv_gz_stats (program, module, lesson, gz);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_stats_success ON mv_gz_stats (avg_success_rate);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_stats_complaint ON mv_gz_stats (avg_complaint_rate);"
        )

    # Создаем кэш риска и обновляем материализованные представления с учетом риска
    # Сначала загружаем данные и рассчитываем риск
    raw_data = load_raw_data(engine)
    df = process_data(raw_data)
    
    # Создаем таблицу кэша риска
    df_cache = df[['card_id','risk']].copy()
    df_cache['updated_at'] = pd.Timestamp.utcnow()
    df_cache.to_sql('card_risk_cache', engine, if_exists='replace', index=False)

    # Обновляем представления с учетом риска
    with engine.begin() as conn:
        # Индекс для кэша риска
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_risk_cache_card_id ON card_risk_cache (card_id);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_risk_cache_risk ON card_risk_cache (risk);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_risk_cache_updated ON card_risk_cache (updated_at);"
        )
        
        # Материализованные представления с учетом риска
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_program_risk;")
        conn.exec_driver_sql(
            """
            CREATE MATERIALIZED VIEW mv_program_risk AS
            SELECT 
                p.program,
                p.card_count,
                p.avg_success_rate,
                p.avg_complaint_rate,
                AVG(r.risk) AS avg_risk,
                p.last_updated
            FROM mv_program_stats p
            JOIN mv_cards_mv c ON p.program = c.program
            JOIN card_risk_cache r ON c.card_id = r.card_id
            GROUP BY p.program, p.card_count, p.avg_success_rate, p.avg_complaint_rate, p.last_updated;
            """
        )
        # Индексы для mv_program_risk
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_program_risk_program ON mv_program_risk (program);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_program_risk_avg_risk ON mv_program_risk (avg_risk);"
        )
        
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_module_risk;")
        conn.exec_driver_sql(
            """
            CREATE MATERIALIZED VIEW mv_module_risk AS
            SELECT 
                m.program,
                m.module,
                m.module_order,
                m.card_count,
                m.avg_success_rate,
                m.avg_complaint_rate,
                AVG(r.risk) AS avg_risk,
                m.last_updated
            FROM mv_module_stats m
            JOIN mv_cards_mv c ON m.program = c.program AND m.module = c.module
            JOIN card_risk_cache r ON c.card_id = r.card_id
            GROUP BY m.program, m.module, m.module_order, m.card_count, m.avg_success_rate, m.avg_complaint_rate, m.last_updated
            ORDER BY m.program, m.module_order;
            """
        )
        # Индексы для mv_module_risk
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_module_risk_program ON mv_module_risk (program);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_module_risk_module ON mv_module_risk (module);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_module_risk_program_module ON mv_module_risk (program, module);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_module_risk_module_order ON mv_module_risk (module_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_module_risk_avg_risk ON mv_module_risk (avg_risk);"
        )
        
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_lesson_risk;")
        conn.exec_driver_sql(
            """
            CREATE MATERIALIZED VIEW mv_lesson_risk AS
            SELECT 
                l.program,
                l.module,
                l.module_order,
                l.lesson,
                l.lesson_order,
                l.card_count,
                l.avg_success_rate,
                l.avg_complaint_rate,
                AVG(r.risk) AS avg_risk,
                l.last_updated
            FROM mv_lesson_stats l
            JOIN mv_cards_mv c ON l.program = c.program AND l.module = c.module AND l.lesson = c.lesson
            JOIN card_risk_cache r ON c.card_id = r.card_id
            GROUP BY l.program, l.module, l.module_order, l.lesson, l.lesson_order, l.card_count, l.avg_success_rate, l.avg_complaint_rate, l.last_updated
            ORDER BY l.program, l.module_order, l.lesson_order;
            """
        )
        # Индексы для mv_lesson_risk
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_risk_program ON mv_lesson_risk (program);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_risk_module ON mv_lesson_risk (module);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_risk_lesson ON mv_lesson_risk (lesson);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_risk_program_module ON mv_lesson_risk (program, module);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_risk_program_module_lesson ON mv_lesson_risk (program, module, lesson);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_risk_orders ON mv_lesson_risk (module_order, lesson_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_lesson_risk_avg_risk ON mv_lesson_risk (avg_risk);"
        )
        
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS mv_gz_risk;")
        conn.exec_driver_sql(
            """
            CREATE MATERIALIZED VIEW mv_gz_risk AS
            SELECT 
                g.program,
                g.module,
                g.module_order,
                g.lesson,
                g.lesson_order,
                g.gz,
                g.gz_id,
                g.card_count,
                g.avg_success_rate,
                g.avg_complaint_rate,
                AVG(r.risk) AS avg_risk,
                g.last_updated
            FROM mv_gz_stats g
            JOIN mv_cards_mv c ON g.program = c.program AND g.module = c.module AND g.lesson = c.lesson AND g.gz = c.gz
            JOIN card_risk_cache r ON c.card_id = r.card_id
            GROUP BY g.program, g.module, g.module_order, g.lesson, g.lesson_order, g.gz, g.gz_id, g.card_count, g.avg_success_rate, g.avg_complaint_rate, g.last_updated
            ORDER BY g.program, g.module_order, g.lesson_order;
            """
        )
        # Индексы для mv_gz_risk
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_risk_program ON mv_gz_risk (program);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_risk_module ON mv_gz_risk (module);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_risk_lesson ON mv_gz_risk (lesson);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_risk_gz ON mv_gz_risk (gz);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_risk_gz_id ON mv_gz_risk (gz_id);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_risk_program_module ON mv_gz_risk (program, module);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_risk_program_module_lesson ON mv_gz_risk (program, module, lesson);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_risk_all_filter ON mv_gz_risk (program, module, lesson, gz);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_gz_risk_avg_risk ON mv_gz_risk (avg_risk);"
        )

    # Старая часть: плоская таблица cards_flat и топ-10 карточек
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS cards_flat;")
        conn.exec_driver_sql("CREATE TABLE cards_flat AS SELECT * FROM mv_cards_mv;")
        # Индексы для cards_flat
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_flat_filters ON cards_flat (program, module, lesson, gz);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_flat_card_id ON cards_flat (card_id);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_flat_program ON cards_flat (program);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_flat_module ON cards_flat (module);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_flat_lesson ON cards_flat (lesson);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_flat_gz ON cards_flat (gz);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_flat_orders ON cards_flat (module_order, lesson_order);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_flat_status ON cards_flat (status);"
        )

    # Топ-10 карточек по каждой группе с учетом риска
    df_top = (
        df[['gz','card_id','risk']]
        .sort_values(['gz','risk'], ascending=[True,False])
        .groupby('gz')
        .head(10)
        .assign(rn=lambda d: d.groupby('gz').cumcount()+1)
    )
    df_top.to_sql('top10_by_group', engine, if_exists='replace', index=False)
    with engine.begin() as conn:
        # Индексы для top10_by_group
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_top10_gz_rn ON top10_by_group (gz, rn);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_top10_card_id ON top10_by_group (card_id);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_top10_risk ON top10_by_group (risk);"
        )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_top10_gz ON top10_by_group (gz);"
        )

if __name__ == '__main__':
    optimize_db()
