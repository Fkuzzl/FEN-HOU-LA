from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./expense_splitter.db"
    jwt_secret: str = "dev-only-change-me"
    jwt_expire_minutes: int = 60 * 24
    cors_origins: str = "http://localhost:5173"
    cookie_secure: bool = False
    trusted_hosts: str = "localhost,127.0.0.1"
    receipt_dir: str = "./receipts"
    storage_provider: str = "local"
    r2_endpoint: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket: str | None = None
    admin_username: str | None = None
    admin_name: str = "Operator"
    admin_email: str | None = None
    admin_password: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]


settings = Settings()
