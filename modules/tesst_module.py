import asyncio
from loguru import logger
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
            "Origin": "https://app.testings.Headers"
            }

    @controller_log("Testing Requests")
    async def test_module_reqs(self):

        url = 'https://webhook.site/30f29d59-5974-43ed-8e7d-e87e61a2cc46'

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
        await self.twitter.follow_account(account_name="RusMetaX")
        return 

    @controller_log("Testing Twitter")
    async def twitter_test_like_tweet(self):
        await self.twitter.like_tweet(tweet_id=1951217370959053017)
        return 

    @controller_log("Testing Twitter")
    async def twitter_test_retweet(self):
        await self.twitter.retweet(tweet_id=1951217370959053017)
        return 

    @controller_log("Testing Twitter")
    async def twitter_test_post(self):
        await self.twitter.post_tweet(text="Hello World!")
        await asyncio.sleep(5)
        await self.twitter.post_tweet(text="Hello World!")
        return 

    @controller_log("Testing Twitter")
    async def twitter_test_auth(self):
        await self.connect_pharos()
        # await self.connect_somnia()
        # await self.connect_plume()
        # await self.connect_camp()
        # await self.connect_0g()
        # await self.connect_kuru()
        return

    @controller_log("Testing Twitter")
    async def connect_pharos(self):
        # PASS
        url = "https://twitter.com/i/oauth2/authorize?client_id=TGQwNktPQWlBQzNNd1hyVkFvZ2E6MTpjaQ&code_challenge=75n30zliaiuudJJfwo6-1Tmyz21LabzUNqMUNd5m6nQ&code_challenge_method=S256&redirect_uri=https://testnet.pharosnetwork.xyz&response_type=code&scope=users.read tweet.read follows.read&state=twitterHQP-LbSi6BYLc3A04y-TiOmFHwyJFgJlwThoZsA9EBG"
        oauth_data = await self.twitter.connect_twitter_to_site_oauth2(twitter_auth_url=url)
        api_url = "https://api.pharosnetwork.xyz/auth/bind/twitter"
        json_data = {
            'state': f'{oauth_data.state_verifier_token}',
            'code': f'{oauth_data.auth_token}',
            'address': '0x5de75856754f6482f131B8BEd19769e6E0445F42'
        }
        headers = {
            'Referer': 'https://testnet.pharosnetwork.xyz/',
        }
        resp = await self.browser.post(url=api_url, json=json_data, headers=headers)
        logger.debug(resp.status_code)
        logger.debug(resp.json())



    @controller_log("Testing Twitter")
    async def connect_somnia(self):
        #PASS
        url = "https://twitter.com/i/oauth2/authorize?response_type=code&client_id=WS1FeDNoZnlqTEw1WFpvX1laWkc6MTpjaQ&redirect_uri=https%3A%2F%2Fquest.somnia.network%2Ftwitter&scope=tweet.read%20users.read&state=eyJ0eXBlIjoiQ09OTkVDVF9UV0lUVEVSIn0=&code_challenge=challenge123&code_challenge_method=plain"
        oauth_data = await self.twitter.connect_twitter_to_site_oauth2(twitter_auth_url=url)
        api_url = "https://quest.somnia.network/api/auth/socials"
        json_data = {
            'code': f'{oauth_data.auth_token}',
            'codeChallenge': 'challenge123',
            'provider': 'twitter',
        }
        resp = await self.browser.post(url=api_url, json=json_data)
        logger.debug(resp.json())

    @controller_log("Testing Twitter")
    async def connect_plume(self):
        #PASS
        url = "https://twitter.com/i/oauth2/authorize?client_id=N1l3bkM4QmhnYk00cFRSWUdpcEI6MTpjaQ&redirect_uri=https%3A%2F%2Fportal-api.plume.org%2Fapi%2Fv1%2Fsocials%2Ftwitter%2Fcallback&response_type=code&scope=tweet.read%20users.read&state=eyJ3YWxsZXRBZGRyZXNzIjoiMHg1ZGU3NTg1Njc1NGY2NDgyZjEzMWI4YmVkMTk3NjllNmUwNDQ1ZjQyIn0=&code_challenge=bSvSa5OJxLqd87RK_eQnnokoxgriWE94ATCqaSmacs4&code_challenge_method=S256"
        oauth_data = await self.twitter.connect_twitter_to_site_oauth2(twitter_auth_url=url)
        logger.debug(oauth_data.callback_response.status_code)
        logger.debug(oauth_data.callback_response.headers)

    @controller_log("Testing Twitter")
    async def connect_camp(self):
        #Not Passed Location
        url = "https://x.com/i/oauth2/authorize?code_challenge_method=plain&code_challenge=8ee088489c3011199b93b1fcaf2ee499229831d3&state=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI1NjRiOWMyNS04ZjBiLTRmM2ItODBmYy05MGI3YzE0MTFkNDgiLCJob3N0IjoibG95YWx0eS5jYW1wbmV0d29yay54eXoiLCJ3ZWJzaXRlSWQiOiIzMmFmYzVjOS1mMGZiLTQ5MzgtOTU3Mi03NzVkZWUwYjRhMmIiLCJpYXQiOjE3NTM4Nzc1NTgsImV4cCI6MTc1Mzg4MTE1OH0.2NUuLUnAQOxMKMjxyMafNhDv--N2FgKkRtFZGoYDLYE&client_id=TVBRYlFuNzg5RVo4QU11b3EzVV86MTpjaQ&scope=users.read%20tweet.read&response_type=code&redirect_uri=https%3A%2F%2Fsnag-render.com%2Fapi%2Ftwitter%2Fauth%2Fcallback"
        oauth_data = await self.twitter.connect_twitter_to_site_oauth2(twitter_auth_url=url)

        headers_dict = dict(oauth_data.callback_response.headers)
        logger.debug(oauth_data.callback_response.status_code)
        logger.debug(headers_dict)

    @controller_log("Testing Twitter")
    async def connect_0g(self):
        #Not Passed Location
        headers = {
            "Content-Type": "text/plain;charset=UTF-8",
            "sec-ch-ua-mobile": "?0",
            "Accept": "*/*",
            "Origin": "https://faucet.0g.ai",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://faucet.0g.ai/",
            "Accept-Encoding": "gzip, deflate, br, zstd",
        }
        
        r = await self.browser.post(url='https://faucet.0g.ai/api/request-token', json={"domain":"0g"}, headers=headers)
        
        r.raise_for_status()
        
        url = r.json().get('url')
  
        api_url = "https://faucet.0g.ai/"
        oauth_data = await self.twitter.connect_twitter_to_site_oauth(twitter_auth_url=url)

        logger.debug(oauth_data.callback_response.status_code)
        logger.debug(oauth_data.callback_response.headers)
            
    @controller_log("Testing Twitter")
    async def connect_kuru(self):
        #Not Passed Privy
        url = "https://x.com/i/oauth2/authorize?redirect_uri=https%3A%2F%2Fauth.privy.io%2Fapi%2Fv1%2Foauth%2Fcallback&response_type=code&scope=users.read+tweet.read&state=fvvnWSJdI8sJJyzxbkw_p6eDZA9S9yWS9QLwSSWHedYEL_EZ&code_challenge=cQ2tS-L57sbaCUw6kNjja9uKmMYt2orgzCdatC4YziM&code_challenge_method=S256&client_id=YlJMT0QtbzB1RU1kaDd6Q2xPem06MTpjaQ"

        oauth_data = await self.twitter.connect_twitter_to_site_oauth2(twitter_auth_url=url)

        api_url = "https://auth.privy.io/api/v1/oauth/link"
        json_data = {
            'authorization_code': f'{oauth_data.auth_token}',
            'code_verifier': 'jFEEqg3L1bzgQVxbJCGl1cl5WcaSznEPUElvABCW9igaQEbu',
            'state_code': f'{oauth_data.state_verifier_token}',
        }
        response = await self.browser.post(url=api_url, json=json_data)
        headers_dict = dict(response.headers)
        logger.debug(response.status_code)
        logger.debug(headers_dict)
        logger.debug(response.json())



