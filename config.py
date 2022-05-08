from pydantic import BaseSettings


class Environment(BaseSettings):
    db_host: str
    db_port: str
    db_username: str
    db_password: str
    db_name: str


env_vars = Environment()
