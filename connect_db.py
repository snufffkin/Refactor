from sqlalchemy import create_engine
from db_config import get_cloud_dsn

def get_engine():
    return create_engine(get_cloud_dsn(), future=True)
