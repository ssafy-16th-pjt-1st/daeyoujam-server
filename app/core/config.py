from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Daeyoujam API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    service_name: str = "daeyoujam-api"
    database_url: str = "sqlite:///./data/localhub.db"
    openai_api_key: str = ""
    openai_model: str = ""
    openai_base_url: str = ""
    vector_store_path: str = "./data/chroma"
    vector_collection_name: str = "daeyoujam_places"
    vector_embedding_dim: int = 384
    frontend_origin: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",")]
        return [origin for origin in origins if origin]

    @property
    def cors_method_list(self) -> list[str]:
        return self._split_cors_value(self.cors_allow_methods)

    @property
    def cors_header_list(self) -> list[str]:
        return self._split_cors_value(self.cors_allow_headers)

    @staticmethod
    def _split_cors_value(value: str) -> list[str]:
        stripped = value.strip()
        if stripped == "*":
            return ["*"]
        return [item.strip() for item in stripped.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
