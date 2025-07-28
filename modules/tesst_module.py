import asyncio
from libs.eth_async.client import Client
from libs.base import Base
from utils.browser import Browser
from utils.db_api.models import Wallet
from utils.logs_decorator import controller_log
from utils.twitter.twitter_client import TwitterClient


class TestModule(Base):
    __module_name__ = "Test Module 1"

    def __init__(self, client: Client, wallet: Wallet):
        self.client = client
        self.wallet = wallet
        self.browser = Browser(wallet=self.wallet)
        self.twitter = TwitterClient(user=wallet)

        self.headers = {
            "Origin": "https://app.testings.Headers",
            "user-agent": "Mozilla/10050000.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "sec-ch-ua-platform" : "Windows"
            }

    @controller_log("Testing Requests")
    async def test_module_reqs(self):

        url = 'https://webhook.site/a0173dd5-1254-4292-9944-819e7ef8905e'

        r = await self.browser.get(url=url, headers=self.headers)
        r.raise_for_status()
        r = await self.browser.get(url=url)

        return r.json()

    @controller_log("Testing Twitter")
    async def twitter_test_module_initialize_with_token(self):
        return await self.twitter.initialize()

    @controller_log("Testing Twitter")
    async def twitter_test_module_initialize_with_login(self):
        twitter = TwitterClient(user=self.wallet, twitter_username="Na66252527", twitter_password="2qP20c8KZ9")
        return await twitter.initialize()

    @controller_log("Testing Twitter")
    async def twitter_test_follow_account_and_check_already_follow(self):
        await self.twitter.follow_account(account_name="playcambria")
        return 

    @controller_log("Testing Twitter")
    async def twitter_test_like_tweet(self):
        await self.twitter.like_tweet(tweet_id=1915140195629904126)
        await asyncio.sleep(5)
        await self.twitter.like_tweet(tweet_id=1915140195629904126)
        return 

    @controller_log("Testing Twitter")
    async def twitter_test_retweet(self):
        await self.twitter.retweet(tweet_id=1915140195629904126)
        await asyncio.sleep(5)
        await self.twitter.retweet(tweet_id=1915140195629904126)
        return 

    @controller_log("Testing Twitter")
    async def twitter_test_post(self):
        await self.twitter.post_tweet(text="Hello World!")
        await asyncio.sleep(5)
        await self.twitter.post_tweet(text="Hello World!")
        return 


