from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    supabase_url: str = Field(min_length=20, env="SUPABASE_URL")
    supabase_api_key: str = Field(min_length=10, env="SUPABASE_API_KEY")

    @field_validator("supabase_url")
    @classmethod
    def check_supabase_url(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("Supabase URL must start with https://")
        if not value.endswith(".supabase.co"):
            raise ValueError("Supabase URL must end with .supabase.co")
        return value

    @field_validator("supabase_api_key")
    @classmethod
    def check_supabase_api_key(cls, value: str) -> str:
        if not value.startswith("sb_secret_"):
            raise ValueError("Supabase API key must start with sb_secret_")
        return value


settings = Settings()