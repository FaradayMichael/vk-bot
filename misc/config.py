import datetime
import json
import logging
import os
from pydantic import (
    BaseModel
)

logger = logging.getLogger(__name__)


class PostgresqlConfig(BaseModel):
    dsn: str


class RedisConfig(BaseModel):
    dsn: str
    minsize: int = 1
    maxsize: int = 10


class TransportSmtpConfig(BaseModel):
    hostname: str = 'mailhog'
    port: int = 1025


class SmtpConfig(BaseModel):
    transport: TransportSmtpConfig
    sender: str = 'noreply@template.ru'


class FoldersConfig(BaseModel):
    static: str
    templates: str


class CheckOrdersServiceConfig(BaseModel):
    check_period_seconds: int = 60
    payment_due_seconds: int = 300


class ParserServiceConfig(BaseModel):
    start_time: datetime.time = datetime.time(hour=3)
    watchcharts_api_key: str = ""


class Config(BaseModel):
    debug: bool = False
    salt: str
    db: PostgresqlConfig
    redis: RedisConfig
    smtp: SmtpConfig
    folders: FoldersConfig
    static_url: str = '/media'


def read_config(path: str) -> Config:
    if not os.path.exists(path):
        raise RuntimeError(f'Configuration file {path} not found')
    with open(path, 'r') as fd:
        config_json = json.load(fd)

    config = Config.model_validate(config_json)
    config = from_env(config)

    return config


def from_env(config: Config) -> Config:
    return config


# def static_files_folder(conf: Config) -> str:
#     return conf.folders.static


def static_files_folder(conf: Config) -> str:
    return conf.folders.static


def template_files_folder(conf: Config) -> str:
    return conf.folders.templates
