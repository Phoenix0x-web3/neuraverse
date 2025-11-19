import asyncio
import math
import random

from loguru import logger
from web3.types import TxParams

from data.models import Contracts
from data.settings import Settings
from libs.base import Base
from libs.eth_async.client import Client
from libs.eth_async.data.models import Networks, TokenAmount, TxArgs
from libs.eth_async.utils.utils import randfloat, wait_for_acceptable_gas_price
from utils.browser import Browser
from utils.db_api.models import Wallet


class Bridge(Base):
    __module__ = "Bridge Neura to Sepolia"

    def __init__(self, client: Client, wallet: Wallet, client_sepolia: Client = Client(network=Networks.NeuraTestnet)):
        self.client = client
        self.client_sepolia = client_sepolia
        self.wallet = wallet
        self.settings = Settings()
        self.session = Browser()

    def __repr__(self):
        return f"{self.__module__} | [{self.wallet.address}]"

    async def bridge_neura_to_sepolia(self, amount_eth: TokenAmount, check_gas_price: bool = True) -> bool:
        try:
            logger.debug(f"{self.wallet} | Bridging {amount_eth.Ether} ANKR from Neura → Sepolia...")

            if amount_eth.Ether <= 0:
                raise Exception(f"Invalid amount: {amount_eth.Ether}")

            if check_gas_price and not await wait_for_acceptable_gas_price(client=self.client, wallet=self.wallet):
                return False

            bridge_contract = await self.client.contracts.get(Contracts.NEURA_BRIDGE)

            tx_params = TxArgs(_recipient=self.client.account.address, _chainId=Networks.Sepolia.chain_id).tuple()

            data = bridge_contract.encode_abi("deposit", args=tx_params)

            transaction = await self.client.transactions.sign_and_send(TxParams(to=bridge_contract.address, data=data, value=amount_eth.Wei))
            recipient = await transaction.wait_for_receipt(client=self.client, timeout=300)

            if recipient["status"] != 1:
                logger.error(f"{self.wallet} | Bridge transaction reverted on-chain")
                raise Exception("Bridge tx reverted on-chain")

            logger.debug(f"{self.wallet} | Bridge Neura → Sepolia completed")
            return True

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

    async def claim_token_on_sepolia(self, encoded_message, signatures_bytes) -> bool:
        try:
            logger.debug(f"{self.wallet} | Claiming bridged tokens on Sepolia…")

            bridge_contract = await self.client_sepolia.contracts.get(Contracts.SEPOLIA_BRIDGE)

            tx_params = TxArgs(encodedMessage=encoded_message, messageSignatures=signatures_bytes)

            data = bridge_contract.encode_abi("claim", args=tx_params)

            transaction = await self.client.transactions.sign_and_send(TxParams(to=bridge_contract.address, data=data))
            recipient = await transaction.wait_for_receipt(client=self.client, timeout=300)

            if recipient["status"] != 1:
                logger.error(f"{self.wallet} | Claim on Sepolia reverted on-chain")
                return False

            logger.debug(f"{self.wallet} | Bridged tokens claimed successfully on Sepolia")
            return True

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

    async def bridge_sepolia_to_neura(self, amount: TokenAmount) -> bool:
        try:
            if amount.Ether <= 0:
                raise Exception(f"Invalid amount: {amount}")

            logger.debug(f"{self.wallet} | Bridging {amount.Ether} tANKR from Sepolia → Neura...")

            token_contract = await self.client_sepolia.contracts.get(Contracts.SEPOLIA_TANKR)
            bridge_contract = await self.client_sepolia.contracts.get(Contracts.SEPOLIA_BRIDGE)

            allowance = await token_contract.functions.allowance(self.client_sepolia.account.address, Contracts.SEPOLIA_BRIDGE.address).call()

            if allowance < amount.Wei:
                logger.info(f"{self.wallet} | Approving bridge to spend tANKR...")
                approve = await self.approve_interface(
                    token_address=Contracts.SEPOLIA_TANKR.address, spender=Contracts.SEPOLIA_BRIDGE.address, amount=amount
                )

                if approve:
                    logger.success(f"{self.wallet} | Approval granted for {amount.Ether} tANKR")
                else:
                    logger.error(f"{self.wallet} | Approval failed for {amount.Ether} tANKR")
                    return False

            else:
                logger.debug(f"{self.wallet} | Sufficient allowance already set")

            logger.debug(f"{self.wallet} | Depositing tANKR to bridge...")

            tx_params = TxArgs(assets=amount.Wei, receiver=self.client.account.address).tuple()

            data = bridge_contract.encode_abi("deposit", args=tx_params)

            transaction = await self.client_sepolia.transactions.sign_and_send(TxParams(to=bridge_contract.address, data=data, value=amount.Wei))
            recipient = await transaction.wait_for_receipt(client=self.client_sepolia, timeout=300)

            if recipient["status"] != 1:
                logger.error(f"{self.wallet} | Bridge Sepolia→Neura deposit transaction reverted on-chain")
                raise Exception("Swap tx reverted on-chain")

            logger.debug(f"{self.wallet} | Bridge Sepolia → Neura completed")
            return True

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

    async def bridge_sepolia_to_neura_all(self) -> bool:
        try:
            logger.debug(f"{self.wallet} | Bridging ALL tANKR from Sepolia → Neura...")

            balance = await self.client.wallet.balance(token=Contracts.SEPOLIA_TANKR)

            min_balance = TokenAmount(amount=0.01, decimals=18)

            if balance.Wei < min_balance.Wei:
                logger.warning(f"{self.wallet} | tANKR balance too low ({balance.Ether} < {min_balance.Ether}), skipping bridge")
                return False

            logger.info(f"{self.wallet} | Bridging {balance.Ether} tANKR (ALL) from Sepolia → Neura")

            sucsess = await self.bridge_sepolia_to_neura(amount=balance)

            random_sleep = random.randint(self.settings.random_pause_between_actions_min, self.settings.random_pause_between_actions_max)

            if not sucsess:
                logger.error(f"{self.wallet} | Bridge Sepolia → Neura (ALL) failed, sleeping {random_sleep}s before exit")
                await asyncio.sleep(random_sleep)
                return False

            logger.success(f"{self.wallet} | Bridge Sepolia → Neura completed: {balance.Ether} tANKR bridged, sleeping {random_sleep}s")
            await asyncio.sleep(random_sleep)
            return True

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

    async def bridge_neura_to_sepolia_percent(self) -> bool:
        try:
            logger.debug(f"{self.wallet} | Starting percentage-based bridge from Neura → Sepolia...")

            balance = await self.client.wallet.balance()

            min_balance = self.settings.min_native_balance
            gas_reserve = 0.2

            if not balance or balance.Ether < min_balance:
                logger.warning(f"{self.wallet} | ANKR balance too low ({balance.Ether if balance else 0:.6f} < {min_balance}), skipping bridge")
                return False

            available_balance = TokenAmount(
                amount=max(0, float(balance.Ether) - gas_reserve),
                decimals=18,
            )

            precision = random.randint(2, 4)
            percent = randfloat(from_=self.settings.brige_percet_min, to_=self.settings.brige_percet_max, step=0.001) / 100
            raw_amount = float(available_balance.Ether) * percent
            factor = 10**precision
            safe_amount = math.floor(raw_amount * factor) / factor

            bridge_amount = TokenAmount(amount=safe_amount, decimals=18)

            if bridge_amount.Ether < 0.01:
                logger.warning(f"{self.wallet} | Bridge amount too small: {bridge_amount.Ether}")
                return False

            logger.info(f"{self.wallet} | Bridging {bridge_amount.Ether} ANKR from Neura → Sepolia")

            sucsess = await self.bridge_neura_to_sepolia(amount_eth=bridge_amount)

            random_sleep = random.randint(
                self.settings.random_pause_between_actions_min,
                self.settings.random_pause_between_actions_max,
            )

            if not sucsess:
                logger.error(f"{self.wallet} | Percentage-based bridge Neura → Sepolia failed, sleeping {random_sleep}s before exit")
                await asyncio.sleep(random_sleep)
                return False

            logger.success(f"{self.wallet} | Percentage-based bridge Neura → Sepolia completed: {bridge_amount.Ether} ANKR, sleeping {random_sleep}s")
            await asyncio.sleep(random_sleep)

            return True

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

    async def bridge_sepolia_to_neura_percent(self) -> bool:
        try:
            logger.debug(f"{self.wallet} | Starting percentage-based bridge from Sepolia → Neura...")

            balance = await self.client_sepolia.wallet.balance(token=Contracts.SEPOLIA_TANKR)

            min_balance = TokenAmount(amount=0.01, decimals=18)

            if balance.Wei < min_balance.Wei:
                logger.warning(f"{self.wallet} | tANKR balance too low ({balance.Ether} < {min_balance.Ether}), skipping bridge")
                return False

            precision = random.randint(2, 4)
            percent = randfloat(from_=self.settings.brige_percet_min, to_=self.settings.brige_percet_max, step=0.001) / 100
            raw_amount = float(balance.Ether) * percent
            factor = 10**precision
            safe_amount = math.floor(raw_amount * factor) / factor

            bridge_amount = TokenAmount(amount=safe_amount, decimals=18)

            if bridge_amount.Ether < 0.001:
                logger.warning(f"{self.wallet} | Bridge amount too small: {bridge_amount}")
                return False

            logger.info(f"{self.wallet} | Bridging {bridge_amount.Ether:.6f} tANKR from Sepolia → Neura")

            sucsess = await self.bridge_sepolia_to_neura(amount=bridge_amount)

            random_sleep = random.randint(
                self.settings.random_pause_between_actions_min,
                self.settings.random_pause_between_actions_max,
            )

            if not sucsess:
                logger.error(f"{self.wallet} | Percentage-based bridge Sepolia → Neura failed, sleeping {random_sleep}s before exit")
                await asyncio.sleep(random_sleep)
                return False

            logger.success(
                f"{self.wallet} | Percentage-based bridge Sepolia → Neura completed: {bridge_amount.Ether} tANKR, sleeping {random_sleep}s"
            )
            await asyncio.sleep(random_sleep)
            return True

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False
