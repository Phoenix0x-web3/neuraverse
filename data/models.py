from typing import Any, cast

from data.config import ABIS_DIR
from libs.eth_async.classes import Singleton
from libs.eth_async.data.models import DefaultABIs, RawContract
from libs.eth_async.utils.files import read_json


class Contracts(Singleton):
    ANKR = RawContract(title="ANKR", address="0x422f5eae5fee0227fb31f149e690a73c4ad02db8", abi=DefaultABIs.Token)

    ZOTTO_ROUTER_ADDRESS = RawContract(
        title="Zotto swap",
        address="0x6836F8A9a66ab8430224aa9b4E6D24dc8d7d5d77",
        abi=cast(list[dict[str, Any]], read_json((ABIS_DIR, "zotto_router.json"))),
    )

    ZOTTO_POOLS_ADRESS = RawContract(
        title="Zotto pools",
        address="0xc3F58730ed927636Fda3eda14824F7D8FcCe19fB",
        abi=cast(list[dict[str, Any]], read_json((ABIS_DIR, "zotto_pools.json"))),
    )

    NEURA_BRIDGE = RawContract(
        title="Neura bridge",
        address="0xc6255a594299F1776de376d0509aB5ab875A6E3E",
        abi=cast(list[dict[str, Any]], read_json((ABIS_DIR, "neura_bridge.json"))),
    )

    SEPOLIA_BRIDGE = RawContract(
        title="Sepolia bridge",
        address="0xc6255a594299F1776de376d0509aB5ab875A6E3E",
        abi=cast(list[dict[str, Any]], read_json((ABIS_DIR, "sepolia_bridge.json"))),
    )

    SEPOLIA_TANKR = RawContract(title="ANKR on Sepolia", address="0xB88Ca91Fef0874828e5ea830402e9089aaE0bB7F", abi=DefaultABIs.Token)

    OMNIHUB_NFT = RawContract(
        title="Omnihub_nft",
        address="0x6f38636175E178e1d2004431fFcb91a1030282aC",
        abi=cast(list[dict[str, Any]], read_json((ABIS_DIR, "omnihub_nft.json"))),
    )
