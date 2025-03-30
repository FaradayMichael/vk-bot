import json
import logging
import os

from pydantic import (
    BaseModel
)

CONFIG_ENV_KEY = 'SRVC_CONFIG'

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


class VkConfig(BaseModel):
    vk_token: str
    user_token: str
    main_user_id: int
    main_group_id: int
    timeout: int = 60
    main_group_alias: str = ""


class KafkaConfig(BaseModel):
    bootstrap_servers: str
    topics: list[str]
    disable_logger: bool = True


class DiscordConfig(BaseModel):
    token: str
    main_user_id: int = 358590015531646977


class DumperConfig(BaseModel):
    cron: str
    user: str
    db: str
    vk_peer_id: int | None = None


class GigachatConfig(BaseModel):
    client_secret: str
    token: str
    scope: str


class SftpConfig(BaseModel):
    username: str
    password: str
    host: str
    port: int


class Config(BaseModel):
    debug: bool = False
    salt: str
    db: PostgresqlConfig
    redis: RedisConfig
    smtp: SmtpConfig
    folders: FoldersConfig
    static_url: str = '/media'
    vk: VkConfig
    kafka: KafkaConfig
    discord: DiscordConfig
    dumper: DumperConfig
    gigachat: GigachatConfig
    sftp: SftpConfig
    amqp: str


def read_config(path: str) -> Config:
    if not os.path.exists(path):
        raise RuntimeError(f'Configuration file {path} not found')
    with open(path, 'r') as fd:
        config_json = json.load(fd)

    config = Config.model_validate(config_json)

    return config


def from_env() -> Config:
    try:
        config_path = os.environ[CONFIG_ENV_KEY]
        return read_config(config_path)
    except Exception as e:
        raise RuntimeError(f'Configuration file path not provided at environment [{CONFIG_ENV_KEY}]')


def static_files_folder(conf: Config) -> str:
    return conf.folders.static


def template_files_folder(conf: Config) -> str:
    return conf.folders.templates
