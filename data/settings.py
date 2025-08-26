import sys

from libs.eth_async.classes import Singleton
from data.config import SETTINGS_FILE
from data.config import LOG_FILE, SETTINGS_FILE
from loguru import logger
import yaml


class Settings(Singleton):
    def __init__(self):
        with open(SETTINGS_FILE, 'r') as file:
            json_data = yaml.safe_load(file) or {}

        self.check_updates = json_data.get("check_updates", True)
        self.private_key_encryption = json_data.get("private_key_encryption", False)
        self.threads = json_data.get("threads", 4)
        self.exact_wallets_to_run = json_data.get("exact_wallets_to_run", [])
        self.shuffle_wallets = json_data.get("shuffle_wallets", True)
        self.hide_wallet_address_log = json_data.get("hide_wallet_address_log", True)
        self.log_level = json_data.get("log_level", "INFO")
        self.sleep_after_each_cycle_hours = json_data.get("sleep_after_each_cycle_hours", 0)
        self.random_pause_between_wallets_min = json_data.get("random_pause_between_wallets",{}).get("min")
        self.random_pause_between_wallets_max = json_data.get("random_pause_between_wallets", {}).get("max")
        self.random_pause_between_actions_min = json_data.get("random_pause_between_actions", {}).get("min")
        self.random_pause_between_actions_max = json_data.get("random_pause_between_actions", {}).get("max")
        self.tg_bot_id = json_data.get("tg_bot_id", "")
        self.tg_user_id = json_data.get("tg_user_id", "")
        self.retry = json_data.get("retry", {})


# Configure the logger based on the settings
settings = Settings()

if settings.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
    raise ValueError(f"Invalid log level: {settings.log_level}. Must be one of: DEBUG, INFO, WARNING, ERROR")
logger.remove()  # Remove the default logger
logger.add(sys.stderr, level=settings.log_level)

logger.add(LOG_FILE, level="DEBUG")
