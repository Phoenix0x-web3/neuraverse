import re
import uuid
from datetime import datetime, timezone
from typing import Dict
from urllib.parse import urlparse

from eth_account.messages import encode_defunct
from loguru import logger

from data.constants import DEFAULT_HEADERS
from libs.eth_async.client import Client
from utils.browser import Browser
from utils.captcha.captcha_handler import CaptchaHandler
from utils.db_api.models import Wallet
from utils.db_api.wallet_api import update_wallet_info


class PrivyAuth:
    __module__ = "Privy authentication"
    BASE_URL = "https://privy.neuraprotocol.io/api/v1"

    def __init__(self, client: Client, wallet: Wallet):
        self.client = client
        self.wallet = wallet
        self.session = Browser()
        self.authentication = False
        self.token_id = self.resolve_privy_ca_id()

        self.headers = {
            **DEFAULT_HEADERS,
            "privy-app-id": "cmbpempz2011ll10l7iucga14",
            "privy-ca-id": self.token_id,
            "privy-client": "react-auth:2.25.0",
        }

    def __repr__(self):
        return f"{self.__module__} | [{self.wallet.address}]"

    @property
    def cookies(self) -> dict:
        return {k: v for k, v in (self.wallet.cookies or {}).items() if k in {"privy-token", "privy-id-token", "privy-session"}}

    async def privy_authorize(self) -> bool:
        if self.cookies:
            try:
                logger.info(f"{self.wallet} | Trying refresh via cookie")
                if await self.refresh_session_via_cookie():
                    self.authentication = True
                    logger.success(f"{self.wallet} | Refresh via cookie: OK (session_token & identity_token & cookies updated)")
                    return True
                else:
                    logger.warning(f"{self.wallet} | Refresh via cookie failed → fallback to full SIWE")

            except Exception as e:
                logger.warning(f"{self.wallet} | Failed to refresh session via cookies — {e}")

        try:
            logger.info(f"{self.wallet} | Getting new session_token via SIWE...")

            if await self.authenticate_via_siwe():
                self.authentication = True
                logger.success(f"{self.wallet} | SIWE: OK (session_token & identity_token & cookies saved)")
                return True
            else:
                logger.error(f"{self.wallet} | SIWE failed: session_token, identity_token or cookies missing")
                return False

        except Exception as e:
            logger.error(f"{self.wallet} | SIWE exception: {e}")
            return False

    async def refresh_session_via_cookie(self) -> bool:
        cookies = {
            k: v
            for k, v in (self.wallet.cookies or {}).items()
            if k in {"privy-token", "privy-id-token", "privy-ssesion", "privy-refresh-token", "privy-access-token"}
        }

        payload = {"refresh_token": "deprecated"}

        if self.wallet.identity_token:
            headers = {**self.headers, "authorization": f"Bearer {self.wallet.identity_token}"}
        else:
            headers = self.headers

        try:
            response = await self.session.post(url=f"{self.BASE_URL}/sessions", cookies=cookies, headers=headers, json=payload)

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                return False

        except Exception as e:
            logger.error(f"{self.wallet} | Request failed — {e}")
            return False

        try:
            session_token = response.json().get("token")
            identity_token = response.json().get("identity_token")

            raw_set_cookie = response.headers.get("set-cookie")
            cookie_header = self.extract_privy_tokens(raw_set_cookie)

            if not (session_token and identity_token and cookie_header):
                logger.error(
                    f"{self.wallet} | SIWE: FAILED (session_token={bool(session_token)},"
                    f"identity_token={bool(identity_token)}, cookie={bool(cookie_header)})"
                )
                raise ValueError("SIWE authentication failed: missing required tokens (session_token, identity_token, or cookies)")

            update_wallet_info(address=self.wallet.address, name_column="session_token", data=session_token)
            update_wallet_info(address=self.wallet.address, name_column="identity_token", data=identity_token)
            update_wallet_info(address=self.wallet.address, name_column="cookies", data=cookie_header)

            self.wallet.session_token = session_token
            self.wallet.identity_token = identity_token
            self.wallet.cookies = cookie_header

        except Exception as e:
            logger.error(f"{self.wallet} | Failed to parse response or extract tokens — {e}")
            return False

        return True

    async def authenticate_via_siwe(self) -> bool:
        try:
            nonce = await self.get_nonce()
            logger.debug(f"{self.wallet} | Nonce obtained: {nonce[:8] + '...' if nonce else 'None'}")

            if not nonce:
                logger.error(f"{self.wallet} | No nonce found in /siwe/init response")
                raise ValueError("SIWE authentication failed: nonce is missing")

        except Exception as e:
            logger.error(f"{self.wallet} | Failed to obtain nonce — {e}")
            return False

        message = self.siwe_message(nonce=nonce)
        signature = self.client.account.sign_message(signable_message=encode_defunct(text=message))

        payload = {
            "message": message,
            "signature": signature.signature.hex(),
            "chainId": "eip155:267",
            "walletClientType": "metamask",
            "connectorType": "injected",
            "mode": "login-or-sign-up",
        }

        try:
            response = await self.session.post(url=f"{self.BASE_URL}/siwe/authenticate", headers=self.headers, json=payload)

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                return False

            session_token = response.json().get("token")
            identity_token = response.json().get("identity_token")

            raw_set_cookie = response.headers.get("set-cookie")
            cookie_header = self.extract_privy_tokens(raw_set_cookie)

            if not (session_token and identity_token and cookie_header):
                logger.error(
                    f"{self.wallet} | SIWE: FAILED (session_token={bool(session_token)},"
                    f"identity_token={bool(identity_token)}, cookie={bool(cookie_header)})"
                )
                raise ValueError("SIWE authentication failed: missing required tokens (session_token, identity_token, or cookies)")

            update_wallet_info(address=self.wallet.address, name_column="session_token", data=session_token)
            update_wallet_info(address=self.wallet.address, name_column="identity_token", data=identity_token)
            update_wallet_info(address=self.wallet.address, name_column="cookies", data=cookie_header)

            self.wallet.session_token = session_token
            self.wallet.identity_token = identity_token
            self.wallet.cookies = cookie_header

        except Exception as e:
            logger.error(f"{self.wallet} | Failed to complete SIWE authentication — {e}")
            return False

        try:
            analytics_events = await self.send_analytics_events(is_new_user=response.json().get("is_new_user", False))

            if analytics_events:
                return True
            else:
                logger.error(f"{self.wallet} | Analytics events failed — cannot continue SIWE authentication")
                raise Exception("SIWE authentication aborted: analytics events could not be sent")

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

    async def get_nonce(self) -> str:
        try:
            captcha_handler = CaptchaHandler(wallet=self.wallet)
            captcha_raw = await captcha_handler.cloudflare_token(
                websiteURL="https://neuraverse.neuraprotocol.io/",
                websiteKey="0x4AAAAAAAM8ceq5KhP1uJBt",
            )

            if isinstance(captcha_raw, dict):
                captcha_token = captcha_raw.get("token")
            else:
                captcha_token = captcha_raw

            if not captcha_token:
                raise ValueError("Сaptcha token missing")

        except Exception as e:
            logger.error(f"{self.wallet} | Failed to obtain captcha token — {e}")
            raise ValueError("Captcha validation failed: token is missing")

        payload = {
            "address": self.wallet.address,
            "token": captcha_token,
        }

        try:
            response = await self.session.post(url=f"{self.BASE_URL}/siwe/init", headers=self.headers, json=payload)

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                return ""

            nonce = response.json().get("nonce")

            if not nonce:
                logger.error(f"{self.wallet} | Nonce missing in response body")
                raise ValueError("Nonce missing in response")

        except Exception as e:
            logger.error(f"{self.wallet} | get_nonce(): request/parse error — {e}")
            raise RuntimeError("get_nonce(): failed to obtain nonce")

        return nonce

    async def send_analytics_events(self, is_new_user: bool) -> bool:
        try:
            cookies = {
                k: v
                for k, v in (self.wallet.cookies or {}).items()
                if k in {"privy-token", "privy-id-token", "privy-ssesion", "privy-refresh-token", "privy-access-token"}
            }

            logger.debug(f"{self.cookies}")
            logger.debug(f"{cookies}")

            headers = {
                **self.headers,
                "authorization": f"Bearer {self.wallet.identity_token}",
            }

            utc_time_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

            payload = {
                "event_name": "sdk_authenticate_siwe",
                "client_id": self.token_id,
                "payload": {
                    "connectorType": "injected",
                    "walletClientType": "metamask",
                    "clientTimestamp": utc_time_now,
                },
            }

            response = await self.session.post(
                url=f"{self.BASE_URL}/analytics_events",
                cookies=cookies,
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                return False

        except Exception as e:
            logger.error(f"{self.wallet} | Analytics event processing failed — {e}")
            raise RuntimeError("Analytics event processing failed")

        try:
            payload = {
                "event_name": "sdk_authenticate",
                "client_id": self.token_id,
                "payload": {
                    "method": "siwe",
                    "isNewUser": is_new_user,
                    "clientTimestamp": utc_time_now,
                },
            }

            response = await self.session.post(
                url=f"{self.BASE_URL}/analytics_events",
                cookies=cookies,
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                return False

        except Exception as e:
            logger.error(f"{self.wallet} | Analytics event processing failed — {e}")
            raise RuntimeError("Analytics event processing failed")

        return True

    def siwe_message(self, nonce: str) -> str:
        issued_at = datetime.utcnow().isoformat() + "Z"

        return (
            "neuraverse.neuraprotocol.io wants you to sign in with your Ethereum account:\n"
            f"{self.wallet.address}\n\n"
            "By signing, you are proving you own this wallet and logging in. "
            "This does not initiate a transaction or cost any fees.\n\n"
            "URI: https://neuraverse.neuraprotocol.io\n"
            "Version: 1\n"
            "Chain ID: 267\n"
            f"Nonce: {nonce}\n"
            f"Issued At: {issued_at}\n"
            "Resources:\n"
            "- https://privy.io"
        )

    def resolve_privy_ca_id(self) -> str:
        wallet_addr = (self.wallet.address or "").lower()
        proxy_raw = self.wallet.proxy or ""
        proxy_norm = self.normalize_proxy(proxy_raw)
        seed = f"{wallet_addr}|{proxy_norm}" if proxy_norm else wallet_addr
        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))

    def normalize_proxy(self, proxy: str) -> str:
        if not proxy:
            return ""
        try:
            p = urlparse(proxy if "://" in proxy else f"http://{proxy}")
            host = p.hostname or ""
            port = p.port
            if not host or not port:
                return ""
            return f"{host}:{port}"
        except Exception:
            return ""

    def extract_privy_tokens(self, set_cookie: str) -> Dict[str, str]:
        wanted = {"privy-token", "privy-id-token", "privy-refresh-token", "privy-access-token"}
        result = {}

        if not set_cookie:
            return result

        for m in re.finditer(r"(?P<name>[^=;,\s]+)=(?P<value>[^;\r\n,]+)", set_cookie):
            name = m.group("name").strip()
            value = m.group("value").strip()

            if name in wanted:
                result[name] = value

        result["privy-session"] = "privy.neuraprotocol.io"

        return result
