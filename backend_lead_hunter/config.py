from functools import lru_cache
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    apify_token: str = Field(alias="APIFY_TOKEN")
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    tg_lead_bot_token: str = Field(validation_alias=AliasChoices("TG_LEAD_BOT", "TG_LEAD_BOT_TOKEN"))
    my_chat_id: str = Field(alias="MY_CHAT_ID")

    apify_instagram_search_actor: str = Field(
        default="apify/instagram-search-scraper",
        alias="APIFY_INSTAGRAM_SEARCH_ACTOR",
    )
    apify_instagram_profile_actor: str = Field(
        default="apify/instagram-scraper",
        alias="APIFY_INSTAGRAM_PROFILE_ACTOR",
    )
    apify_instagram_comment_actor: str = Field(
        default="apify/instagram-comment-scraper",
        alias="APIFY_INSTAGRAM_COMMENT_ACTOR",
    )

    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")
    dry_run: bool = Field(default=False, alias="DRY_RUN")
    apify_poll_interval_seconds: int = Field(default=20, alias="APIFY_POLL_INTERVAL_SECONDS")

    default_keywords: str = Field(
        default=(
            "автоматизация продаж,продажи в директ,нейросети для бизнеса,"
            "чат боты для бизнеса,воронка продаж,CRM для бизнеса,нейропродавец"
        ),
        alias="DEFAULT_KEYWORDS",
    )
    similar_donor_keywords: str = Field(
        default=(
            "ИИ для бизнеса,автоматизация бизнеса,автоворонка продаж,amocrm,"
            "онлайн школа,запуск онлайн школы,инстаграм продажи,лиды из инстаграм,"
            "ИИ ассистент,AI эксперт,бизнес процессы,отдел продаж,скрипты продаж,"
            "обработка заявок,клиентский сервис,директ менеджер"
        ),
        alias="SIMILAR_DONOR_KEYWORDS",
    )
    seed_donors: str = Field(default="", alias="SEED_DONORS")
    min_donor_followers: int = Field(default=5000, alias="MIN_DONOR_FOLLOWERS")

    auto_hunt_enabled: bool = Field(default=True, alias="AUTO_HUNT_ENABLED")
    auto_hunt_interval_hours: int = Field(default=24, alias="AUTO_HUNT_INTERVAL_HOURS")
    auto_hunt_start_on_boot: bool = Field(default=False, alias="AUTO_HUNT_START_ON_BOOT")
    auto_hunt_max_donors: int = Field(default=3, alias="AUTO_HUNT_MAX_DONORS")
    auto_hunt_max_comments_per_post: int = Field(default=100, alias="AUTO_HUNT_MAX_COMMENTS_PER_POST")
    auto_hunt_max_leads: int = Field(default=10, alias="AUTO_HUNT_MAX_LEADS")
    comment_fetch_growth_factor: int = Field(default=2, alias="COMMENT_FETCH_GROWTH_FACTOR")
    comment_fetch_hard_limit: int = Field(default=1000, alias="COMMENT_FETCH_HARD_LIMIT")
    database_path: str = Field(default="lead_hunter.db", alias="DATABASE_PATH")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def default_keyword_list(self) -> list[str]:
        return self._split_csv(self.default_keywords)

    @property
    def similar_donor_keyword_list(self) -> list[str]:
        return self._split_csv(self.similar_donor_keywords)

    @property
    def seed_donor_list(self) -> list[str]:
        result: list[str] = []
        for donor in [item.removeprefix("@") for item in self._split_csv(self.seed_donors)]:
            if donor and donor not in result:
                result.append(donor)
        return result

    def _split_csv(self, value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
