from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    paypal_client_id: str = ""
    paypal_client_secret: str = ""
    paypal_environment: str = "sandbox"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_thinking_level: str = ""  # optional: low, medium or high, if the model accepts it
    database_url: str = "sqlite:///./horkos.db"
    jwt_secret: str = ""
    frontend_origin: str = "http://localhost:3000"
    paypal_funding: str = "simulated"  # simulated or sandbox
    paypal_return_url: str = "http://localhost:3000/money-tracker"
    paypal_cancel_url: str = "http://localhost:3000/money-tracker"
    paypal_payout_email: str = ""
    demo_controls: bool = True


settings = Settings()