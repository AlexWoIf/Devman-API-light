from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic.types import constr


class DvmnSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_prefix='dvmn_',
        extra='allow',
        frozen=True,
    )
    token: constr(pattern=r'[0-9a-fA-F]{40}')


class TgSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_prefix='tg_',
        extra='allow',
        frozen=True,
        regex_engine='python-re',
    )
    bot_token: constr(pattern=r'^[0-9]{8,10}:[a-zA-Z0-9_-]{35}$')
    chat_id: constr(pattern=r'^(-)?[0-9]{1,10}$')


class LogSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_prefix='log_',
        extra='allow',
    )
    level: str = 'INFO'
