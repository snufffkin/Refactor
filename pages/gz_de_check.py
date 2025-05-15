import streamlit as st
import pandas as pd
from sqlalchemy import text
from connect_db import get_engine

st.title('Проверка сочетаемости ГЗ и ДЕ')

engine = get_engine()

# 1. Получаем список программ
programs = pd.read_sql('SELECT DISTINCT program FROM cards_flat ORDER BY program', engine)['program'].tolist()
selected_programs = st.multiselect('Выберите программу', programs, default=programs[:1])

if not selected_programs:
    st.info('Выберите хотя бы одну программу для проверки.')
    st.stop()

# 2. Загружаем ГЗ выбранных программ
query_gz = f'''
SELECT DISTINCT cf.gz_id, cf.gz, cf.program
FROM cards_flat cf
WHERE cf.program IN ({','.join(['%s']*len(selected_programs))})
ORDER BY cf.program, cf.gz
'''
gz_df = pd.read_sql(query_gz, engine, params=tuple(selected_programs))

# 2b. Загружаем mapping gz_id -> module, lesson
module_lesson_df = pd.read_sql('SELECT DISTINCT gz_id, module, lesson FROM cards_flat', engine)
module_lesson_df = module_lesson_df.drop_duplicates(subset=['gz_id'])
gz2modles = module_lesson_df.set_index('gz_id')[['module', 'lesson']].to_dict(orient='index')

# 3. Загружаем топ-10 ДЕ для каждого ГЗ (теперь из таблицы)
gz_ids = gz_df['gz_id'].tolist()

gz_de_df = pd.read_sql(
    'SELECT * FROM gz_de_top5_copy WHERE gz_id = ANY(%(gz_ids)s)',
    engine,
    params={'gz_ids': list(gz_ids)}
)

# Фильтруем только те ГЗ, где approved == False
gz_de_df = gz_de_df[(gz_de_df['approved'] == False) | (gz_de_df['approved'].isnull())]
gz_ids_to_check = set(gz_de_df['gz_id'])
gz_df = gz_df[gz_df['gz_id'].isin(gz_ids_to_check)]

# 4. Загружаем справочник ДЕ с темой ТК и родителем
unique_de_df = pd.read_sql('SELECT "ID ДЕ", "Наименование ДЕ", "Наименование темы ТК", "Наименование ДЕ-родителя" FROM unique_de', engine)
de_info = unique_de_df.set_index('ID ДЕ').to_dict(orient='index')

# 5. Формируем интерфейс для ручной проверки
selected_de = {}
for _, row in gz_df.iterrows():
    gz_id = row['gz_id']
    gz_name = row['gz']
    program = row['program']
    module = gz2modles.get(gz_id, {}).get('module', '')
    lesson = gz2modles.get(gz_id, {}).get('lesson', '')
    public_url = f'https://education.yandex.ru/classroom/public-lesson/{gz_id}/run/'
    st.markdown(f'---\n### ГЗ: {gz_name} (ID: {gz_id}, программа: {program}) [🔗 Открыть ГЗ]({public_url})')
    if module or lesson:
        st.markdown(f'<span style="color: #aaa;">Модуль: {module} | Урок: {lesson}</span>', unsafe_allow_html=True)
    top10_row = gz_de_df[gz_de_df['gz_id'] == gz_id]
    de_ids_to_show = list(top10_row.iloc[0]['top5_de_ids']) if not top10_row.empty else []
    # Чекбокс "Выбрать все/Снять выделение"
    all_checked_default = False
    # --- session_state для выбранных ДЕ ---
    checked_de_key = f"checked_de_{gz_id}"
    if checked_de_key not in st.session_state:
        st.session_state[checked_de_key] = de_ids_to_show.copy()
    checked_de = st.session_state[checked_de_key]
    all_checked = st.checkbox('Выбрать все/Снять выделение', value=all_checked_default, key=f'select_all_{gz_id}')
    checked_de = list(dict.fromkeys(checked_de))  # удаляем дубликаты, сохраняем порядок
    for de_id in checked_de:
        info = de_info.get(de_id, {})
        de_name = info.get('Наименование ДЕ', 'Не найдено')
        topic = info.get('Наименование темы ТК')
        parent = info.get('Наименование ДЕ-родителя')
        label = f"{de_id} — {de_name}"
        if topic:
            label += f" | Тема ТК: {topic}"
        if parent:
            label += f" | Родитель: {parent}"
        checked = st.checkbox(label, value=de_id in checked_de, key=f"chk_{gz_id}_{de_id}")
        if checked and de_id not in checked_de:
            checked_de.append(de_id)
        if not checked and de_id in checked_de:
            checked_de.remove(de_id)
    # --- ручное добавление ДЕ ---
    st.markdown("**Добавить ДЕ вручную:**")
    de_options = [
        f'{row["ID ДЕ"]} — {row["Наименование ДЕ"]} | Тема ТК: {row["Наименование темы ТК"] or ""} | Родитель: {row["Наименование ДЕ-родителя"] or ""}'
        for _, row in unique_de_df.iterrows()
    ]
    selected_de_to_add = st.multiselect("Выберите ДЕ для добавления", de_options, key=f"add_de_select_{gz_id}")
    if st.button("Добавить выбранные ДЕ", key=f"add_de_btn_{gz_id}"):
        for de_str in selected_de_to_add:
            de_id_to_add = int(de_str.split('—')[0].strip())
            if de_id_to_add not in checked_de:
                checked_de.append(de_id_to_add)
        st.session_state[checked_de_key] = checked_de
        # Сохраняем изменения в БД сразу
        with engine.begin() as conn:
            conn.execute(
                text('UPDATE gz_de_top5_copy SET top5_de_ids=:de_ids WHERE gz_id=:gz_id'),
                {'gz_id': gz_id, 'de_ids': [int(x) for x in checked_de]}
            )
        st.success("Выбранные ДЕ добавлены в список для этой ГЗ и сохранены!")
    selected_de[gz_id] = checked_de
    # Чекбокс "Проверка завершена"
    approved = st.checkbox('Проверка завершена', value=False, key=f'approved_{gz_id}')
    if approved:
        with engine.begin() as conn:
            conn.execute(text('UPDATE gz_de_top5_copy SET approved=TRUE WHERE gz_id=:gz_id'), {'gz_id': gz_id})
        st.success('Проверка для этой ГЗ завершена!')

# Кнопка сохранить теперь в сайдбаре
if selected_programs:
    placeholders = ','.join(['%s']*len(selected_programs))
    query_total = f'SELECT COUNT(DISTINCT t.gz_id) FROM gz_de_top5_copy t JOIN cards_flat cf ON t.gz_id=cf.gz_id WHERE cf.program IN ({placeholders})'
    total_gz = int(pd.read_sql(query_total, engine, params=tuple(selected_programs)).iloc[0,0])
    query_checked = f'SELECT COUNT(DISTINCT t.gz_id) FROM gz_de_top5_copy t JOIN cards_flat cf ON t.gz_id=cf.gz_id WHERE t.approved=TRUE AND cf.program IN ({placeholders})'
    num_checked = int(pd.read_sql(query_checked, engine, params=tuple(selected_programs)).iloc[0,0])
else:
    total_gz = 0
    num_checked = 0
st.sidebar.markdown(f'**Проверено ГЗ:** {num_checked} из {total_gz}')
if st.sidebar.button('💾 Сохранить соответствия'):
    with engine.begin() as conn:
        for gz_id, de_ids in selected_de.items():
            # Обновляем только если чекбокс 'Проверка завершена' отмечен
            if st.session_state.get(f'approved_{gz_id}', False):
                conn.execute(
                    text('UPDATE gz_de_top5_copy SET top5_de_ids=:de_ids WHERE gz_id=:gz_id'),
                    {'gz_id': gz_id, 'de_ids': [int(x) for x in de_ids]}
                )
    st.sidebar.success('Соответствия успешно сохранены!') 