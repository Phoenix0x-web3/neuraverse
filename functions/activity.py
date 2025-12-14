import asyncio
import random
from datetime import datetime, timedelta
from typing import List

from loguru import logger

from data.settings import Settings
from functions.controller import Controller
from libs.eth_async.client import Client
from libs.eth_async.data.models import Networks
from utils.db_api.models import Wallet
from utils.db_api.wallet_api import db
from utils.encryption import check_encrypt_param


async def random_sleep_before_start(wallet):
    random_sleep = random.randint(Settings().random_pause_start_wallet_min, Settings().random_pause_start_wallet_max)
    now = datetime.now()

    logger.info(f"{wallet} Start at {now + timedelta(seconds=random_sleep)} sleep {random_sleep} seconds before start actions")
    await asyncio.sleep(random_sleep)


async def execute(wallets: List[Wallet], task_func, random_pause_wallet_after_completion: int = 0):
    while True:
        semaphore = asyncio.Semaphore(min(len(wallets), Settings().threads))

        if Settings().shuffle_wallets:
            random.shuffle(wallets)

        async def sem_task(wallet: Wallet):
            async with semaphore:
                task_timeout_seconds = 3600
                try:
                    await asyncio.wait_for(task_func(wallet), timeout=task_timeout_seconds)

                except asyncio.TimeoutError:
                    logger.error(f"[{wallet.id}] Core Execution Tasks | {task_func.__name__} timed out after {task_timeout_seconds} seconds")

                except Exception as e:
                    logger.error(f"[{wallet.id}] failed: {e}")

        tasks = [asyncio.create_task(sem_task(wallet)) for wallet in wallets]
        await asyncio.gather(*tasks, return_exceptions=True)

        if random_pause_wallet_after_completion == 0:
            break

        # update dynamically the pause time
        random_pause_wallet_after_completion = random.randint(
            Settings().random_pause_wallet_after_completion_min, Settings().random_pause_wallet_after_completion_max
        )

        next_run = datetime.now() + timedelta(seconds=random_pause_wallet_after_completion)
        logger.info(f"Sleeping {random_pause_wallet_after_completion} seconds. Next run at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        await asyncio.sleep(random_pause_wallet_after_completion)


async def activity(action: int):
    if not check_encrypt_param():
        logger.error(f"Decryption Failed | Wrong Password")
        return

    wallets = db.all(Wallet)

    range_wallets = Settings().range_wallets_to_run
    if range_wallets != [0, 0]:
        start, end = range_wallets
        wallets = [wallet for i, wallet in enumerate(wallets, start=1) if start <= i <= end]
    else:
        if Settings().exact_wallets_to_run:
            wallets = [wallet for i, wallet in enumerate(wallets, start=1) if i in Settings().exact_wallets_to_run]

    if action == 1:
        await execute(
            wallets,
            random_activity_task,
            random.randint(Settings().random_pause_wallet_after_completion_min, Settings().random_pause_wallet_after_completion_max),
        )

    elif action == 2:
        await execute(
            wallets,
            portal_task,
        )

    elif action == 3:
        await execute(
            wallets,
            update_points,
        )

    elif action == 4:
        await execute(
            wallets,
            faucet,
        )

    elif action == 5:
        await execute(
            wallets,
            ai_talk,
        )

    elif action == 6:
        await execute(
            wallets,
            swaps,
        )

    elif action == 7:
        await execute(
            wallets,
            bridge,
        )

    elif action == 8:
        await execute(
            wallets,
            bridge_all_to_neura,
        )

    elif action == 9:
        await execute(
            wallets,
            connect_socials,
        )


async def random_activity_task(wallet):
    try:
        await random_sleep_before_start(wallet=wallet)

        client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.NeuraTestnet)
        client_sepolia = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.Sepolia)
        controller = Controller(client=client, wallet=wallet, client_sepolia=client_sepolia)

        actions = await controller.build_actions()

        if actions:
            logger.info(f"{wallet} | Started Activity Tasks | Wallet will do {len(actions)} actions")

            for action in actions:
                sleep = random.randint(Settings().random_pause_between_actions_min, Settings().random_pause_between_actions_max)

                try:
                    await action()
                except Exception as e:
                    logger.error(f"Error — {e}")
                    continue

                finally:
                    await asyncio.sleep(sleep)

        await controller.update_db_by_user_info()

    except asyncio.CancelledError:
        raise

    except Exception as e:
        logger.error(f"Core | Random Activity | {wallet} | {e}")
        raise e


async def portal_task(wallet):
    await random_sleep_before_start(wallet=wallet)

    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.NeuraTestnet)
    controller = Controller(client=client, wallet=wallet)

    try:
        await controller.complete_quests()
    except Exception as e:
        logger.error(f"Error — {e}")


async def connect_socials(wallet):
    await random_sleep_before_start(wallet=wallet)

    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.NeuraTestnet)
    controller = Controller(client=client, wallet=wallet)

    try:
        await controller.connect_socials()
    except Exception as e:
        logger.error(f"Error — {e}")


async def update_points(wallet):
    await random_sleep_before_start(wallet=wallet)

    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.NeuraTestnet)
    controller = Controller(client=client, wallet=wallet)

    try:
        await controller.update_db_by_user_info()
    except Exception as e:
        logger.error(f"Error — {e}")


async def faucet(wallet):
    await random_sleep_before_start(wallet=wallet)

    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.NeuraTestnet)
    controller = Controller(client=client, wallet=wallet)

    try:
        await controller.faucet()
    except Exception as e:
        logger.error(f"Error — {e}")


async def ai_talk(wallet):
    await random_sleep_before_start(wallet=wallet)

    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.NeuraTestnet)
    controller = Controller(client=client, wallet=wallet)

    try:
        total_ai_chat = random.randint(Settings().ai_chat_count_min, Settings().ai_chat_count_max)
        await controller.run_ai_chat_session(total_ai_chat=total_ai_chat)
    except Exception as e:
        logger.error(f"Error — {e}")


async def swaps(wallet):
    await random_sleep_before_start(wallet=wallet)

    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.NeuraTestnet)
    controller = Controller(client=client, wallet=wallet)

    try:
        total_swaps = random.randint(Settings().swaps_count_min, Settings().swaps_count_max)
        await controller.execute_zotto_swaps(total_swaps=total_swaps)
    except Exception as e:
        logger.error(f"Error — {e}")


async def bridge(wallet):
    await random_sleep_before_start(wallet=wallet)

    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.NeuraTestnet)
    client_sepolia = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.Sepolia)
    controller = Controller(client=client, wallet=wallet, client_sepolia=client_sepolia)

    try:
        total_bridge = random.randint(Settings().bridge_count_min, Settings().bridge_count_max)
        await controller.execute_auto_bridge(total_bridge=total_bridge)
    except Exception as e:
        logger.error(f"Error — {e}")


async def bridge_all_to_neura(wallet):
    await random_sleep_before_start(wallet=wallet)

    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.NeuraTestnet)
    client_sepolia = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.Sepolia)
    controller = Controller(client=client, wallet=wallet, client_sepolia=client_sepolia)

    try:
        await controller.execute_auto_bridge(bridge_all_to_neura=True, total_bridge=1)
    except Exception as e:
        logger.error(f"Error — {e}")
