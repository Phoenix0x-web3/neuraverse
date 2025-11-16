import asyncio
import random

from loguru import logger
from web3.types import TxParams

from data.models import Contracts
from data.settings import Settings
from libs.base import Base
from libs.eth_async.client import Client
from libs.eth_async.data.models import Networks, TokenAmount, TxArgs
from libs.eth_async.utils.utils import randfloat
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

    async def bridge_neura_to_sepolia(self, amount_eth: TokenAmount) -> bool:
        try:
            if amount_eth.Ether <= 0:
                raise Exception(f"Invalid amount: {amount_eth.Ether}")

            logger.debug(f"{self.wallet} | Bridging {amount_eth.Ether} ANKR from Neura → Sepolia...")

            bridge_contract = await self.client.contracts.get(Contracts.NEURA_BRIDGE)

            tx_params = TxArgs(_recipient=self.client.account.address, _chainId=Networks.Sepolia.chain_id).tuple()

            data = await bridge_contract.encode_abi("deposit", args=tx_params)

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

            data = await bridge_contract.encode_abi("claim", args=tx_params)

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

    async def bridge_sepolia_to_neura(self, amount_eth: TokenAmount) -> bool:
        try:
            if amount_eth.Ether <= 0:
                raise Exception(f"Invalid amount: {amount_eth}")

            logger.debug(f"{self.wallet} | Bridging {amount_eth.Ether} tANKR from Sepolia → Neura...")

            token_contract = await self.client_sepolia.contracts.get(Contracts.SEPOLIA_TANKR)
            bridge_contract = await self.client_sepolia.contracts.get(Contracts.SEPOLIA_BRIDGE)

            allowance = await token_contract.functions.allowance(self.client_sepolia.account.address, Contracts.SEPOLIA_BRIDGE.address).call()

            if allowance < amount_eth.Wei:
                logger.info(f"{self.wallet} | Approving bridge to spend tANKR...")
                approve = self.approve_interface(
                    token_address=Contracts.SEPOLIA_TANKR.address, spender=Contracts.SEPOLIA_BRIDGE.address, amount=amount_eth.Wei
                )

                if approve:
                    logger.success(f"{self.wallet} | Approval granted for {amount_eth.Ether} tANKR")
                else:
                    logger.error(f"{self.wallet} | Approval failed for {amount_eth.Ether} tANKR")
                    return False

            else:
                logger.debug(f"{self.wallet} | Sufficient allowance already set")

            logger.debug(f"{self.wallet} | Depositing tANKR to bridge...")

            tx_params = TxArgs(assets=amount_eth.Wei, receiver=self.client.account.address).tuple()

            data = await bridge_contract.encode_abi("deposit", args=tx_params)

            transaction = await self.client.transactions.sign_and_send(TxParams(to=bridge_contract.address, data=data, value=amount_eth.Wei))
            recipient = await transaction.wait_for_receipt(client=self.client, timeout=300)

            if recipient["status"] != 1:
                logger.error(f"{self.wallet} | Bridge Sepolia→Neura deposit transaction reverted on-chain")
                raise Exception("Swap tx reverted on-chain")

            logger.debug(f"{self.wallet} | Bridge Sepolia → Neura completed")
            return True

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

    async def _bridge_sepolia_to_neura_all(self) -> bool:
        try:
            logger.debug(f"{self.wallet} | Bridging ALL tANKR from Sepolia → Neura...")

            token_contract = await self.client_sepolia.contracts.get(Contracts.SEPOLIA_TANKR)

            tankr_balance = await token_contract.functions.balanceOf(self.wallet.address).call()

            MIN_BALANCE = TokenAmount(amount=0.01, decimals=18)

            if tankr_balance < MIN_BALANCE.Wei:
                logger.warning(f"{self.wallet} | tANKR balance too low ({tankr_balance:.6f} < {MIN_BALANCE}), skipping bridge")
                return False

            logger.info(f"{self.wallet} | Bridging {tankr_balance} tANKR (ALL) from Sepolia → Neura")

            sucsess = await self.bridge_sepolia_to_neura(amount_eth=TokenAmount(amount=tankr_balance, decimals=18, wei=True))

            random_sleep = random.randint(self.settings.random_pause_between_actions_min, self.settings.random_pause_between_actions_max)

            if not sucsess:
                logger.error(f"{self.wallet} | Bridge Sepolia → Neura (ALL) failed, sleeping {random_sleep}s before exit")
                await asyncio.sleep(random_sleep)
                return False

            logger.success(f"{self.wallet} | Bridge Sepolia → Neura completed: {tankr_balance} tANKR bridged, sleeping {random_sleep}s")
            await asyncio.sleep(random_sleep)
            return True

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return False

    async def _bridge_neura_to_sepolia_percent(self) -> bool:
        try:
            logger.debug(f"{self.wallet} | Starting percentage-based bridge from Neura → Sepolia...")

            balance = await self.client.wallet.balance()

            MIN_BALANCE = self.settings.min_native_balance
            GAS_RESERVE = 0.2

            if not balance or balance.Ether < MIN_BALANCE:
                logger.warning(f"{self.wallet} | ANKR balance too low ({balance.Ether if balance else 0:.6f} < {MIN_BALANCE}), skipping bridge")
                return False

            available_balance = max(0, float(balance.Ether) - GAS_RESERVE)

            percent_to_brige = randfloat(from_=self.settings.brige_percet_min, to_=self.settings.brige_percet_max, step=0.001) / 100

            bridge_amount = TokenAmount(amount=available_balance * percent_to_brige, decimals=18)

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

    async def _bridge_sepolia_to_neura_percent(self) -> bool:
        try:
            logger.debug(f"{self.wallet} | Starting percentage-based bridge from Sepolia → Neura...")
            token_contract = await self.client_sepolia.contracts.get(Contracts.SEPOLIA_TANKR)

            balance = await token_contract.functions.balanceOf(self.wallet.address).call()

            MIN_BALANCE = TokenAmount(amount=0.01, decimals=18)

            if balance < MIN_BALANCE.Wei:
                logger.warning(f"{self.wallet} | tANKR balance too low ({balance:.6f} < {MIN_BALANCE}), skipping bridge")
                return False

            percent_to_brige = randfloat(from_=self.settings.brige_percet_min, to_=self.settings.brige_percet_max, step=0.001) / 100

            bridge_amount = TokenAmount(amount=balance * percent_to_brige, decimals=18)

            if bridge_amount.Ether < 0.001:
                logger.warning(f"{self.wallet} | Bridge amount too small: {bridge_amount}")
                return False

            logger.info(f"{self.wallet} | Bridging {bridge_amount.Ether:.6f} tANKR from Sepolia → Neura")

            sucsess = await self.bridge_sepolia_to_neura(amount_eth=bridge_amount)

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
