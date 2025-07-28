from typing import Optional, Any, Tuple
from loguru import logger
import libs.twitter as twitter  
from libs.twitter.utils import remove_at_sign
from utils.db_api.models import Wallet
from utils.db_api.wallet_api import update_twitter_token

from data.config import logger
from data.models import Settings

#TODO Move to Exception file
class BadTwitter(Exception):
    pass


class TwitterClient():

    def __init__(
        self,
        user: Wallet,
        twitter_auth_token: str | None = None,
        twitter_username: str | None = None,
        twitter_password: str | None = None,
        totp_secret: str | None = None,
        ct0: str | None = None,
        email: str | None = None
    ):
        """
        Initialize Twitter client

        Args:
            user: User object
            twitter_auth_token: Twitter authorization token
            twitter_username: Twitter username (without @)
            twitter_password: Twitter account password
            totp_secret: TOTP secret (if 2FA is enabled)
        """

        if not twitter_auth_token:
            twitter_auth_token = user.twitter_token
        # Create Twitter account
        self.user = user
        self.twitter_account = twitter.Account(
            auth_token=twitter_auth_token,
            username=twitter_username,
            password=twitter_password,
            totp_secret=totp_secret,
            ct0=ct0,
            email=email
        )

        # Twitter client configuration
        self.client_config = {
            "wait_on_rate_limit": True,
            "auto_relogin": True,
            "update_account_info_on_startup": True,
            #TODO: Import CAPMONSTER_API_KEY
            "capsolver_api_key": "CAPMONSTER_API_KEY", 
        }

        # Add proxy if specified
        if user.proxy:
            self.client_config["proxy"] = user.proxy

        # Initialize Twitter client as None
        self.twitter_client = None
        self.is_connected = False

        # Add fields for tracking errors
        self.last_error = None
        self.error_count = 0
        self.settings = Settings()

    async def initialize(self) -> bool:
        """
        Initializes the Twitter client

        Returns:
            Success status
        """
        try:
            # Create Twitter client
            self.twitter_client = twitter.Client(
                self.twitter_account, **self.client_config
            )

            # Establish connection
            await self.twitter_client.__aenter__()

            # Check account status
            await self.twitter_client.establish_status()

            if self.twitter_account.status == twitter.AccountStatus.GOOD:
                logger.success(f"{self.user} Twitter client initialized")
                update_twitter_token(private_key=self.user.private_key, updated_token=self.twitter_account.auth_token)
                return True
            else:
                error_msg = f"Problem with Twitter account status: {self.twitter_account.status}"
                logger.error(f"{self.user} {error_msg}")
                self.last_error = error_msg
                self.error_count += 1

                # If authorization issue, mark token as bad
                if self.twitter_account.status in [
                    twitter.AccountStatus.BAD_TOKEN,
                    twitter.AccountStatus.SUSPENDED,
                ]:
                    #TODO Replace Twitter Token to DB
                    raise BadTwitter

                return False

        except Exception as e:
            error_msg = f"Error initializing Twitter client: {str(e)}"
            logger.error(f"{self.user} {error_msg}")
            return False

    async def close(self):
        """Closes the Twitter connection"""
        if self.twitter_client:
            try:
                await self.twitter_client.__aexit__(None, None, None)
                self.twitter_client = None
                logger.info(f"{self.user} Twitter client closed")
            except Exception as e:
                logger.error(
                    f"{self.user} Error closing Twitter client: {str(e)}"
                )

    async def __aenter__(self):
        """Context manager for entering"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager for exiting"""
        await self.close()

    async def follow_account(
        self, account_name: str
    ) -> Tuple[bool, Optional[str], bool]:
        """
        Follows the specified Twitter account

        Args:
            account_name: Account name to follow (with or without @)

        Returns:
            Tuple[success, error_message, already_following]:
            - Success status
            - Error message (if any)
            - Flag indicating if already following
        """
        already_following = False

        if not self.twitter_client:
            logger.error(
                f"{self.user} Attempt to perform action without client initialization"
            )
            return False, "Twitter client not initialized", False

        try:
            # Remove @ from account name if present
            clean_account_name = remove_at_sign(account_name)

            # Get user by username
            user = await self.twitter_client.request_user_by_username(
                clean_account_name
            )

            if not user or not user.id:
                logger.error(
                    f"{self.user} Could not find user @{clean_account_name}"
                )
                return False, f"User @{clean_account_name} not found", False

            # Check if already following the user
            is_following = await self._check_if_following(user_id=user.id)
            if is_following:
                logger.info(f"{self.user} Already following @{clean_account_name}")
                return True, None, True  # Return already_following=True

            # Follow the user
            try:
                is_followed = await self.twitter_client.follow(user.id)

                if is_followed:
                    logger.success(f"{self.user} Followed @{clean_account_name}")
                    return True, None, False
                else:
                    logger.warning(
                        f"{self.user} Failed to follow @{clean_account_name}"
                    )
                    return False, "Follow error", False
            except Exception as e:
                error_msg = str(e)

                logger.error(
                    f"{self.user} Error following @{clean_account_name}: {error_msg}"
                )
                return False, error_msg, False

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"{self.user} Error following @{account_name}: {error_msg}"
            )
            return False, error_msg, False

    async def _check_if_following(self, user_id: int) -> bool:
        """
        Checks if the current user is following the specified user

        Args:
            user_id: ID of the user to check

        Returns:
            True if already following, False otherwise
        """
        try:
            # Get current user's Twitter ID
            try:
                following = await self.twitter_client.request_followings()
                if following:
                    for followed_user in following:
                        if str(followed_user.id) == str(user_id):
                            return True
            except Exception as e:
                # If this method fails, rely on friendship result
                logger.warning(
                    f"{self.user} Failed to get following list: {str(e)}"
                )
            return False
        except Exception as e:
            logger.error(f"{self.user} Error checking follow status: {str(e)}")
            return False

    async def post_tweet(self, text: str) -> Optional[Any]:
        """
        Posts a tweet with the specified text

        Args:
            text: Tweet text

        Returns:
            Tweet object on success, None on error
        """
        if not self.twitter_client:
            logger.error(
                f"{self.user} Attempt to perform action without client initialization"
            )
            return None

        try:
            # Post the tweet
            tweet = await self.twitter_client.tweet(text)

            if tweet:
                logger.success(f"{self.user} Tweet posted (ID: {tweet.id})")
                return tweet
            else:
                logger.warning(f"{self.user} Failed to post tweet")
                return None

        except Exception as e:
            logger.error(f"{self.user} Error posting tweet: {str(e)}")
            return None

    async def retweet(self, tweet_id: int) -> bool:
        """
        Retweets the specified tweet

        Args:
            tweet_id: ID of the tweet to retweet

        Returns:
            Success status
        """
        if not self.twitter_client:
            logger.error(
                f"{self.user} Attempt to perform action without client initialization"
            )
            return False

        try:
            # Perform retweet
            retweet_id = await self.twitter_client.repost(tweet_id)

            if retweet_id:
                logger.success(f"{self.user} Retweet successful")
                return True
            else:
                logger.warning(f"{self.user} Failed to retweet")
                return False

        except Exception as e:
            logger.error(f"{self.user} Error retweeting: {str(e)}")
            return False

    async def like_tweet(self, tweet_id: int) -> bool:
        """
        Likes the specified tweet

        Args:
            tweet_id: ID of the tweet to like

        Returns:
            Success status
        """
        if not self.twitter_client:
            logger.error(
                f"{self.user} Attempt to perform action without client initialization"
            )
            return False

        try:
            # Like the tweet
            is_liked = await self.twitter_client.like(tweet_id)

            if is_liked:
                logger.success(f"{self.user} Like successful")
                return True
            else:
                logger.warning(f"{self.user} Failed to like")
                return False

        except Exception as e:
            logger.error(f"{self.user} Error liking tweet: {str(e)}")
            return False

