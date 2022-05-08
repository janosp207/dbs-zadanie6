from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import env_vars

SQL_ALCHEMY_DATABASE_URL = f'postgresql://{env_vars.db_username}:{env_vars.db_password}@' \
                           f'{env_vars.db_host}:{env_vars.db_port}/{env_vars.db_name}'

engine = create_engine(SQL_ALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def connect_to_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()

