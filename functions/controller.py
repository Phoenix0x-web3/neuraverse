from libs.eth_async.client import Client
from libs.base import Base
from modules.tesst_module import TestModule

from utils.db_api.models import Wallet
from utils.db_api.wallet_api import db
from utils.logs_decorator import controller_log


class Controller:

    def __init__(self, client: Client, wallet: Wallet):
        #super().__init__(client)
        self.client = client
        self.wallet = wallet
        self.base = Base(client=client, wallet=wallet)
        self.test_module = TestModule(client=client, wallet=wallet)

    async def testings_info(self):
        return self.wallet

    async def testings_requests(self):
        return await self.test_module.test_module_reqs()

    @controller_log('Balance Query')
    async def testing_web3(self):
        return await self.client.wallet.balance()

    async def testing_twitter(self):

        await self.test_module.twitter_test_auth()

        # await self.test_module.twitter_test_module_initialize_with_login()
        # await self.test_module.twitter_test_follow_account_and_check_already_follow()
        # await self.test_module.twitter_test_like_tweet()
        # await self.test_module.twitter_test_retweet()
        # await self.test_module.twitter_test_post()
        await self.test_module.twitter.close()
        return 
