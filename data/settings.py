import sys

import yaml
from loguru import logger

from data.config import LOG_FILE, SETTINGS_FILE
from libs.eth_async.classes import Singleton


class Settings(Singleton):
    def __init__(self):
        with open(SETTINGS_FILE, "r") as file:
            json_data = yaml.safe_load(file) or {}

        self.check_git_updates = json_data.get("check_git_updates", True)
        self.private_key_encryption = json_data.get("private_key_encryption", False)
        self.threads = json_data.get("threads", 4)
        self.range_wallets_to_run = json_data.get("range_wallets_to_run", [])
        self.exact_wallets_to_run = json_data.get("exact_wallets_to_run", [])
        self.shuffle_wallets = json_data.get("shuffle_wallets", True)
        self.show_wallet_address_logs = json_data.get("show_wallet_address_logs", True)
        self.log_level = json_data.get("log_level", "INFO")
        self.random_pause_start_wallet_min = json_data.get("random_pause_start_wallet", {}).get("min")
        self.random_pause_start_wallet_max = json_data.get("random_pause_start_wallet", {}).get("max")
        self.random_pause_between_actions_min = json_data.get("random_pause_between_actions", {}).get("min")
        self.random_pause_between_actions_max = json_data.get("random_pause_between_actions", {}).get("max")
        self.random_pause_wallet_after_completion_min = json_data.get("random_pause_wallet_after_completion", {}).get("min")
        self.random_pause_wallet_after_completion_max = json_data.get("random_pause_wallet_after_completion", {}).get("max")

        self.swaps_count_min = json_data.get("swaps_count", {}).get("min")
        self.swaps_count_max = json_data.get("swaps_count", {}).get("max")
        self.swaps_percent_min = json_data.get("swaps_percent", {}).get("min")
        self.swaps_percent_max = json_data.get("swaps_percent", {}).get("max")
        self.swaps_allowed_tokens = json_data.get("swaps_allowed_tokens", [])

        self.bridge_count_min = json_data.get("bridge_count", {}).get("min")
        self.bridge_count_max = json_data.get("bridge_count", {}).get("max")
        self.brige_percet_min = json_data.get("bridge_percet", {}).get("min")
        self.brige_percet_max = json_data.get("bridge_percet", {}).get("max")

        self.ai_chat_count_min = json_data.get("ai_chat_count", {}).get("min")
        self.ai_chat_count_max = json_data.get("ai_chat_count", {}).get("max")
        self.questions_for_ai_list = json_data.get("questions_for_ai_list", [])

        self.min_native_balance = json_data.get("min_native_balance", 1)
        self.max_gas_price = json_data.get("max_gas_price", 700)

        self.omnihub_nft_mint_count_per_transaction_min = json_data.get("omnihub_nft_mint_count_per_transaction", {}).get("min")
        self.omnihub_nft_mint_count_per_transaction_max = json_data.get("omnihub_nft_mint_count_per_transaction", {}).get("max")

        self.omnihub_repeat_if_already_minted = json_data.get("omnihub_repeat_if_already_minted", False)

        self.capmonster_api_key = json_data.get("capmonster_api_key", "")


# Configure the logger based on the settings
settings = Settings()

if settings.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
    raise ValueError(f"Invalid log level: {settings.log_level}. Must be one of: DEBUG, INFO, WARNING, ERROR")
logger.remove()  # Remove the default logger
logger.add(sys.stderr, level=settings.log_level)

logger.add(LOG_FILE, retention="10 days", level=settings.log_level)
