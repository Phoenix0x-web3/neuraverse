import base64
import hashlib
import json
import os
import re
import time

from loguru import logger

from data.constants import DEFAULT_HEADERS
from data.settings import Settings
from libs.eth_async.client import Client
from modules.privy_authentication import PrivyAuth
from utils.browser import Browser
from utils.db_api.models import Wallet
from utils.db_api.wallet_api import update_wallet_info
from utils.twitter.twitter_client import TwitterOauthData


class NeuraVerse:
    __module__ = "Neuraverse"
    BASE_URL = "https://neuraverse-testnet.infra.neuraprotocol.io/api"

    def __init__(self, client: Client, wallet: Wallet) -> None:
        self.wallet = wallet
        self.client = client
        self.session = Browser(wallet=wallet)

        self.privy = PrivyAuth(client=client, wallet=self.wallet)

        self.settings = Settings()

    @property
    def headers(self) -> dict:
        return {**DEFAULT_HEADERS, "authorization": f"Bearer {self.wallet.identity_token}"}

    async def get_account_info(self) -> dict:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        try:
            logger.debug(f"{self.wallet} | Requesting account info")

            response = await self.session.get(url=f"{self.BASE_URL}/account", cookies=self.privy.cookies, headers=self.headers)

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                raise RuntimeError(f"Non-200 response ({response.status_code})")

            account_info = response.json()

            if not account_info:
                raise ValueError(f"Invalid account info response: {response.text}")

            logger.debug(f"{self.wallet} | Account info fetched successfully")

            return account_info
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return {}

    async def get_leaderboards_info(self) -> dict:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        try:
            logger.debug(f"{self.wallet} | Requesting leaderboards info")

            response = await self.session.get(url=f"{self.BASE_URL}/leaderboards", cookies=self.privy.cookies, headers=self.headers)

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                raise RuntimeError(f"Non-200 response ({response.status_code})")

            account_info = response.json()

            if not account_info:
                raise ValueError(f"Invalid leaderboards info response: {response.text}")

            logger.debug(f"{self.wallet} | Leaderboards info fetched successfully")

            return account_info
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return {}

    async def get_all_quests(self) -> list:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        try:
            logger.debug(f"{self.wallet} | Requesting all quests")

            response = await self.session.get(
                url=f"{self.BASE_URL}/tasks",
                cookies=self.privy.cookies,
                headers=self.headers,
            )

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                raise RuntimeError(f"Non-200 response ({response.status_code})")

            all_quest = response.json().get("tasks", [])

            if not all_quest:
                raise ValueError(f"Invalid all quests response: {response.text}")

            logger.debug(f"{self.wallet} | All quests fetched successfully")
            return all_quest
        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return []

    async def claim_quest_reward(self, quest: dict) -> bool:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        quest_id = quest.get("id")
        quest_name = quest.get("name")

        logger.debug(f"{self.wallet} | Claiming reward for quest '{quest_name}' (id={quest_id})")

        try:
            response = await self.session.post(
                url=f"{self.BASE_URL}/tasks/{quest_id}/claim",
                cookies=self.privy.cookies,
                headers=self.headers,
                json={},
            )

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                raise RuntimeError(f"Non-200 response ({response.status_code})")

            status = response.json().get("status", None)

            if not status and status != "claimed":
                raise ValueError(f"Invalid quest claim response: {response.text}")

            logger.debug(f"{self.wallet} | Reward claimed successfully for quest '{quest_name}' (id={quest_id})")
            return True

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

    async def collect_single_pulse(self, pulse_id: str) -> bool:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        try:
            logger.debug(f"{self.wallet} | Collecting pulse with id={pulse_id}")

            payload = {
                "type": "pulse:collectPulse",
                "payload": {
                    "id": "pulse:" + pulse_id,
                },
            }

            response = await self.session.post(
                url=f"{self.BASE_URL}/events",
                cookies=self.privy.cookies,
                headers=self.headers,
                json=payload,
            )

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                raise RuntimeError(f"Non-200 response ({response.status_code})")

            logger.debug(f"{self.wallet} | Pulse collected successfully (id={pulse_id})")
            return True

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

    async def visit_location(self, location_id: str) -> bool:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        try:
            logger.debug(f"{self.wallet} | Visiting location {location_id}")
            payload = {
                "type": f"{location_id}",
            }

            response = await self.session.post(
                url=f"{self.BASE_URL}/events",
                cookies=self.privy.cookies,
                headers=self.headers,
                json=payload,
            )

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                raise RuntimeError(f"Non-200 response ({response.status_code})")

            logger.debug(f"{self.wallet} | Location {location_id} visited successfully")
            return True

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

    async def faucet(self) -> bool:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        try:
            logger.info(f"{self.wallet} | Starting faucet claim process")

            headers = {
                "sec-ch-ua-platform": '"Windows"',
                "Referer": "https://neuraverse.neuraprotocol.io/?section=faucet",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
                "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
            }

            response = await self.session.get(url="https://neuraverse.neuraprotocol.io/_next/static/chunks/8571-6adecd311a93bda8.js", headers=headers)
            logger.debug(f"{self.wallet} | Faucet JS chunk status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                raise RuntimeError(f"Non-200 response ({response.status_code})")

            action_id = None
            js_code = response.text

            pattern = r'createServerReference\)\("([a-f0-9]+)"'
            match = re.search(pattern, js_code)

            if match:
                action_id = match.group(1)
                logger.debug(f"{self.wallet} | Action ID extracted successfully: {action_id}")
            else:
                logger.error(f"[{self.wallet}] | Failed to extract action ID")
                return False

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

        try:
            logger.debug(f"{self.wallet} | Submitting faucet claim request")

            headers = {
                "accept": "text/x-component",
                "accept-language": "en-US,en;q=0.9,ru;q=0.8,zh-TW;q=0.7,zh;q=0.6,uk;q=0.5",
                "content-type": "text/plain;charset=UTF-8",
                "next-action": action_id,
                "next-router-state-tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
                "origin": "https://neuraverse.neuraprotocol.io",
                "priority": "u=1, i",
                "referer": "https://neuraverse.neuraprotocol.io/?section=faucet",
            }

            params = {
                "section": "faucet",
            }

            if self.wallet.faucet_last_claim:
                cookie = {**self.privy.cookies, "faucet_last_claim": self.wallet.faucet_last_claim}
            else:
                cookie = self.privy.cookies

            logger.debug(f"{self.wallet} | Faucet POST cookies keys: {list(cookie.keys())}")

            data = '["' + self.client.account.address + '",267,"' + self.wallet.identity_token + '",true]'

            response = await self.session.post(
                url="https://neuraverse.neuraprotocol.io/",
                params=params,
                cookies=cookie,
                headers=headers,
                data=data,
            )

            logger.debug(f"{self.wallet} | Faucet POST response text (trimmed): {response.text[:600]}")

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                raise RuntimeError(f"Non-200 response ({response.status_code})")

            if "Insufficient neuraPoints." in response.text:
                logger.error(f"{self.wallet} | Insufficient neuraPoints.")
                return False

            elif "Faucet queue full" in response.text:
                logger.error(f"{self.wallet} | Faucet queue full, please retry in a minute.")
                return False

            elif "Address has already received" in response.text:
                logger.warning(f"{self.wallet} | Address has already received")
                return False

            elif "ANKR distribution successful" in response.text:
                logger.success(f"{self.wallet} | Faucet claimed successfully")

                ts_ms = int(time.time() * 1000)
                faucet_last_claim = json.dumps({"timestamp": ts_ms}, separators=(",", ":"))
                self.wallet.faucet_last_claim = faucet_last_claim
                update_wallet_info(
                    address=self.wallet.address,
                    name_column="faucet_last_claim",
                    data=faucet_last_claim,
                )

            else:
                logger.error(f"{self.wallet} | Faucet response did not match any known substrings; raw text (trimmed): {response.text[:600]}")
                return False

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

        try:
            logger.info(f"{self.wallet} | Sending faucet event POST to {self.BASE_URL}/events")

            event_headers = {
                "accept": "application/json, text/plain, */*",
                "authorization": f"Bearer {self.wallet.identity_token}",
                "content-type": "application/json",
                "origin": "https://neuraverse.neuraprotocol.io",
                "referer": "https://neuraverse.neuraprotocol.io/",
            }

            event_response = await self.session.post(
                url=f"{self.BASE_URL}/events", cookies=self.privy.cookies, headers=event_headers, json={"type": "faucet:claimTokens"}
            )

            if event_response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 faucet event response ({event_response.status_code}). Body: {event_response.text}")
                raise RuntimeError(f"Non-200 faucet event response ({event_response.status_code})")

            logger.success(f"[{self.wallet}] | Faucet event sent successfully")

            return True

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return True

    async def get_validators(self) -> list:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        try:
            logger.debug(f"{self.wallet} | Requesting validators list")

            response = await self.session.get(
                url=f"{self.BASE_URL}/game/validators",
                headers=self.headers,
            )

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                raise RuntimeError(f"Non-200 response ({response.status_code})")

            all_validator_info = response.json().get("validators", [])

            if not all_validator_info:
                raise ValueError(f"Invalid validators response: {response.text}")

            logger.debug(f"{self.wallet} | Validators list fetched successfully - {all_validator_info}")

            return all_validator_info

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return []

    async def chat(self, payload: dict, validator_id: str) -> list:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        try:
            logger.debug(f"{self.wallet} | Sending chat request to validator {validator_id}")

            response = await self.session.post(url=f"{self.BASE_URL}/game/chat/validator/{validator_id}", headers=self.headers, json=payload)

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                raise RuntimeError(f"Non-200 response ({response.status_code})")

            messages_all = response.json().get("messages", [])

            content_messages = [message.get("content") for message in messages_all if "content" in message]

            if not content_messages:
                raise ValueError(f"Invalid account info response: {response.text}")

            logger.debug(f"{self.wallet} | Chat response received successfully - {content_messages}")

            return content_messages

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return []

    async def get_claim_tokens_on_sepolia(self) -> list:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        try:
            logger.debug(f"{self.wallet} | Fetching claim list...")

            response = await self.session.get(
                url=f"https://neuraverse-testnet.infra.neuraprotocol.io/api/claim-tx?recipient={self.wallet.address.lower()}&page=1&limit=20",
                headers=self.headers,
            )

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                raise RuntimeError(f"Non-200 response ({response.status_code})")

            transactions = response.json().get("transactions", [])

            logger.debug(f"{self.wallet} | Claim transactions fetched successfully: {len(transactions)} items")
            return transactions

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return []

    async def get_twitter_link(self) -> str:
        # Not working yet
        return ""

        if not self.privy.authentication:
            await self.privy.privy_authorize()

        code_verifier = base64.urlsafe_b64encode(os.urandom(36)).decode().rstrip("=")
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")
        state_code = base64.urlsafe_b64encode(os.urandom(36)).decode().rstrip("=")

        logger.debug(f"{self.wallet} | Twitter PKCE generated | challenge={code_challenge}, state={state_code}")

        payload = {
            "provider": "twitter",
            "redirect_to": "https://neuraverse.neuraprotocol.io/",
            "code_challenge": code_challenge,
            "state_code": state_code,
        }

        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "ru,en;q=0.9",
            "content-type": "application/json",
            "priority": "u=1, i",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "authorization": "Bearer eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Il9wWWZSYzMtSFJneE4xY1NYSThrOEVBdFgweXZOSUVnYXMtUHFPbHFMRk0ifQ.eyJzaWQiOiJjbWh2bHd6cHIwMDB2bGIwZGRnMnN1ZXU3IiwiaXNzIjoicHJpdnkuaW8iLCJpYXQiOjE3NjMwMTg5MTcsImF1ZCI6ImNtYnBlbXB6MjAxMWxsMTBsN2l1Y2dhMTQiLCJzdWIiOiJkaWQ6cHJpdnk6Y21ob3YyamE0MDE1M2xnMGNycXUweGZsaSIsImV4cCI6MTc2MzEwNTMxN30.h2aG5Q3E7WTvLcI9_MQh8qTni-wZnVaEr6RV3VNsm_t15loBL9LJkNf5G7MDpqFV5ZMOQxT1admMq0lVssS36g",
            "privy-app-id": "cmbpempz2011ll10l7iucga14",
            "privy-ca-id": "c787a08d-383c-4d26-b082-42510f2505d5",
            "privy-client": "react-auth:2.25.0",
            "origin": "https://neuraverse.neuraprotocol.io",
            "referer": "https://neuraverse.neuraprotocol.io/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 YaBrowser/25.8.0.0 Safari/537.36",
        }

        cookies = {
            "privy-session": "privy.neuraprotocol.io",
            "privy-token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Il9wWWZSYzMtSFJneE4xY1NYSThrOEVBdFgweXZOSUVnYXMtUHFPbHFMRk0ifQ.eyJzaWQiOiJjbWh2bHd6cHIwMDB2bGIwZGRnMnN1ZXU3IiwiaXNzIjoicHJpdnkuaW8iLCJpYXQiOjE3NjMwMTg5MTcsImF1ZCI6ImNtYnBlbXB6MjAxMWxsMTBsN2l1Y2dhMTQiLCJzdWIiOiJkaWQ6cHJpdnk6Y21ob3YyamE0MDE1M2xnMGNycXUweGZsaSIsImV4cCI6MTc2MzEwNTMxN30.h2aG5Q3E7WTvLcI9_MQh8qTni-wZnVaEr6RV3VNsm_t15loBL9LJkNf5G7MDpqFV5ZMOQxT1admMq0lVssS36g",
            "privy-access-token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Il9wWWZSYzMtSFJneE4xY1NYSThrOEVBdFgweXZOSUVnYXMtUHFPbHFMRk0ifQ.eyJhaWQiOiJjbWJwZW1wejIwMTFsbDEwbDdpdWNnYTE0IiwiYXR0IjoicGF0Iiwic2lkIjoiY21odmx3enByMDAwdmxiMGRkZzJzdWV1NyIsImlzcyI6InByaXZ5LmlvIiwiaWF0IjoxNzYzMDE4OTE3LCJhdWQiOiJwcml2eS5uZXVyYXByb3RvY29sLmlvIiwic3ViIjoiZGlkOnByaXZ5OmNtaG92MmphNDAxNTNsZzBjcnF1MHhmbGkiLCJleHAiOjE3NjMxMDUzMTd9.yIeXOMvQSBImHWWi3pxzBhpdTIJhN1ojlJ3WmzoGG2iu452y1NQVwwboQ2CKrnNP6Y5kip-EM5hj9-l8avw2ZA",
            "privy-refresh-token": "owM32zSMrkT-EjF8mdPUBV6OqwRR-VyXR8Dzfuy-H0KlnGEW5dfs4GnbMo_1mXbUqdnMP5j0Z4KF9eGIPexF8w",
            "privy-id-token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Il9wWWZSYzMtSFJneE4xY1NYSThrOEVBdFgweXZOSUVnYXMtUHFPbHFMRk0ifQ.eyJjciI6IjE3NjI1MjAyODQiLCJsaW5rZWRfYWNjb3VudHMiOiJbe1widHlwZVwiOlwid2FsbGV0XCIsXCJhZGRyZXNzXCI6XCIweDVFNTEzNjJhQjA2M0IwN2U3ZmE0OEZmZmFiZjMzN2E1ZTY1YkM1NjlcIixcImNoYWluX3R5cGVcIjpcImV0aGVyZXVtXCIsXCJ3YWxsZXRfY2xpZW50X3R5cGVcIjpcIm1ldGFtYXNrXCIsXCJsdlwiOjE3NjMwMzQ4Mzd9LHtcImlkXCI6XCJmcm16ZGYya29ieHM4YWJ6aDl2aTlkeGxcIixcInR5cGVcIjpcIndhbGxldFwiLFwiYWRkcmVzc1wiOlwiMHg1NTU0QkM5YjQzMWI5NjY0NjFGNTcxZmJDMTFmOEZmNTkyMTk2OTRmXCIsXCJjaGFpbl90eXBlXCI6XCJldGhlcmV1bVwiLFwid2FsbGV0X2NsaWVudF90eXBlXCI6XCJwcml2eVwiLFwibHZcIjoxNzYyNTIwMjkwfV0iLCJpc3MiOiJwcml2eS5pbyIsImlhdCI6MTc2MzAzNjI4NiwiYXVkIjoiY21icGVtcHoyMDExbGwxMGw3aXVjZ2ExNCIsInN1YiI6ImRpZDpwcml2eTpjbWhvdjJqYTQwMTUzbGcwY3JxdTB4ZmxpIiwiZXhwIjoxNzYzMTIyNjg2fQ.liOJAkcHrJ_SN0UQk05TljtLpAu8uZ0oCZkqyiuN4sRCrfmyU4hnpJ2H1kNS6kytyPBGYVhwxGQRf-ZSEEs2bw",
        }

        logger.debug(f"{self.wallet} | Twitter OAuth init request -> url=https://privy.neuraprotocol.io/api/v1/oauth/init")
        logger.debug(f"{self.wallet} | Twitter OAuth init headers: {headers}")
        logger.debug(f"{self.wallet} | Twitter OAuth init cookies keys: {list(cookies.keys())}")

        response = await self.session.post(
            url="https://privy.neuraprotocol.io/api/v1/oauth/init",
            cookies=cookies,
            headers=headers,
            json=payload,
        )

        logger.debug(f"{self.wallet} | Twitter OAuth init response status: {response.status_code}")
        logger.debug(f"{self.wallet} | Twitter OAuth init response text (trimmed): {response.text}")

        if response.status_code != 200:
            logger.error(f"{self.wallet} | OAuth init failed ({response.status_code}). Body: {response.text}")
            raise RuntimeError(f"OAuth init failed ({response.status_code})")

        data = response.json()
        logger.debug(f"{self.wallet} | OAuth init response: {data}")

        auth_url = data.get("url")

        if not auth_url:
            raise ValueError(f"Unable to find authorization URL in response: {data}")

        return auth_url

    async def bind_twitter(self, callback: TwitterOauthData) -> bool:
        # Not working yet
        return False

        if not self.privy.authentication:
            await self.privy.privy_authorize()

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "ru,en;q=0.9",
            "priority": "u=0, i",
            "referer": "https://x.com/",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "YaBrowser";v="25.8", "Yowser";v="2.5"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "cross-site",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 YaBrowser/25.8.0.0 Safari/537.36",
        }

        logger.debug(f"{self.wallet} | Privy callback URL to call (no redirects): {callback.callback_url}")

        response = await self.session.get(
            url=callback.callback_url,
            headers=headers,
            allow_redirects=False,
        )

        logger.debug(f"{self.wallet} | First Privy callback response status: {response.status_code}")
        logger.debug(f"{self.wallet} | First Privy callback text: {response.text}")

        location = response.headers.get("location")

        logger.debug(f"{self.wallet} | First Privy callback Location header: {location}")

        if not location:
            logger.error(f"{self.wallet} | No Location header in Privy callback response, cannot continue Twitter bind")
            return False

        cookies = {
            "faucet_last_claim": '{"timestamp":1762789097408}',
            "privy-session": "privy.neuraprotocol.io",
            "privy-token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Il9wWWZSYzMtSFJneE4xY1NYSThrOEVBdFgweXZOSUVnYXMtUHFPbHFMRk0ifQ.eyJzaWQiOiJjbWh2bHd6cHIwMDB2bGIwZGRnMnN1ZXU3IiwiaXNzIjoicHJpdnkuaW8iLCJpYXQiOjE3NjMwMTg5MTcsImF1ZCI6ImNtYnBlbXB6MjAxMWxsMTBsN2l1Y2dhMTQiLCJzdWIiOiJkaWQ6cHJpdnk6Y21ob3YyamE0MDE1M2xnMGNycXUweGZsaSIsImV4cCI6MTc2MzEwNTMxN30.h2aG5Q3E7WTvLcI9_MQh8qTni-wZnVaEr6RV5VNsm_t15loBL9LJkNf5G7MDpqFV5ZMOQxT1admMq0lVssS36g",
            "privy-id-token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Il9wWWZSYzMtSFJneE4xY1NYSThrOEVBdFgweXZOSUVnYXMtUHFPbHFMRk0ifQ.eyJjciI6IjE3NjI1MjAyODQiLCJsaW5rZWRfYWNjb3VudHMiOiJbe1widHlwZVwiOlwid2FsbGV0XCIsXCJhZGRyZXNzXCI6XCIweDVFNTEzNjJhQjA2M0IwN2U3ZmE0OEZmZmFiZjMzN2E1ZTY1YkM1NjlcIixcImNoYWluX3R5cGVcIjpcImV0aGVyZXVtXCIsXCJ3YWxsZXRfY2xpZW50X3R5cGVcIjpcIm1ldGFtYXNrXCIsXCJsdlwiOjE3NjMwMzQ4Mzd9LHtcImlkXCI6XCJmcm16ZGYya29ieHM4YWJ6aDl2aTlkeGxcIixcInR5cGVcIjpcIndhbGxldFwiLFwiYWRkcmVzc1wiOlwiMHg1NTU0QkM5YjQzMWI5NjY0NjFGNTcxZmJDMTFmOEZmNTkyMTk2OTRmXCIsXCJjaGFpbl90eXBlXCI6XCJldGhlcmV1bVwiLFwid2FsbGV0X2NsaWVudF90eXBlXCI6XCJwcml2eVwiLFwibHZcIjoxNzYyNTIwMjkwfV0iLCJpc3MiOiJwcml2eS5pbyIsImlhdCI6MTc2MzA0MDQ1OCwiYXVkIjoiY21icGVtcHoyMDExbGwxMGw3aXVjZ2ExNCIsInN1YiI6ImRpZDpwcml2eTpjbWhvdjJqYTQwMTUzbGcwY3JxdTB4ZmxpIiwiZXhwIjoxNzYzMTI2ODU4fQ.eTvhU2HqMo3KRHbf_bJB2_4LaxM0da25rtOZGuGj20npgZzkv4WlS5G8P92YUDszuuxoWHgXSauz17LzPuyaDA",
        }

        logger.info(f"{self.wallet} | Calling Neuraverse redirect URL from Location...")
        response = await self.session.get(
            url=location,
            cookies=cookies,
            headers=headers,
        )

        logger.debug(f"{self.wallet} | Neuraverse redirect response status: {response.status_code}")

        if response.status_code in (200, 301, 302):
            logger.debug(f"{self.wallet} | Neuraverse/Twitter bind flow completed (browser-like redirect sequence)")
            return True

        raise Exception(f"Unexpected status from Neuraverse redirect: {response.status_code}")
