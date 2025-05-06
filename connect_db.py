import psycopg2

conn = psycopg2.connect(
    host="rc1b-fkbqfy1dg88d0134.mdb.yandexcloud.net",
    port=6432,
    sslmode="verify-full",
    dbname="course_quality",
    sslrootcert="/Users/romannikitin/.postgresql/root.crt",
    user="romannikitin",
    password="changeme123",
    target_session_attrs="read-write"
)

q = conn.cursor()
q.execute('SELECT version()')

print(q.fetchone())

conn.close()
