from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    mode: Literal["shadow", "live", "off"] = Field(default="shadow", alias="HERMES_MODE")
    hostname: str = Field(default="localhost", alias="HERMES_HOSTNAME")

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    model: str = Field(default="anthropic/claude-sonnet-4-6", alias="HERMES_MODEL")
    classifier_model: str = Field(
        default="claude-haiku-4-5", alias="HERMES_CLASSIFIER_MODEL"
    )

    gmail_address: str = Field(default="", alias="GMAIL_ADDRESS")
    gmail_app_password: str = Field(default="", alias="GMAIL_APP_PASSWORD")
    imap_host: str = Field(default="imap.gmail.com", alias="IMAP_HOST")
    imap_port: int = Field(default=993, alias="IMAP_PORT")
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")

    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str = Field(default="", alias="TWILIO_FROM_NUMBER")
    twilio_webhook_url: str = Field(default="", alias="TWILIO_WEBHOOK_URL")

    allowlist_path: Path = Field(
        default=Path("/etc/hermes/allowlist.yaml"), alias="ALLOWLIST_PATH"
    )
    pause_file: Path = Field(default=Path("/etc/hermes/PAUSE"), alias="PAUSE_FILE")
    state_db: Path = Field(default=Path("/var/lib/hermes/state.db"), alias="STATE_DB")

    rate_hourly: int = Field(default=20, alias="RATE_HOURLY")
    rate_per_sender_daily: int = Field(default=5, alias="RATE_PER_SENDER_DAILY")
    daily_sms_budget_usd: float = Field(default=2.0, alias="DAILY_SMS_BUDGET_USD")
    sms_unit_cost_usd: float = Field(default=0.0079, alias="SMS_UNIT_COST_USD")

    http_host: str = Field(default="127.0.0.1", alias="HTTP_HOST")
    http_port: int = Field(default=8000, alias="HTTP_PORT")


def load_settings() -> Settings:
    return Settings()
