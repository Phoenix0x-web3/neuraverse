import asyncio
import random
import time
from decimal import Decimal

from eth_abi.abi import encode as abi_encode
from loguru import logger
from web3.types import TxParams

from data.constants import DEFAULT_HEADERS
from data.models import Contracts
from libs.base import Base
from libs.eth_async.client import Client
from libs.eth_async.data.models import DefaultABIs, RawContract, TokenAmount, TxArgs
from utils.browser import Browser
from utils.db_api.models import Wallet


class ZottoSwap(Base):
    __module__ = "Zotto swap"

    def __init__(self, client: Client, wallet: Wallet):
        self.client = client
        self.wallet = wallet
        self.session = Browser()
        self.headers = DEFAULT_HEADERS

    async def get_all_tokens_info(self) -> list:
        try:
            logger.debug(f"{self.wallet} | Fetching full token list from API")

            payload = {
                "operationName": "AllTokens",
                "variables": {},
                "query": "query AllTokens {\n  tokens {\n    ...TokenFields\n    __typename\n  }\n}\n\nfragment TokenFields on Token {\n  id\n  symbol\n  name\n  decimals\n  derivedMatic\n  __typename\n}",
            }

            response = await self.session.post(
                url="https://api.goldsky.com/api/public/project_cmc8t6vh6mqlg01w19r2g15a7/subgraphs/analytics/1.0.1/gn",
                headers=self.headers,
                json=payload,
            )

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                raise RuntimeError(f"Non-200 response ({response.status_code})")

            all_tokens_info = response.json()["data"]["tokens"]

            if not all_tokens_info:
                raise ValueError(f"Invalid account info response: {response.text}")

            logger.debug(f"{self.wallet} | Account info fetched successfully - {all_tokens_info}")

            return all_tokens_info

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            raise

    async def get_available_token_contracts(self) -> list[RawContract]:
        try:
            logger.debug(f"{self.wallet} | Fetching available token contracts")
            tokens_all = await self.get_all_tokens_info()
            if not tokens_all:
                logger.error(f"{self.wallet} | Tokens list from API is empty")
                return []

            seen_ids = set()
            filtered = []
            for token in tokens_all:
                if float(token.get("derivedMatic", 0)) == 0:
                    continue

                token_id = token.get("id")
                if not token_id or token_id in seen_ids:
                    continue

                seen_ids.add(token_id)
                filtered.append(token)

            if not filtered:
                logger.warning(f"{self.wallet} | No tokens passed filters")
                return []

            available_tokens: list[RawContract] = []
            for token in filtered:
                available_tokens.append(RawContract(title=token.get("symbol", ""), address=token["id"], abi=DefaultABIs.Token))

            logger.debug(f"{self.wallet} | Available token contracts fetched successfully - {available_tokens}")
            return available_tokens

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return []

    async def get_pools_info(self, pools: list) -> list:
        try:
            logger.debug(f"{self.wallet} | Fetching pools info from API")
            payload = {
                "operationName": "MultiplePools",
                "variables": {
                    "poolIds": pools,
                },
                "query": "query MultiplePools($poolIds: [ID!]) {\n  pools(where: { id_in: $poolIds }) {\n    id\n    fee\n    token0 {\n      id\n      symbol\n      name\n      decimals\n      derivedMatic\n      __typename\n    }\n    token1 {\n      id\n      symbol\n      name\n      decimals\n      derivedMatic\n      __typename\n    }\n    sqrtPrice\n    liquidity\n    tick\n    tickSpacing\n    totalValueLockedUSD\n    volumeUSD\n    feesUSD\n    untrackedFeesUSD\n    token0Price\n    token1Price\n    __typename\n  }\n}",
            }

            response = await self.session.post(
                url="https://api.goldsky.com/api/public/project_cmc8t6vh6mqlg01w19r2g15a7/subgraphs/analytics/1.0.1/gn",
                headers=self.headers,
                json=payload,
            )

            if response.status_code != 200:
                logger.error(f"{self.wallet} | Non-200 response ({response.status_code}). Body: {response.text}")
                raise RuntimeError(f"Non-200 response ({response.status_code})")

            all_pools = response.json()["data"]["pools"]

            if not all_pools:
                logger.debug(f"{self.wallet} | No pools found for provided addresses")
                return []

            logger.debug(f"{self.wallet} | Pools info fetched successfully - {all_pools}")

            return all_pools

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return []

    async def get_pool_prices_if_liquid(self, token_0: RawContract, token_1: RawContract) -> dict:
        try:
            logger.debug(f"{self.wallet} | DEBUG: fetching Zotto pools contract")
            pools_contract = await self.client.contracts.get(Contracts.ZOTTO_POOLS_ADRESS)
            logger.debug(f"{self.wallet} | DEBUG: Zotto pools contract fetched")

            pool_address_1 = await pools_contract.functions.computePoolAddress(token_0.address, token_1.address).call()
            await asyncio.sleep(random.uniform(1, 2))
            pool_address_2 = await pools_contract.functions.computePoolAddress(token_1.address, token_0.address).call()

            pools_info = await self.get_pools_info(pools=[pool_address_1.lower(), pool_address_2.lower()])

            logger.debug(f"{self.wallet} | DEBUG: after get_pools_info → {pools_info}")

            logger.debug(f"{self.wallet} | DEBUG: scanning pools_info for liquidity")

            selected_pool = None
            for pool in pools_info:
                try:
                    liq = int(pool.get("liquidity", 0) or 0)
                    logger.debug(f"{self.wallet} | DEBUG: pool {pool.get('id')} has liquidity {liq}")
                    if liq > 0:
                        selected_pool = pool
                        break
                except Exception as e:
                    logger.debug(f"{self.wallet} | DEBUG: failed to parse liquidity for pool {pool.get('id')} — {e}")
                    continue

            logger.debug(f"{self.wallet} | DEBUG: selected pool = {selected_pool}")

            if not selected_pool:
                return {}

            token_0_id = selected_pool.get("token0", {}).get("id")
            token_1_id = selected_pool.get("token1", {}).get("id")
            token_0_price = float(selected_pool.get("token0Price", 0) or 0)
            token_1_price = float(selected_pool.get("token1Price", 0) or 0)

            if not token_0_id or not token_1_id:
                return {}

            logger.debug(f"{self.wallet} | Pool prices fetched successfully")

            logger.debug(f"{self.wallet} | DEBUG: returning pool prices: {token_0_id}={token_0_price}, {token_1_id}={token_1_price}")
            return {
                token_0_id: token_0_price,
                token_1_id: token_1_price,
            }

        except Exception as e:
            logger.error(f"{self.wallet} | Error — {e}")
            return {}

    async def execute_swap(
        self,
        amount: TokenAmount,
        from_token: RawContract,
        to_token: RawContract,
        max_gas_price: int,
        tokens_price: dict | None = None,
        slippage: float = 15.0,
    ) -> bool:
        try:
            logger.debug(f"{self.wallet} | DEBUG: execute_swap START — amount={amount.Ether}, from={from_token.title}, to={to_token.title}")

            if amount.Wei <= 0:
                raise ValueError(f"Invalid amount: {amount.Wei}")

            if max_gas_price:
                gas_price = await self.client.transactions.gas_price()
                logger.debug(f"{self.wallet} | DEBUG: initial gas price — {gas_price.Gwei} gwei")

                if gas_price.Gwei > max_gas_price:
                    logger.warning(f"{self.wallet} | High gas price detected: {gas_price.Gwei} gwei")

                    wait_start = time.time()
                    while gas_price.Gwei > max_gas_price:
                        elapsed = time.time() - wait_start
                        if elapsed >= 120:
                            logger.warning(
                                f"{self.wallet} | Gas did not drop below {max_gas_price} gwei within 120s "
                                f"(last observed {gas_price.Gwei} gwei) — aborting swap"
                            )
                            return False
                        sleep = random.randint(20, 60)
                        logger.debug(f"{self.wallet} | DEBUG: gas still high ({gas_price.Gwei} gwei), sleeping {sleep}s (elapsed {int(elapsed)}s)")
                        await asyncio.sleep(sleep)
                        gas_price = await self.client.transactions.gas_price()
                        logger.debug(f"{self.wallet} | DEBUG: refreshed gas price — {gas_price.Gwei} gwei")

                    logger.info(f"{self.wallet} | Gas normalized below threshold: {gas_price.Gwei} gwei — continuing execution")
                else:
                    logger.debug(f"{self.wallet} | DEBUG: gas price acceptable — {gas_price.Gwei} gwei")

            swap_from_native = from_token.address.lower() == Contracts.ANKR.address.lower()

            if not swap_from_native:
                approve = await self.approve_interface(
                    token_address=from_token.address, spender=Contracts.ZOTTO_ROUTER_ADDRESS.address, amount=amount, title=from_token.title
                )

                if approve:
                    sleep = random.randint(5, 10)
                    logger.success(f"{self.wallet} | Approved {amount.Ether} {from_token.title}, sleeping {sleep}s before swap")
                    await asyncio.sleep(sleep)
                else:
                    logger.error(f"{self.wallet} | Token approval failed for {amount.Ether} {from_token.title}")
                    return False

            deadline_ms = int(time.time() * 1000) + (30 * 60 * 1000)

            if tokens_price:
                price = Decimal(str(tokens_price[from_token.address.lower()]))
                amt = Decimal(str(amount.Ether))
                slip = Decimal(str((100 - slippage) / 100))

                logger.debug(f"{self.wallet} | DEBUG: calculating amount_out_min using price={price} and amount={amt}")

                amount_out_min = TokenAmount(
                    amount=float(price * amt * slip),
                    decimals=18
                    if to_token.address == Contracts.ANKR.address
                    else await self.client.transactions.get_decimals(contract=to_token.address),
                )

            else:
                amount_out_min = None

            recipient_address = "0x0000000000000000000000000000000000000000" if swap_from_native else self.client.account.address

            inner = self._encode_swap_params(
                from_token=from_token,
                to_token=to_token,
                recipient_address=recipient_address,
                deadline_ms=deadline_ms,
                amount=amount,
                amount_out_min=amount_out_min
                if amount_out_min
                else TokenAmount(
                    amount=0,
                    decimals=18
                    if from_token.address == Contracts.ANKR.address
                    else await self.client.transactions.get_decimals(contract=to_token.address),
                ),
            )

            calls = [bytes.fromhex(inner[2:])]

            if not swap_from_native:
                unwrap_params = abi_encode(["uint256", "address"], [0, self.client.account.address])
                unwrap_call = bytes.fromhex("69bc35b2" + unwrap_params.hex())
                calls.append(unwrap_call)

            contract = await self.client.contracts.get(Contracts.ZOTTO_ROUTER_ADDRESS)

            tx_value = amount.Wei if swap_from_native else 0
            tx_params = TxArgs(data=calls).tuple()
            data = contract.encode_abi("multicall", args=tx_params)

            transaction = await self.client.transactions.sign_and_send(TxParams(to=Contracts.ZOTTO_ROUTER_ADDRESS.address, data=data, value=tx_value))
            recipient = await transaction.wait_for_receipt(client=self.client, timeout=300)

            if recipient["status"] != 1:
                logger.error(f"{self.wallet} | Swap transaction reverted on-chain")
                raise Exception("Swap tx reverted on-chain")

            logger.debug(f"{self.wallet} | Swap executed successfully: {amount.Ether} {from_token.title} → {to_token.title}")
            return True

        except Exception:
            logger.error(f"{self.wallet} | Swap execution failed for {amount.Ether} {from_token.title} → {to_token.title}")
            return False

    def _encode_swap_params(
        self,
        from_token: RawContract,
        to_token: RawContract,
        recipient_address: str,
        deadline_ms: int,
        amount: TokenAmount,
        amount_out_min: TokenAmount,
    ) -> str:
        swap_params = abi_encode(
            ["address", "address", "uint256", "address", "uint256", "uint256", "uint256", "uint256"],
            [
                from_token.address,
                to_token.address,
                0,
                self.client.w3.to_checksum_address(recipient_address),
                int(deadline_ms),
                int(amount.Wei),
                amount_out_min.Wei,
                0,
            ],
        )
        return "0x1679c792" + swap_params.hex()

    async def _current_balances(self, tokens: list) -> dict:
        balances = {}
        for token in tokens:
            logger.debug(f"{self.wallet} | DEBUG: checking balance for {token.title} ({token.address})")

            await asyncio.sleep(random.uniform(1, 2))

            try:
                if token.address == Contracts.ANKR.address:
                    balance = await self.client.wallet.balance()
                else:
                    balance = await self.client.wallet.balance(token=token)

                logger.debug(f"{self.wallet} | DEBUG: got balance for {token.title}: {balance.Ether}")
                balances[token.address] = balance

            except Exception as e:
                logger.error(f"{self.wallet} | DEBUG: balance query failed for {token.title} ({token.address}) — {e}")
                balances[token.address] = None
                continue

        return balances
