#!/usr/bin/env python3
"""
Скрипт для анализа отзывов учителей с помощью OpenAI API.

Этот скрипт:
1. Подключается к таблице teachers_reviews в базе данных
2. Получает данные отзывов учителей об уроках
3. Отправляет их в OpenAI API для анализа
4. Сохраняет результат в поле ai_summarization

Использование:
    python analyze_teacher_reviews.py          # Анализировать только новые отзывы
    python analyze_teacher_reviews.py -force   # Перезаписать все отзывы
"""

import os
import json
import logging
import argparse
from typing import Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from openai import OpenAI
from db_config import get_cloud_dsn

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Промпт для анализа отзывов
ANALYSIS_PROMPT = """Ты - опытный методист-аналитик образовательных программ. Твоя задача - проанализировать отзывы учителей об уроке и создать структурированную суммаризацию.

ВХОДНЫЕ ДАННЫЕ:
- program_name: {program_name}
- module_name: {module_name}
- lesson_name: {lesson_name}
- presentation_rate: {presentation_rate}
- presentation_like: {presentation_like}
- presentation_dislike: {presentation_dislike}
- workbook_rate: {workbook_rate}
- workbook_like: {workbook_like}
- workbook_dislike: {workbook_dislike}
- addmaterial_stat: {addmaterial_stat}
- addmaterial_rate: {addmaterial_rate}
- addmaterial_like: {addmaterial_like}
- addmaterial_dislike: {addmaterial_dislike}
- overall_stat: {overall_stat}
- interest_stat: {interest_stat}
- interest_dislike: {interest_dislike}
- interest_like: {interest_like}
- complexity_stat: {complexity_stat}
- complexity_to_simplify: {complexity_to_simplify}
- complexity_to_complicate: {complexity_to_complicate}

СРЕДНИЕ ЗНАЧЕНИЯ ПО ПРОГРАММЕ:
- presentation_rate: {avg_program_presentation_rate}
- workbook_rate: {avg_program_workbook_rate}
- addmaterial_stat: {avg_program_addmaterial_stat}
- addmaterial_rate: {avg_program_addmaterial_rate}
- overall_stat: {avg_program_overall_stat}
- interest_stat: {avg_program_interest_stat}
- complexity_stat: {avg_program_complexity_stat}

СРЕДНИЕ ЗНАЧЕНИЯ ПО МОДУЛЮ:
- presentation_rate: {avg_module_presentation_rate}
- workbook_rate: {avg_module_workbook_rate}
- addmaterial_stat: {avg_module_addmaterial_stat}
- addmaterial_rate: {avg_module_addmaterial_rate}
- overall_stat: {avg_module_overall_stat}
- interest_stat: {avg_module_interest_stat}
- complexity_stat: {avg_module_complexity_stat}

ИНСТРУКЦИИ:
1. Проанализируй все отзывы, выделяя ключевые темы и паттерны. Используй ТОЛЬКО данные из блока «ВХОДНЫЕ ДАННЫЕ» — никаких внешних домыслов. 
2. Обрати особое внимание на конкретные рекомендации учителей
3. Выяви проблемные зоны и успешные элементы урока
4. Сформулируй практические рекомендации для методистов
5. Учитывай количественные оценки при формировании выводов
6. Сравнивай показатели урока со средними по программе и модулю
7. В каждом списке упорядочивай элементы от 🔴 к 🟢. 
8. Перед выводом проверь, что JSON валиден (без комментариев, кавычки двойные)

ВАЖНО - СИСТЕМА ОБОЗНАЧЕНИЯ СИЛЫ УТВЕРЖДЕНИЙ:
Для КАЖДОГО утверждения в списках добавь в начало эмодзи, обозначающий силу/частоту упоминания:
- 🟢 - единичное упоминание (1-2 учителя)
- 🟡 - умеренно частое (3-4 учителя)
- 🟠 - частое упоминание (5-6 учителей)
- 🔴 - очень частое (7+ учителей)

Определяй силу на основе:
- Количества похожих отзывов
- Частоты упоминания темы
- Интенсивности формулировок

ВЫХОДНОЙ ФОРМАТ (строгий JSON):
{{
  "lesson_info": {{
    "program": "название программы",
    "module": "название модуля", 
    "lesson": "название урока",
    "overall_rating": число,
    "teachers_count": количество уникальных отзывов
  }},
  
  "quantitative_metrics": {{
    "presentation_rating": число,
    "workbook_rating": число,
    "additional_materials_rating": число,
    "interest_rating": число,
    "complexity_rating": число,
    "additional_materials_usage": процент_использования
  }},
  
  "comparison_with_averages": {{
    "vs_program": {{
      "presentation_diff": число_со_знаком,
      "workbook_diff": число_со_знаком,
      "overall_diff": число_со_знаком,
      "interest_diff": число_со_знаком,
      "summary": "краткое сравнение с программой"
    }},
    "vs_module": {{
      "presentation_diff": число_со_знаком,
      "workbook_diff": число_со_знаком,
      "overall_diff": число_со_знаком,
      "interest_diff": число_со_знаком,
      "summary": "краткое сравнение с модулем"
    }}
  }},
  
  "key_strengths": {{
    "presentation": ["🟢/🟡/🟠/🔴 список основных достоинств презентации"],
    "workbook": ["🟢/🟡/🟠/🔴 список основных достоинств рабочей тетради"],
    "additional_materials": ["🟢/🟡/🟠/🔴 список достоинств доп. материалов"],
    "pedagogical_value": ["🟢/🟡/🟠/🔴 что особенно ценно с педагогической точки зрения"]
  }},
  
  "identified_issues": {{
    "presentation": ["🟢/🟡/🟠/🔴 конкретные проблемы презентации"],
    "workbook": ["🟢/🟡/🟠/🔴 конкретные проблемы рабочей тетради"],
    "additional_materials": ["🟢/🟡/🟠/🔴 проблемы доп. материалов"],
    "complexity_balance": ["🟢/🟡/🟠/🔴 проблемы баланса сложности"]
  }},
  
  "teacher_recommendations": {{
    "content_improvements": ["🟢/🟡/🟠/🔴 конкретные предложения по улучшению контента"],
    "methodology_suggestions": ["🟢/🟡/🟠/🔴 методические рекомендации"],
    "complexity_adjustments": ["🟢/🟡/🟠/🔴 рекомендации по корректировке сложности"],
    "engagement_ideas": ["🟢/🟡/🟠/🔴 идеи для повышения вовлеченности"]
  }},
  
  "methodist_action_items": {{
    "immediate_fixes": ["🟢/🟡/🟠/🔴 что нужно исправить срочно"],
    "content_additions": ["🟢/🟡/🟠/🔴 какой контент добавить"],
    "content_removals": ["🟢/🟡/🟠/🔴 что можно убрать"],
    "structural_changes": ["🟢/🟡/🟠/🔴 изменения в структуре урока"],
    "assessment_recommendations": ["🟢/🟡/🟠/🔴 рекомендации по оцениванию"]
  }},
  
  "patterns_and_insights": {{
    "common_difficulties": ["🟢/🟡/🟠/🔴 типичные сложности учеников"],
    "successful_elements": ["🟢/🟡/🟠/🔴 что работает особенно хорошо"],
    "teacher_consensus": ["🟢/🟡/🟠/🔴 в чем сходятся мнения учителей"],
    "controversial_points": ["🟢/🟡/🟠/🔴 спорные моменты"]
  }},
  
  "summary": {{
    "main_conclusion": "общий вывод об уроке с учетом сравнения с программой и модулем",
    "priority_improvements": ["3-5 приоритетных улучшений с учетом силы утверждений"],
    "expected_impact": "ожидаемый эффект от внедрения рекомендаций",
    "relative_performance": "как урок выглядит на фоне программы и модуля"
  }}
}}

ВАЖНО:
- Группируй похожие отзывы, избегая повторений
- Выделяй конкретные примеры и детали из отзывов
- Формулируй четкие, actionable рекомендации
- Учитывай контекст (класс, программа, уровень сложности)
- Если отзывы противоречивы, отмечай это в patterns_and_insights
- ОБЯЗАТЕЛЬНО добавляй эмодзи силы к КАЖДОМУ пункту в списках
- Используй сравнение со средними значениями для усиления выводов"""


class TeacherReviewsAnalyzer:
    """Класс для анализа отзывов учителей с помощью OpenAI API."""
    
    def __init__(self, force_reanalyze: bool = False):
        """
        Инициализация анализатора.
        
        Args:
            force_reanalyze: Если True, перезаписывает существующие анализы
        """
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY не найден в переменных окружения")
        
        self.client = OpenAI(api_key=self.openai_api_key)
        self.dsn = get_cloud_dsn()
        self.force_reanalyze = force_reanalyze
        
    def ensure_ai_summarization_column(self) -> None:
        """Проверяет наличие и создает колонку ai_summarization если её нет."""
        conn = None
        try:
            conn = psycopg2.connect(self.dsn)
            with conn.cursor() as cur:
                # Проверяем существование колонки
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'teacher_reviews' 
                    AND column_name = 'ai_summarization'
                """)
                
                if not cur.fetchone():
                    logger.info("Добавляю колонку ai_summarization в таблицу teacher_reviews")
                    cur.execute("""
                        ALTER TABLE teacher_reviews 
                        ADD COLUMN IF NOT EXISTS ai_summarization JSONB
                    """)
                    conn.commit()
                    logger.info("Колонка ai_summarization успешно добавлена")
                else:
                    logger.info("Колонка ai_summarization уже существует")
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке/создании колонки: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def get_average_metrics(self, program_id: int, module_id: int) -> Tuple[Dict, Dict]:
        """Получает средние значения метрик по программе и модулю."""
        conn = None
        try:
            conn = psycopg2.connect(self.dsn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Средние по программе
                cur.execute("""
                    SELECT 
                        AVG(presentation_rate) as avg_presentation_rate,
                        AVG(workbook_rate) as avg_workbook_rate,
                        AVG(addmaterial_stat) as avg_addmaterial_stat,
                        AVG(addmaterial_rate) as avg_addmaterial_rate,
                        AVG(overall_stat) as avg_overall_stat,
                        AVG(interest_stat) as avg_interest_stat,
                        AVG(complexity_stat) as avg_complexity_stat
                    FROM teacher_reviews
                    WHERE program_id = %s
                    AND presentation_rate IS NOT NULL
                """, (program_id,))
                
                program_averages = cur.fetchone() or {}
                
                # Средние по модулю
                cur.execute("""
                    SELECT 
                        AVG(presentation_rate) as avg_presentation_rate,
                        AVG(workbook_rate) as avg_workbook_rate,
                        AVG(addmaterial_stat) as avg_addmaterial_stat,
                        AVG(addmaterial_rate) as avg_addmaterial_rate,
                        AVG(overall_stat) as avg_overall_stat,
                        AVG(interest_stat) as avg_interest_stat,
                        AVG(complexity_stat) as avg_complexity_stat
                    FROM teacher_reviews
                    WHERE module_id = %s
                    AND presentation_rate IS NOT NULL
                """, (module_id,))
                
                module_averages = cur.fetchone() or {}
                
                # Преобразуем None в 0
                for avg_dict in [program_averages, module_averages]:
                    for key in avg_dict:
                        if avg_dict[key] is None:
                            avg_dict[key] = 0
                
                return dict(program_averages), dict(module_averages)
                
        except Exception as e:
            logger.error(f"Ошибка при получении средних значений: {e}")
            # Возвращаем пустые словари в случае ошибки
            return {}, {}
        finally:
            if conn:
                conn.close()
    
    def get_reviews_to_analyze(self) -> List[Dict]:
        """Получает отзывы для анализа."""
        conn = None
        try:
            conn = psycopg2.connect(self.dsn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Формируем условие WHERE в зависимости от флага force
                where_clause = "WHERE lesson_id IS NOT NULL"
                if not self.force_reanalyze:
                    where_clause += " AND ai_summarization IS NULL"
                
                query = f"""
                    SELECT 
                        lesson_id,
                        program_id,
                        module_id,
                        program_name,
                        module_name,
                        lesson_name,
                        presentation_rate,
                        presentation_like,
                        presentation_dislike,
                        workbook_rate,
                        workbook_like,
                        workbook_dislike,
                        addmaterial_stat,
                        addmaterial_rate,
                        addmaterial_like,
                        addmaterial_dislike,
                        overall_stat,
                        interest_stat,
                        interest_dislike,
                        interest_like,
                        complexity_stat,
                        complexity_to_simplify,
                        complexity_to_complicate
                    FROM teacher_reviews
                    {where_clause}
                    ORDER BY program_name, module_name, lesson_name
                """
                
                cur.execute(query)
                
                reviews = cur.fetchall()
                
                if self.force_reanalyze:
                    logger.info(f"Найдено {len(reviews)} отзывов для анализа (режим перезаписи)")
                else:
                    logger.info(f"Найдено {len(reviews)} новых отзывов для анализа")
                    
                return reviews
                
        except Exception as e:
            logger.error(f"Ошибка при получении отзывов: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def count_teachers_from_reviews(self, review_data: Dict) -> int:
        """Подсчитывает количество уникальных отзывов учителей."""
        count = 0
        
        # Проверяем все поля с отзывами
        review_fields = [
            'presentation_like', 'presentation_dislike',
            'workbook_like', 'workbook_dislike',
            'addmaterial_like', 'addmaterial_dislike',
            'interest_like', 'interest_dislike',
            'complexity_to_simplify', 'complexity_to_complicate'
        ]
        
        for field in review_fields:
            if review_data.get(field):
                # Считаем количество отзывов по разделителю \n
                reviews = str(review_data[field]).strip().split('\n')
                # Фильтруем пустые строки
                reviews = [r.strip() for r in reviews if r.strip()]
                count = max(count, len(reviews))
        
        return count
    
    def analyze_review(self, review: Dict) -> Optional[Dict]:
        """Анализирует один отзыв с помощью OpenAI API."""
        try:
            # Получаем средние значения по программе и модулю
            program_averages, module_averages = self.get_average_metrics(
                review.get('program_id'),
                review.get('module_id')
            )
            
            # Подготавливаем данные для промпта
            prompt_data = {
                'program_name': review.get('program_name', 'Не указано'),
                'module_name': review.get('module_name', 'Не указано'),
                'lesson_name': review.get('lesson_name', 'Не указано'),
                'presentation_rate': review.get('presentation_rate', 'Нет данных'),
                'presentation_like': review.get('presentation_like', 'Нет отзывов'),
                'presentation_dislike': review.get('presentation_dislike', 'Нет отзывов'),
                'workbook_rate': review.get('workbook_rate', 'Нет данных'),
                'workbook_like': review.get('workbook_like', 'Нет отзывов'),
                'workbook_dislike': review.get('workbook_dislike', 'Нет отзывов'),
                'addmaterial_stat': review.get('addmaterial_stat', 'Нет данных'),
                'addmaterial_rate': review.get('addmaterial_rate', 'Нет данных'),
                'addmaterial_like': review.get('addmaterial_like', 'Нет отзывов'),
                'addmaterial_dislike': review.get('addmaterial_dislike', 'Нет отзывов'),
                'overall_stat': review.get('overall_stat', 'Нет данных'),
                'interest_stat': review.get('interest_stat', 'Нет данных'),
                'interest_dislike': review.get('interest_dislike', 'Нет отзывов'),
                'interest_like': review.get('interest_like', 'Нет отзывов'),
                'complexity_stat': review.get('complexity_stat', 'Нет данных'),
                'complexity_to_simplify': review.get('complexity_to_simplify', 'Нет отзывов'),
                'complexity_to_complicate': review.get('complexity_to_complicate', 'Нет отзывов'),
                # Средние по программе
                'avg_program_presentation_rate': round(program_averages.get('avg_presentation_rate', 0), 2),
                'avg_program_workbook_rate': round(program_averages.get('avg_workbook_rate', 0), 2),
                'avg_program_addmaterial_stat': round(program_averages.get('avg_addmaterial_stat', 0), 2),
                'avg_program_addmaterial_rate': round(program_averages.get('avg_addmaterial_rate', 0), 2),
                'avg_program_overall_stat': round(program_averages.get('avg_overall_stat', 0), 2),
                'avg_program_interest_stat': round(program_averages.get('avg_interest_stat', 0), 2),
                'avg_program_complexity_stat': round(program_averages.get('avg_complexity_stat', 0), 2),
                # Средние по модулю
                'avg_module_presentation_rate': round(module_averages.get('avg_presentation_rate', 0), 2),
                'avg_module_workbook_rate': round(module_averages.get('avg_workbook_rate', 0), 2),
                'avg_module_addmaterial_stat': round(module_averages.get('avg_addmaterial_stat', 0), 2),
                'avg_module_addmaterial_rate': round(module_averages.get('avg_addmaterial_rate', 0), 2),
                'avg_module_overall_stat': round(module_averages.get('avg_overall_stat', 0), 2),
                'avg_module_interest_stat': round(module_averages.get('avg_interest_stat', 0), 2),
                'avg_module_complexity_stat': round(module_averages.get('avg_complexity_stat', 0), 2)
            }
            
            # Формируем промпт
            prompt = ANALYSIS_PROMPT.format(**prompt_data)
            
            logger.info(f"Анализирую отзыв для урока: {review['lesson_name']}")
            
            # Отправляем запрос в OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты - опытный методист-аналитик. Твоя задача - анализировать отзывы учителей и создавать структурированные отчеты в формате JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=4000
            )
            
            # Парсим ответ
            result = json.loads(response.choices[0].message.content)
            
            # Добавляем количество учителей
            if 'lesson_info' in result:
                result['lesson_info']['teachers_count'] = self.count_teachers_from_reviews(review)
            
            logger.info(f"Анализ завершен для урока: {review['lesson_name']}")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при анализе отзыва для урока '{review.get('lesson_name', 'Unknown')}': {type(e).__name__}: {str(e)}")
            import traceback
            logger.debug(f"Полный traceback: {traceback.format_exc()}")
            return None
    
    def save_analysis(self, lesson_id: int, analysis: Dict) -> None:
        """Сохраняет результат анализа в базу данных."""
        conn = None
        try:
            conn = psycopg2.connect(self.dsn)
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE teacher_reviews
                    SET ai_summarization = %s
                    WHERE lesson_id = %s
                """, (json.dumps(analysis, ensure_ascii=False), lesson_id))
                
                conn.commit()
                logger.info(f"Анализ сохранен для lesson_id: {lesson_id}")
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении анализа: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def run(self) -> None:
        """Запускает процесс анализа отзывов."""
        try:
            # Проверяем/создаем колонку для хранения результатов
            self.ensure_ai_summarization_column()
            
            # Получаем отзывы для анализа
            reviews = self.get_reviews_to_analyze()
            
            if not reviews:
                if self.force_reanalyze:
                    logger.info("Нет отзывов для перезаписи")
                else:
                    logger.info("Нет новых отзывов для анализа")
                return
            
            # Анализируем каждый отзыв
            success_count = 0
            error_count = 0
            
            for i, review in enumerate(reviews, 1):
                logger.info(f"Обработка {i}/{len(reviews)}: {review['lesson_name']}")
                
                analysis = self.analyze_review(review)
                
                if analysis:
                    self.save_analysis(review['lesson_id'], analysis)
                    success_count += 1
                else:
                    error_count += 1
                    logger.warning(f"Не удалось проанализировать отзыв для lesson_id: {review['lesson_id']}")
            
            logger.info(f"Анализ завершен. Успешно: {success_count}, Ошибок: {error_count}")
            
        except Exception as e:
            logger.error(f"Критическая ошибка при выполнении анализа: {e}")
            raise


def main():
    """Главная функция."""
    # Создаем парсер аргументов командной строки
    parser = argparse.ArgumentParser(
        description='Анализ отзывов учителей с помощью OpenAI API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python analyze_teacher_reviews.py          # Анализировать только новые отзывы
  python analyze_teacher_reviews.py -force   # Перезаписать все отзывы
        """
    )
    
    parser.add_argument(
        '-force',
        '--force',
        action='store_true',
        help='Перезаписать существующие анализы (по умолчанию анализируются только новые отзывы)'
    )
    
    args = parser.parse_args()
    
    try:
        analyzer = TeacherReviewsAnalyzer(force_reanalyze=args.force)
        
        if args.force:
            logger.info("Запуск в режиме перезаписи всех отзывов")
        else:
            logger.info("Запуск в режиме анализа только новых отзывов")
            
        analyzer.run()
    except Exception as e:
        logger.error(f"Ошибка при запуске анализатора: {e}")
        raise


if __name__ == "__main__":
    main() 