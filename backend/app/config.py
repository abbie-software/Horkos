from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_environment: str = "sandbox"
    openai_api_key: str = ""
    openai_model: str = ""
    database_url: str = "sqlite:///./horkos.db"
    jwt_secret: str = ""
    frontend_origin: str = "http://localhost:3000"


settings = Settings()