from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ha_base_url: str = Field(..., alias="HA_BASE_URL")
    ha_token: str = Field(..., alias="HA_TOKEN")

    price_api_url: str | None = Field(default=None, alias="PRICE_API_URL")
    price_api_key: str | None = Field(default=None, alias="PRICE_API_KEY")

    weather_api_url: str | None = Field(default=None, alias="WEATHER_API_URL")
    weather_api_key: str | None = Field(default=None, alias="WEATHER_API_KEY")

    slack_webhook_url: str | None = Field(default=None, alias="SLACK_WEBHOOK_URL")
    whatsapp_webhook_url: str | None = Field(default=None, alias="WHATSAPP_WEBHOOK_URL")

    mqtt_host: str | None = Field(default=None, alias="MQTT_HOST")
    mqtt_port: int = Field(default=1883, alias="MQTT_PORT")
    mqtt_username: str | None = Field(default=None, alias="MQTT_USERNAME")
    mqtt_password: str | None = Field(default=None, alias="MQTT_PASSWORD")
    mqtt_topics: str | None = Field(default=None, alias="MQTT_TOPICS")

    influxdb_url: str | None = Field(default=None, alias="INFLUXDB_URL")
    influxdb_token: str | None = Field(default=None, alias="INFLUXDB_TOKEN")
    influxdb_org: str = Field(default="auroran", alias="INFLUXDB_ORG")
    influxdb_ai_memory_bucket: str = Field(default="ha_ai_memory", alias="INFLUXDB_AI_MEMORY_BUCKET")

    bedroom_hp_entity: str = Field(default="climate.ac_12488762", alias="BEDROOM_HP_ENTITY")
    bedroom_hp_off_start_hour: int = Field(default=19, alias="BEDROOM_HP_OFF_START_HOUR")
    bedroom_hp_off_end_hour: int = Field(default=9, alias="BEDROOM_HP_OFF_END_HOUR")
    local_timezone: str = Field(default="Europe/Helsinki", alias="LOCAL_TIMEZONE")

    auto_apply: bool = Field(default=False, alias="AUTO_APPLY")
    poll_interval_seconds: int = Field(default=300, alias="POLL_INTERVAL_SECONDS")
