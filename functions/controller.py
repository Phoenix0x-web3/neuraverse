import asyncio
import time
import json
import math
import random

from loguru import logger

from libs.eth_async.client import Client
from modules.neuraverse import NeuraVerse
from utils.db_api.models import Wallet
from utils.twitter.twitter_client import TwitterClient
from utils.discord.discord import DiscordOAuth, DiscordStatus
from data.settings import Settings
from collections import Counter
from modules.bridge import Bridge
from libs.eth_async.data.models import Networks
from modules.zotto import ZottoSwap
from modules.omnihub_nft import OmnihubNFT
from libs.eth_async.utils.utils import randfloat
from data.models import Contracts
from libs.eth_async.data.models import TokenAmount
from utils.db_api.wallet_api import update_wallet_info


class Controller:
    def __init__(self, client: Client, wallet: Wallet, client_sepolia: Client = Client(network=Networks.Sepolia)):
        self.client = client
        self.wallet = wallet
        self.settings = Settings()
        self.portal = NeuraVerse(client=client, wallet=wallet)
        self.bridge = Bridge(client_sepolia=client_sepolia, client=client, wallet=wallet)
        self.zotto = ZottoSwap(client=client, wallet=wallet)
        self.omnihub = OmnihubNFT(client=client, wallet=wallet)

    async def build_actions(self) -> list:
        try:
            actions = []
                 
            if await self.portal.privy.privy_authorize():
                
                account_info = await self.portal.get_account_info()
                points = account_info.get("neuraPoints", 0)
                
                if points == 0:
                    await self.complete_quests()
                else:
                    actions.append(self.complete_quests)
                    
                faucet_last_claim = self.wallet.faucet_last_claim
                
                if not faucet_last_claim:
                    can_use_faucet = True
                else:
                    try:
                        data = json.loads(faucet_last_claim)
                        last_ts = int(data.get("timestamp", 0))
                        now_ms = int(time.time() * 1000)
                        can_use_faucet = (now_ms - last_ts) >= 86_400_000
                    except Exception as e:
                        logger.error(
                            f"{self.wallet} | Failed to parse faucet_last_claim='{faucet_last_claim}': {e}"
                        )
                        can_use_faucet = True

                if can_use_faucet:
                    await self.faucet()

                wallet_balance = await self.client.wallet.balance()
                
                if wallet_balance.Ether > self.settings.min_native_balance:
                
                    total_swaps = random.randint(self.settings.swaps_count_min, self.settings.swaps_count_max)
                    total_bridge = random.randint(self.settings.bridge_count_min, self.settings.bridge_count_max)
                    
                
                    if total_swaps:
                        async def do_swaps():
                            return await self.execute_zotto_swaps(total_swaps=total_swaps)
                        actions.append(do_swaps)

                    if total_bridge:
                        async def do_bridge():
                            return await self.execute_auto_bridge(total_bridge=total_bridge)
                        actions.append(do_bridge)

                    if await self.omnihub.is_minting():
                        if self.settings.omnihub_repeat_if_already_minted:
                            actions.append(self.mint_omnihub_nft)
                    else:
                        actions.append(self.mint_omnihub_nft)
                        
                total_ai_chat = random.randint(self.settings.ai_chat_count_min, self.settings.ai_chat_count_max)
                
                if total_ai_chat:
                        async def do_ai_chat():
                            return await self.run_ai_chat_session(total_ai_chat=total_ai_chat)
                        actions.append(do_ai_chat)

                random.shuffle(actions)
                return actions
            else:
                logger.error(f"{self.wallet} | Privy authorization failed — unable to build actions list")
                return []
        
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return []
                   
    async def update_db_by_user_info(self) -> bool:
        
        user_data = await self.portal.get_account_info()
        leaderboard_data = await self.portal.get_leaderboards_info()
        
        if not user_data:
            logger.error(f"{self.wallet} | Failed to fetch user data")
            return False
        
        if not leaderboard_data:
            logger.error(f"{self.wallet} | Failed to fetch leaderboard data")
            return False
         
        total_points = user_data.get("neuraPoints", None)
        trading_volume = user_data.get("tradingVolume", {}).get("allTime", None)

        leaderboards = leaderboard_data.get("leaderboards", [])
        rank = leaderboards[1].get("accountRank", None)
        
        logger.info(
            f"{self.wallet} | Points={total_points}, Volume={trading_volume}, Rank={rank}"
        )
        
        updates = [
            ("points", total_points),
            ("trading_volume", trading_volume),
            ("rank", rank),
        ]

        for column, data in updates:
            if data is not None:
                update_wallet_info(address=self.wallet.address, name_column=column, data=data)

        return True
         
    async def connect_twitter(self) -> bool:
        
        try:
            logger.info(f"{self.wallet} | Starting Twitter connect flow…")
            
            twitter = TwitterClient(user=self.wallet)

            auth_url, code_verifier = await self.portal.get_twitter_link()
            
            callback = await twitter.connect_twitter_to_site_oauth2(twitter_auth_url=auth_url)
            await twitter.close()
            
            bind_twitter = await self.portal.bind_twitter(callback=callback, code_verifier=code_verifier)
            
            if bind_twitter:
                user_data = await self.portal.get_account_info()
                social_accounts = user_data.get("socialAccounts", [])
                
                if social_accounts:
                    for social in social_accounts:
                        type = social.get('type', '')
        
                        if type == 'twitter':
                            logger.success(f"{self.wallet} | Twitter successfully connected")
                            return True
                        
            logger.error(f"{self.wallet} | Failed to connect Twitter")
            return False
        
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False
    
    async def connect_discord(self) -> bool:
        
        try:
            logger.info(f"{self.wallet} | Starting Discord connect flow…")
            
            guild_id = '1230647507428577332'
            
            discord = DiscordOAuth(wallet=self.wallet, guild_id=guild_id)
            
            auth_url, code_verifier = await self.portal.get_discord_link()
            
            callback, _ = await discord.start_oauth2(oauth_url=auth_url)
            
            bind_discrod = await self.portal.bind_discord(callback=callback, code_verifier=code_verifier)
            
            if bind_discrod:
                user_data = await self.portal.get_account_info()
                social_accounts = user_data.get("socialAccounts", [])
                
                if social_accounts:
                    for social in social_accounts:
                        type = social.get('type', '')
        
                        if type == 'discord':
                            logger.success(f"{self.wallet} | Discord successfully connected")
                            self.wallet.discord_status = DiscordStatus.ok
                            return True
                        
            logger.error(f"{self.wallet} | Failed to connect Discord")
            return False
        
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False
    
    async def connect_socials(self) -> bool:
        
        try:
            user_data = await self.portal.get_account_info()
            
            if not user_data:
                logger.error(f"{self.wallet} | Failed to fetch account info in connect_socials")
                return False

            social_accounts = user_data.get("socialAccounts", []) or []
            
            bound_types = {
                social.get("type")
                for social in social_accounts
                if social.get("type")
            }

            all_ok = True

            if "twitter" not in bound_types:
                
                ok_twitter = await self.connect_twitter()
                all_ok = all_ok and ok_twitter

            if "discord" not in bound_types:
                ok_discord = await self.connect_discord()
                all_ok = all_ok and ok_discord


            return all_ok

        except Exception as e:
            logger.error(f"{self.wallet} | Error in connect_socials — {e}")
            return False
        
    async def complete_quests(self) -> bool:
         
        try: 
            logger.info(f"{self.wallet} | Starting quest processing...")
            
            all_quests = await self.portal.get_all_quests()

            if not all_quests:
                logger.error(f"{self.wallet} | No quests found")
                return False

            random.shuffle(all_quests)
            all_quests.sort(key=lambda quest: quest.get("id") == "claim_faucet")

            counts = Counter(q.get("status") for q in all_quests)
            claimable_quests = counts.get("claimable", 0)
            not_completed_quests = counts.get("notCompleted", 0)

            logger.info(
                f"{self.wallet} | Quests overview: claimable={claimable_quests}, not_completed={not_completed_quests}, total={len(all_quests)}"
            )

            supported_quest = [
                "daily_login",
                "collect_all_pulses",
                "visit_all_map",
                "claim_faucet",
            ]
            
            total_quest_claimed = 0
            total_quest_completed = 0
            total_claim_errors = 0
            total_complete_errors = 0
            
            for quest in all_quests:
                quest_status = quest.get("status")
                quest_id = quest.get("id")
                quest_name = quest.get("name")
                quest_points = quest.get("points")
                
                
                try:
                    if quest_status == "notCompleted":
                        if quest_id not in supported_quest:
                            logger.debug(f"{self.wallet} | Unsupported quest skipped: {quest_name}")
                            continue

                        logger.info(f"{self.wallet} | Running quest: {quest_name} ({quest_points} pts)")

                        completion_result = await self.execute_single_quest(quest)
                        
                        
                        random_sleep = random.randint(self.settings.random_pause_between_actions_min, self.settings.random_pause_between_actions_max)
                        
                        if not completion_result:
                            total_complete_errors += 1
                            logger.error(f"{self.wallet} | Failed to complete quest: {quest_name}. Next action in {random_sleep}s")
                            await asyncio.sleep(random_sleep)
                            continue

                        total_quest_completed += 1
                        logger.success(f"{self.wallet} | Quest '{quest_name}' completed ({quest_points} pts). Next action in {random_sleep}s")
                        await asyncio.sleep(random_sleep)

                        logger.info(f"{self.wallet} | Claiming reward for quest: {quest_name}")
                        claim_result = await self.portal.claim_quest_reward(quest)
                        
                        random_sleep = random.randint(self.settings.random_pause_between_actions_min, self.settings.random_pause_between_actions_max)

                        if not claim_result:
                            total_claim_errors += 1
                            logger.error(f"{self.wallet} | Failed to claim quest: {quest_name}. Next action in {random_sleep}s")
                            await asyncio.sleep(random_sleep)
                        else:
                            total_quest_claimed += 1
                            logger.success(f"{self.wallet} | Successfully claimed quest: {quest_name}. Next action in {random_sleep}s")
                            await asyncio.sleep(random_sleep)

                    elif quest_status == "claimable":
                        logger.info(f"{self.wallet} | Claiming reward for quest: {quest_name}")
                        claim_result = await self.portal.claim_quest_reward(quest)
                        
                        random_sleep = random.randint(self.settings.random_pause_between_actions_min, self.settings.random_pause_between_actions_max)
                        
                        if not claim_result:
                            total_claim_errors += 1
                            logger.error(f"{self.wallet} | Failed to claim quest: {quest_name}. Next action in {random_sleep}s")
                            await asyncio.sleep(random_sleep)
                        else:
                            total_quest_claimed += 1
                            logger.success(f"{self.wallet} | Successfully claimed quest: {quest_name}. Next action in {random_sleep}s")
                            await asyncio.sleep(random_sleep)

                except Exception as e:
                    logger.error(f"{self.wallet} | Error while processing quest '{quest_name}': {e}")
                    total_complete_errors += 1
                    continue

            logger.info(
                f"{self.wallet} | Quests summary: claimed={total_quest_claimed}, completed={total_quest_completed}, "
                f"claim_failures={total_claim_errors}, complete_failures={total_complete_errors}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False
    
    async def execute_single_quest(self, quest: dict) -> bool:
        
        try:
            quest_id = quest.get("id")
            quest_name = quest.get("name")

            if quest_id == "daily_login":
                return True

            if quest_id == "collect_all_pulses":
                return await self.collect_all_pulses()

            elif quest_id == "visit_all_map":
                return await self.visit_all_supported_locations()

            elif quest_id == "claim_faucet":
                await self.portal.visit_location("faucet:visit")
                return await self.portal.faucet()

            else:
                raise TypeError(f"Quest {quest_name} not supported yet")
            
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False
            
    async def visit_all_supported_locations(self) -> bool:
        
        try:
            SUPPORTED_LOCATIONS = [
                "game:visitFountain",
                "game:visitBridge",
                "game:visitOracle",
                "game:visitValidatorHouse",
                "game:visitObservationDeck",
            ]
            
            locations = SUPPORTED_LOCATIONS
            random.shuffle(locations)

            for location in locations:
                logger.info(f"{self.wallet} | Visiting location: {location}")
                await self.portal.visit_location(location)
                random_sleep = random.randint(self.settings.random_pause_between_actions_min, self.settings.random_pause_between_actions_max)
                logger.success(f"{self.wallet} | Visited location {location}. Next in {random_sleep}s")
                await asyncio.sleep(random_sleep)

            return True
        
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

    async def collect_all_pulses(self) -> bool:
        try:
            account_info = await self.portal.get_account_info()

            if not account_info:
                logger.error(f"{self.wallet} | Unable to fetch account info")
                raise ValueError("Account info is missing or invalid")

            pulses_section = account_info.get("pulses", {})
            pulse_list = pulses_section.get("data", [])

            uncollected = [pulse for pulse in pulse_list if pulse.get("isCollected") is False]

            pulse_ids = []

            for pulse in uncollected:
                pulse_id = (pulse.get("id") or "").replace("pulse:", "")
                if pulse_id:
                    pulse_ids.append(pulse_id)

            random.shuffle(pulse_ids)

            logger.info(f"{self.wallet} | Uncollected pulses ({len(pulse_ids)}): [{', '.join(pulse_ids) if pulse_ids else 'none'}]")

            for pulse_id in pulse_ids:
                logger.info(f"{self.wallet} | Collecting pulse: {pulse_id}")
                await self.portal.collect_single_pulse(pulse_id)
                random_sleep = random.randint(self.settings.random_pause_between_actions_min, self.settings.random_pause_between_actions_max)
                logger.success(f"{self.wallet} | Collected pulse {pulse_id}. Next in {random_sleep}s")
                await asyncio.sleep(random_sleep)

            account_info = await self.portal.get_account_info()

            if not account_info:
                logger.error(f"{self.wallet} | Unable to fetch account info")
                raise ValueError("Account info is missing or invalid")

            pulses_section = account_info.get("pulses", {})
            pulse_list = pulses_section.get("data", [])

            all_collected = all(pulse.get("isCollected", False) for pulse in pulse_list)

            if not all_collected:
                remaining = []
                for pulse in pulse_list:
                    if not pulse.get("isCollected", False):
                        pulse_id = (pulse.get("id") or "").replace("pulse:", "")
                        if pulse_id:
                            remaining.append(pulse)
                logger.error(f"{self.wallet} | Not all pulses collected — remaining: {remaining}")
                return False

            logger.success(f"{self.wallet} | All pulses collected successfully ({len(pulse_list)} total)")
            return True
        
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

    async def run_ai_chat_session(self, total_ai_chat: int) -> bool:

        try: 
            
            if not total_ai_chat:
                logger.warning(f"{self.wallet} | total_ai_chat is 0 — configure ai_chat_count_min/max in settings.yaml")
                return False
            
            list_validators = await self.portal.get_validators()

            if not list_validators:
                logger.error(f"{self.wallet} | No validators available for AI chat")
                return False

            list_messages = self.settings.questions_for_ai_list

            if not list_messages:
                logger.error(f"{self.wallet} | No AI messages configured")
                return False

            attempts = 0
            completed = 0
            max_fail_attempts = total_ai_chat * 3
            
            logger.info(f"{self.wallet} | AI chat session start (total={total_ai_chat})")
            while completed < total_ai_chat and attempts < max_fail_attempts:
                
                validator_id = random.choice(list_validators).get("id", "")

                if not validator_id:
                    logger.error(f"{self.wallet} | Validator ID is empty or missing in validators list — skipping this attempt")
                    attempts += 1
                    continue

                message = random.choice(list_messages)

                payload = {"messages": [{"role": "user", "content": message}]}
                
                logger.info(f"{self.wallet} | Sending AI message to validator {validator_id}: '{message}'")
                
                message_list = await self.portal.chat(payload=payload, validator_id=validator_id)

                if message_list:
                    completed += 1
                    attempts = 0
                    logger.success(f"{self.wallet} | AI chat response received from validator {validator_id}: {message_list}")
                else:
                    attempts += 1
                    logger.error(f"{self.wallet} | AI chat failed for validator {validator_id}")

                if completed < total_ai_chat:
                    random_sleep = random.randint(self.settings.random_pause_between_actions_min, self.settings.random_pause_between_actions_max)
                    logger.info(f"{self.wallet} | Next AI message in {random_sleep}s")
                    await asyncio.sleep(random_sleep)
                    
            logger.info(f"{self.wallet} | AI chat session finished: {completed}/{total_ai_chat}") 
            return True
                    
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False
                            
    async def execute_auto_bridge(self, total_bridge: int, bridge_all_to_neura: bool = False) -> bool:
        try:
            
            if not total_bridge:
                logger.warning(f"{self.wallet} | total_bridge is 0 — configure bridge_count_min/max in settings.yaml")
                return False
            
            if bridge_all_to_neura:
                logger.info(f"{self.wallet} | Starting full Sepolia → Neura bridge...")
                await self.portal.visit_location("bridge:visit")
                sucsess = await self.bridge.bridge_sepolia_to_neura_all()
                
                if sucsess:
                    return True
                else:
                    return False
                           
            else:
                await self.portal.visit_location("bridge:visit")
                
                directions = ["neura_to_sepolia", "sepolia_to_neura"]

                attempts = 0
                completed = 0
                max_fail_attempts = total_bridge * 3
                
                logger.info(f"{self.wallet} | Auto‑bridge session started: total={total_bridge}")

                while completed < total_bridge and attempts < max_fail_attempts:
                    direction = random.choice(directions)

                    if direction == "neura_to_sepolia":
                        sucsess = await self.bridge.bridge_neura_to_sepolia_percent()
                        attempts += 1
                        
                        if sucsess:
                            attempts = 0
                            await self.claim_pending_sepolia_bridges()
                            
                        else:
                            logger.warning(f"{self.wallet} | Neura balance too low, trying Sepolia → Neura instead")
                            sucsess = await self.bridge.bridge_sepolia_to_neura_percent()
                            attempts += 1

                            if not sucsess:
                                continue
                            else:
                                attempts = 0
                            
                        completed += 1

                    else:
                        
                        sucsess = await self.bridge.bridge_sepolia_to_neura_percent()
                        attempts += 1
                        
                        if not sucsess:
                            logger.warning(f"{self.wallet} | Sepolia balance too low, trying Neura → Sepolia instead")
                            sucsess = await self.bridge.bridge_neura_to_sepolia_percent()
                            attempts += 1
                            
                            if sucsess:
                                attempts = 0
                                await self.claim_pending_sepolia_bridges()
                            else:
                                continue
                        else:
                            attempts = 0
                            
                        completed += 1
                
                logger.info(f"{self.wallet} | Auto-bridge session completed: {completed}/{total_bridge}")
                return True
             
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False
                                                        
    async def claim_pending_sepolia_bridges(self, wait_ms: int = 60000) -> bool:
        
        try:
            logger.info(f"{self.wallet} | Checking validated Sepolia bridge claims…")

            if wait_ms > 0:
                logger.info(f"{self.wallet} | Waiting {wait_ms} ms before fetching validated Sepolia bridge claims…")
                await asyncio.sleep(wait_ms / 1000)

            transactions = await self.portal.get_claim_tokens_on_sepolia()

            if not transactions:
                logger.info(f"{self.wallet} | No transactions found to process on Sepolia")
                return True

            to_claim = [
                transaction
                for transaction in transactions
                if str(transaction.get("chainId")) == Networks.Sepolia.chain_id
                and transaction.get("status") == "validated"
                and transaction.get("encodedMessage")
                and isinstance(transaction.get("messageSignatures"), list)
                and len(transaction.get("messageSignatures", [])) > 0
            ]

            if not to_claim:
                logger.info(f"{self.wallet} | No validated transactions to claim")
                return True

            logger.info(f"{self.wallet} | Found {len(to_claim)} validated tx to claim on Sepolia")

            
            for tx_info in to_claim:
                tx_hash_short = tx_info.get("transactionHash", tx_info.get("id", "0x..."))[:10]

                try:
                    logger.info(f"{self.wallet} | Claiming {tx_hash_short}...")

                    encoded_message = tx_info["encodedMessage"]
                    message_signatures = tx_info["messageSignatures"]

                    if isinstance(encoded_message, str):
                        if encoded_message.startswith("0x"):
                            encoded_message = bytes.fromhex(encoded_message[2:])
                        else:
                            encoded_message = bytes.fromhex(encoded_message)

                    signatures_bytes = []

                    for sig in message_signatures:
                        if isinstance(sig, str):
                            if sig.startswith("0x"):
                                signatures_bytes.append(bytes.fromhex(sig[2:]))
                            else:
                                signatures_bytes.append(bytes.fromhex(sig))
                        else:
                            signatures_bytes.append(sig)
                            
                    transaction = await self.bridge.claim_token_on_sepolia(encoded_message=encoded_message, signatures_bytes=signatures_bytes)
                    
                    if transaction:
                        logger.success(f"{self.wallet} | Successfully claimed Sepolia bridge tx {tx_hash_short}")
                    else:
                        logger.error(f"{self.wallet} | Failed to claim Sepolia bridge tx {tx_hash_short}")
                            
                except Exception as e:
                    error_msg = str(e)
                    if "already claimed" in error_msg.lower() or "already processed" in error_msg.lower() or "duplicate" in error_msg.lower():
                        logger.warning(f"{self.wallet} | Skip (Already claimed): {tx_hash_short}")
                        continue
                    logger.error(f"{self.wallet} | Failed to claim {tx_hash_short}: {error_msg}")

            logger.success(f"{self.wallet} | Claim process completed")
            return True
        
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False
        
    async def execute_zotto_swaps(self, total_swaps: int) -> bool:
        try: 
               
            if not total_swaps:
                logger.warning(f"{self.wallet} | total_swaps is 0 — configure swaps_count_min/max in settings.yaml")
                return False
            
            
            tokens_list = await self.zotto.get_available_token_contracts()
            
            if not tokens_list or len(tokens_list) < 2:
                logger.error(f"{self.wallet} | Not enough tokens available")
                return False
            
            random.shuffle(tokens_list)
            
            attempts = 0 
            completed = 0
            max_fail_attempts = total_swaps * 3

            logger.info(f"{self.wallet} | Starting Zotto auto-swap: total={total_swaps}")
            
            all_token_balances = await self.zotto.current_balances(tokens_list)
            
            while completed < total_swaps and attempts < max_fail_attempts:
                
                logger.debug(f"{self.wallet} | DEBUG: loop heartbeat → completed={completed}, attempts={attempts}, total={total_swaps}")

                candidates_with_balance = [
                    token for token in tokens_list if token.address in all_token_balances and all_token_balances[token.address].Ether > 0.1
                ]

                if not candidates_with_balance:
                    logger.error(f"{self.wallet} | No tokens with sufficient balance for swap")
                    break

                native_balance = await self.client.wallet.balance()
                min_native_balance = self.settings.min_native_balance
                
                if native_balance.Ether < 0.15:
                    logger.warning(
                        f"{self.wallet} | Native balance critically low ({native_balance.Ether} ANKR < 0.15 ANKR), stopping Zotto swaps"
                    )
                    break

                try:
                    if native_balance.Ether < min_native_balance:
                        
                        logger.warning(f"{self.wallet} | Native balance low: {native_balance.Ether} ANRK (min required: {min_native_balance} ANRK)")

                        while native_balance.Ether < min_native_balance and attempts < max_fail_attempts:
                            
                            if native_balance.Ether < 0.15:
                                break
                            
                            spendables = [token for token in candidates_with_balance if token.address != Contracts.ANKR.address]

                            if not spendables:
                                attempts += 1
                                break

                            from_token = random.choice(spendables)
                            
                            tokens_price = await self.zotto.get_pool_prices_if_liquid(token_0=from_token, token_1=Contracts.ANKR)

                            if not tokens_price:
                                attempts += 1
                                continue
                            
                            precision = random.randint(2, 4)
                            percent = randfloat(from_=self.settings.swaps_percent_min, to_=self.settings.swaps_percent_max, step=0.001) / 100
                            raw_amount = float(all_token_balances[from_token.address].Ether) * percent
                            factor = 10 ** precision
                            safe_amount = math.floor(raw_amount * factor) / factor
                            
                            swap_amount = TokenAmount(
                                amount=safe_amount,
                                decimals=await self.client.transactions.get_decimals(contract=from_token.address),
                            )
                            
                            logger.info(f"{self.wallet} | Restoring native balance: swapping {swap_amount.Ether} {from_token.title} → ANKR")
                            
                            ok = await self.zotto.execute_swap(
                                from_token=from_token,
                                to_token=Contracts.ANKR,
                                amount=swap_amount,
                                tokens_price=tokens_price
                            )
                            
                            random_sleep = random.randint(
                                self.settings.random_pause_between_actions_min,
                                self.settings.random_pause_between_actions_max,
                            )
                            
                            if ok:
                                
                                completed += 1
                                attempts = 0
                                logger.success(
                                    f"{self.wallet} | Native balance restored: swapped {swap_amount.Ether} {from_token.title} → ANKR "
                                    f"({completed}/{total_swaps}). Next action in {random_sleep}s"
                                )
                                await asyncio.sleep(random_sleep)
                                
                                if completed >= total_swaps:
                                    break
                                
                                native_balance = await self.client.wallet.balance()
                                all_token_balances[from_token.address] = await self.client.wallet.balance(from_token)
                                all_token_balances[Contracts.ANKR.address] = native_balance
                                
                                if from_token in candidates_with_balance:
                                    candidates_with_balance.remove(from_token)
                            else:
                                
                                attempts += 1
                                logger.error(
                                    f"{self.wallet} | Failed to restore native balance: swap {swap_amount.Ether} {from_token.title} → ANKR failed. "
                                    f"Next action in {random_sleep}s"
                                )
                                await asyncio.sleep(random_sleep)
                                continue
                            
                        if native_balance.Ether < min_native_balace:
                            break
                        else:
                            continue

                    else:
                        
                        from_token = random.choice(candidates_with_balance)
                        other_tokens = [token for token in tokens_list if token.address != from_token.address]
                        to_token = random.choice(other_tokens)

                        tokens_price = await self.zotto.get_pool_prices_if_liquid(token_0=from_token, token_1=to_token)

                        if not tokens_price:
                            attempts += 1
                            continue

                        from_token_balance = all_token_balances[from_token.address]
                        percent_to_swap = randfloat(from_=self.settings.swaps_percent_min, to_=self.settings.swaps_percent_max, step=0.001) / 100
                        swap_amount = TokenAmount(
                            amount=round(float(from_token_balance.Ether) * percent_to_swap, random.randint(2, 4)),
                            decimals=18
                            if from_token.address == Contracts.ANKR.address
                            else await self.client.transactions.get_decimals(contract=from_token.address),
                        )
                        
                        logger.info(f"{self.wallet} | Swapping {swap_amount.Ether} {from_token.title} → {to_token.title}")
                        
                        ok = await self.zotto.execute_swap(
                            from_token=from_token,
                            to_token=to_token,
                            amount=swap_amount,
                            tokens_price=tokens_price,
                        )
                        
                        
                        random_sleep = random.randint(
                            self.settings.random_pause_between_actions_min,
                            self.settings.random_pause_between_actions_max,
                        )
                        
                        if ok:
                            
                            attempts = 0
                            all_token_balances[from_token.address] = await self.client.wallet.balance(from_token)
                            all_token_balances[to_token.address] = await self.client.wallet.balance(to_token)
                            logger.success(
                                f"{self.wallet} | Swap successful: {swap_amount.Ether} {from_token.title} → {to_token.title}. "
                                f"Next action in {random_sleep}s"
                            )
                            completed += 1
                            await asyncio.sleep(random_sleep)
                            
                        else:
                            
                            attempts += 1
                            logger.error(
                                f"{self.wallet} | Swap failed: {swap_amount.Ether} {from_token.title} → {to_token.title}. "
                                f"Next action in {random_sleep}s"
                            )
                            await asyncio.sleep(random_sleep)

                except Exception as e:
                    logger.error(f"{self.wallet} | Unexpected error during Zotto swap cycle: {e}")
                    attempts += 1
                    continue

            logger.info(f"{self.wallet} | Zotto swap cycle completed: {completed}/{total_swaps}")
            return True
        
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False
    
    async def mint_omnihub_nft(self) -> bool:
        try:     
            logger.info(f"{self.wallet} | Starting Omnihub NFT mint process…")
            
            quantity = random.randint(self.settings.omnihub_nft_mint_count_per_transaction_min, self.settings.omnihub_nft_mint_count_per_transaction_max)
            mint_nft = await self.omnihub.mint_nft(quantity=quantity)
            
            if mint_nft:
                logger.success(f"{self.wallet} | Successfully minted Omnihub NFT (quantity={quantity})")
                return True
            else:
                logger.error(f"{self.wallet} | Failed to mint Omnihub NFT (quantity={quantity})")
                return False
        
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False
 
    async def faucet(self) -> bool:
        await self.portal.visit_location("faucet:visit")
        return await self.portal.faucet()