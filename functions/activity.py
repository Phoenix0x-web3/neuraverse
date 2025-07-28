import asyncio
import random
from datetime import datetime, timedelta

from curl_cffi import AsyncSession
from loguru import logger

from functions.controller import Controller
from libs.eth_async.client import Client
from libs.eth_async.data.models import Networks
from utils.db_api.models import Wallet
from utils.db_api.wallet_api import db
from settings import THREADS, SHUFFLE_WALLETS, SLEEP_AFTER_EACH_CYCLE_HOURS, EXACT_WALLETS_TO_RUN

async def execute(wallets : Wallet, task_func, timeout_hours : int = 0):
    
    while True:
        
        semaphore = asyncio.Semaphore(min(len(wallets), THREADS))

        if SHUFFLE_WALLETS:
            random.shuffle(wallets)

        async def sem_task(wallet : Wallet):
            async with semaphore:
                try:
                    await task_func(wallet)
                except Exception as e:
                    logger.error(f"[{wallet.id}] failed: {e}")

        tasks = [asyncio.create_task(sem_task(wallet)) for wallet in wallets]
        await asyncio.gather(*tasks)

        if timeout_hours == 0:
            break
        
        logger.info(f"Sleeping for {timeout_hours} hours before the next iteration")
        await asyncio.sleep(timeout_hours * 60 * 60)
        

async def activity(action: int):
    all_wallets = db.all(Wallet)

    # Filter wallets if EXACT_WALLETS_TO_USE is defined
    if EXACT_WALLETS_TO_RUN:
        wallets = [wallet for i, wallet in enumerate(all_wallets, start=1) if i in EXACT_WALLETS_TO_RUN]
    else:
        wallets = all_wallets

    if action == 1:
        await execute(wallets, test_activity)

    elif action == 2:
        await execute(wallets, test_requests, SLEEP_AFTER_EACH_CYCLE_HOURS)

    elif action == 3:
        await execute(wallets, test_web3)
       
    elif action == 4:
        await execute(wallets, test_twitter)

async def test_activity(wallet):
    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.Ethereum)

    controller = Controller(client=client, wallet=wallet)

    c = await controller.testings_info()
    logger.success(c)

async def test_requests(wallet):
    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.Ethereum)

    controller = Controller(client=client, wallet=wallet)

    c = await controller.testings_requests()
    logger.success(c)

async def test_web3(wallet):
    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.Ethereum)

    controller = Controller(client=client, wallet=wallet)

    c = await controller.testing_web3()
    logger.success(c)

async def test_twitter(wallet):
    client = Client(private_key=wallet.private_key, proxy=wallet.proxy, network=Networks.Ethereum)

    controller = Controller(client=client, wallet=wallet)

    c = await controller.testing_twitter()
    logger.success(c)
