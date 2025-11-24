import base64
import hashlib
import json
import os
import re
import time
from urllib.parse import parse_qs, urlparse

from loguru import logger

from data.constants import DEFAULT_HEADERS
from libs.eth_async.client import Client
from modules.privy_authentication import PrivyAuth
from utils.browser import Browser
from utils.captcha.captcha_handler import CaptchaHandler
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

    def __repr__(self):
        return f"{self.__module__} | [{self.wallet.address}]"

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
                return {}

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
                return {}

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
                return []

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
                return False

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
                return False

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
                return False

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

            headers = {"Referer": "https://neuraverse.neuraprotocol.io/?section=faucet"}

            response = await self.session.get(url="https://neuraverse.neuraprotocol.io/_next/static/chunks/3160-c1da923f868648d0.js", headers=headers)
            logger.debug(f"{self.wallet} | Faucet JS chunk status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 JS chunk response in faucet ({response.status_code}). Body: {response.text}")
                return False

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

            captcha_handler = CaptchaHandler(wallet=self.wallet)
            captcha_raw = await captcha_handler.cloudflare_token(
                websiteURL="https://neuraverse.neuraprotocol.io/?section=faucet",
                websiteKey="0x4AAAAAACAe7c3f7wATdkJe",
            )

            if isinstance(captcha_raw, dict):
                captcha_token = captcha_raw.get("token")
            else:
                captcha_token = captcha_raw

            if not captcha_token:
                raise ValueError("Сaptcha token missing")

            faucet_nonce = None
            try:
                logger.debug(f"{self.wallet} | Fetching faucet nonce from RSC payload")

                rsc_headers = {
                    "accept": "text/x-component",
                    "next-router-state-tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%2Cnull%2Cnull%5D%7D%2Cnull%2Cnull%2Ctrue%5D",
                    "origin": "https://neuraverse.neuraprotocol.io",
                    "priority": "u=1, i",
                    "referer": "https://neuraverse.neuraprotocol.io/?section=faucet",
                }

                rsc_response = await self.session.get(
                    url="https://neuraverse.neuraprotocol.io/?section=faucet",
                    cookies=cookie,
                    headers=rsc_headers,
                )

                logger.debug(f"{self.wallet} | Faucet RSC nonce fetch status: {rsc_response.status_code}")

                if rsc_response.status_code != 200:
                    logger.error(
                        f"{self.wallet} | Non-200 faucet RSC response while fetching nonce ({rsc_response.status_code}). Body: {rsc_response.text}"
                    )
                else:
                    text = rsc_response.text
                    # Try to find a UUID-like nonce near the "initialFaucetNonce" key inside the RSC payload
                    nonce_match = re.search(
                        r"initialFaucetNonce[^0-9a-fA-F]{0,300}([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
                        text,
                    )
                    if nonce_match:
                        faucet_nonce = nonce_match.group(1)
                    else:
                        logger.error(f"{self.wallet} | Failed to extract faucet nonce from RSC payload")
            except Exception as e:
                logger.error(f"{self.wallet} | Error while fetching faucet nonce — {e}")

            if not faucet_nonce:
                logger.error(f"{self.wallet} | Faucet nonce is missing after RSC fetch, aborting claim")
                return False

            data = json.dumps(
                [
                    self.client.account.address,
                    267,
                    self.wallet.identity_token,
                    True,
                    captcha_token,
                    faucet_nonce,
                ],
                separators=(",", ":"),
            )

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
                return False

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
                logger.error(f"{self.wallet} | Faucet response did not match any known substrings: {response.text[:600]}")
                return False

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

        try:
            logger.info(f"{self.wallet} | Sending faucet event")

            event_response = await self.session.post(
                url=f"{self.BASE_URL}/events", cookies=self.privy.cookies, headers=self.headers, json={"type": "faucet:claimTokens"}
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
                return []

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
                return []

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
                return []

            transactions = response.json().get("transactions", [])

            logger.debug(f"{self.wallet} | Claim transactions fetched successfully: {len(transactions)} items")
            return transactions

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return []

    async def get_twitter_link(self) -> tuple:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        try:
            logger.debug(f"{self.wallet} | Starting Twitter OAuth init flow")

            code_verifier = base64.urlsafe_b64encode(os.urandom(36)).decode().rstrip("=")
            code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")
            state_code = base64.urlsafe_b64encode(os.urandom(36)).decode().rstrip("=")

            headers = {
                **self.headers,
                "privy-app-id": "cmbpempz2011ll10l7iucga14",
                "privy-ca-id": self.privy.token_id,
                "privy-client": "react-auth:2.25.0",
                "privy-ui": "t",
            }

            payload = {
                "provider": "twitter",
                "redirect_to": "https://neuraverse.neuraprotocol.io/",
                "code_challenge": code_challenge,
                "state_code": state_code,
            }

            cookies = {
                k: v for k, v in (self.wallet.cookies or {}).items() if k in {"privy-token", "privy-id-token", "privy-session", "privy-access-token"}
            }

            response = await self.session.post(
                url="https://privy.neuraprotocol.io/api/v1/oauth/init",
                cookies=cookies,
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                logger.error(f"{self.wallet} | OAuth init failed ({response.status_code}). Body: {response.text}")
                return ()

            data = response.json()
            auth_url = data.get("url")

            logger.debug(f"{self.wallet} | Twitter OAuth init parsed URL: {auth_url}")

            if not auth_url:
                return ()

            return auth_url, code_verifier

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return ()

    async def bind_twitter(self, callback: TwitterOauthData, code_verifier: str) -> bool:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        try:
            headers = {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept-language": "ru,en;q=0.9",
                "priority": "u=0, i",
                "referer": "https://x.com/",
            }

            response = await self.session.get(
                url=callback.callback_url,
                headers=headers,
                allow_redirects=False,
            )

            if response.status_code != 307:
                logger.error(f"{self.wallet} | OAuth init failed ({response.status_code}). Body: {response.text}")
                return False

            location = response.headers.get("location")

            if not location:
                logger.error(f"{self.wallet} | No Location header in Privy callback response, cannot continue Twitter bind")
                return False

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

        try:
            headers = {
                **self.headers,
                "privy-app-id": "cmbpempz2011ll10l7iucga14",
                "privy-ca-id": self.privy.token_id,
                "privy-client": "react-auth:2.25.0",
            }

            cookies = {
                k: v
                for k, v in (self.wallet.cookies or {}).items()
                if k in {"privy-token", "privy-id-token", "privy-session", "privy-access-token", "privy-refresh-token"}
            }

            parsed = urlparse(location)
            params = parse_qs(parsed.query)

            authorization_code = params.get("privy_oauth_code", [None])[0]
            state_code = params.get("privy_oauth_state", [None])[0]

            if not authorization_code or not state_code:
                logger.error(f"{self.wallet} | Missing privy_oauth_code/state in callback URL")
                return False

            payload = {
                "authorization_code": authorization_code,
                "state_code": state_code,
                "code_verifier": code_verifier,
            }

            response = await self.session.post(url="https://privy.neuraprotocol.io/api/v1/oauth/link", cookies=cookies, headers=headers, json=payload)

            if response.status_code != 200:
                logger.error(f"{self.wallet} | OAuth init failed ({response.status_code}). Body: {response.text}")
                return False

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

        try:
            await self.privy.privy_authorize()

            headers = {k: v for k, v in self.headers.items() if k.lower() != "content-type"}

            sync_response = await self.session.post(
                url=f"{self.BASE_URL}/account/social/sync",
                cookies=self.privy.cookies,
                headers=headers,
            )

            if sync_response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 social sync response ({sync_response.status_code}). Body: {sync_response.text}")
                raise RuntimeError(f"Non-200 social sync response ({sync_response.status_code})")

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

        return True

    async def get_discord_link(self) -> tuple:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        try:
            logger.debug(f"{self.wallet} | Starting Discord OAuth init flow")

            code_verifier = base64.urlsafe_b64encode(os.urandom(36)).decode().rstrip("=")
            code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")
            state_code = base64.urlsafe_b64encode(os.urandom(36)).decode().rstrip("=")

            headers = {
                **self.headers,
                "privy-app-id": "cmbpempz2011ll10l7iucga14",
                "privy-ca-id": self.privy.token_id,
                "privy-client": "react-auth:2.25.0",
                "privy-ui": "t",
            }

            payload = {
                "provider": "discord",
                "redirect_to": "https://neuraverse.neuraprotocol.io/",
                "code_challenge": code_challenge,
                "state_code": state_code,
            }

            cookies = {
                k: v for k, v in (self.wallet.cookies or {}).items() if k in {"privy-token", "privy-id-token", "privy-session", "privy-access-token"}
            }

            response = await self.session.post(
                url="https://privy.neuraprotocol.io/api/v1/oauth/init",
                cookies=cookies,
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                logger.error(f"{self.wallet} | OAuth init failed ({response.status_code}). Body: {response.text}")
                return ()

            data = response.json()
            auth_url = data.get("url")

            logger.debug(f"{self.wallet} | Twitter OAuth init parsed URL: {auth_url}")

            if not auth_url:
                return ()

            return auth_url, code_verifier

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return ()

    async def bind_discord(self, callback: str, code_verifier: str) -> bool:
        if not self.privy.authentication:
            await self.privy.privy_authorize()

        try:
            headers = {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "priority": "u=0, i",
                "referer": "https://x.com/",
            }

            response = await self.session.get(
                url=callback,
                headers=headers,
                allow_redirects=False,
            )

            if response.status_code != 307:
                logger.error(f"{self.wallet} | OAuth init failed ({response.status_code}). Body: {response.text}")
                return False

            location = response.headers.get("location")

            if not location:
                logger.error(f"{self.wallet} | No Location header in Privy callback response, cannot continue Twitter bind")
                return False

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

        try:
            headers = {
                **self.headers,
                "privy-app-id": "cmbpempz2011ll10l7iucga14",
                "privy-ca-id": self.privy.token_id,
                "privy-client": "react-auth:2.25.0",
            }

            cookies = {
                k: v
                for k, v in (self.wallet.cookies or {}).items()
                if k in {"privy-token", "privy-id-token", "privy-session", "privy-access-token", "privy-refresh-token"}
            }

            parsed = urlparse(location)
            params = parse_qs(parsed.query)

            authorization_code = params.get("privy_oauth_code", [None])[0]
            state_code = params.get("privy_oauth_state", [None])[0]

            if not authorization_code or not state_code:
                logger.error(f"{self.wallet} | Missing privy_oauth_code/state in callback URL")
                return False

            payload = {
                "authorization_code": authorization_code,
                "state_code": state_code,
                "code_verifier": code_verifier,
            }

            response = await self.session.post(url="https://privy.neuraprotocol.io/api/v1/oauth/link", cookies=cookies, headers=headers, json=payload)

            if response.status_code != 200:
                logger.error(f"{self.wallet} | OAuth init failed ({response.status_code}). Body: {response.text}")
                return False

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

        try:
            await self.privy.privy_authorize()

            headers = {k: v for k, v in self.headers.items() if k.lower() != "content-type"}

            sync_response = await self.session.post(
                url=f"{self.BASE_URL}/account/social/sync",
                cookies=self.privy.cookies,
                headers=headers,
            )

            if sync_response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 social sync response ({sync_response.status_code}). Body: {sync_response.text}")
                raise RuntimeError(f"Non-200 social sync response ({sync_response.status_code})")

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

        return True
