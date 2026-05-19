import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    BOT_TOKEN: str = field(default_factory=lambda: os.environ["BOT_TOKEN"])
    BOT_USERNAME: str = field(default_factory=lambda: os.getenv("BOT_USERNAME", ""))
    DATABASE_URL: str = field(default_factory=lambda: os.environ["DATABASE_URL"])
    YUKASSA_SHOP_ID: str = field(default_factory=lambda: os.environ["YUKASSA_SHOP_ID"])
    YUKASSA_SECRET_KEY: str = field(default_factory=lambda: os.environ["YUKASSA_SECRET_KEY"])
    CHANNEL_ID: int = field(default_factory=lambda: int(os.environ["CHANNEL_ID"]))
    ADMIN_IDS: List[int] = field(
        default_factory=lambda: [int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]
    )
    SUPPORT_USERNAME: str = field(default_factory=lambda: os.getenv("SUPPORT_USERNAME", ""))
    WEBHOOK_PORT: int = field(default_factory=lambda: int(os.getenv("WEBHOOK_PORT", "8080")))
    BASE_URL: str = field(default_factory=lambda: os.getenv("BASE_URL", "https://t.me"))
    TEST_MODE: bool = field(default_factory=lambda: os.getenv("TEST_MODE", "false").lower() == "true")


PLANS = {
    "1m": {"name": "1 месяц", "months": 1, "price": 2499, "save": None},
}

config = Config()

# Override prices in test mode
if config.TEST_MODE:
    for plan in PLANS.values():
        plan["price"] = 10
