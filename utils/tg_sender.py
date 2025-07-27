from curl_cffi.requests import AsyncSession
from loguru import logger

import settings

BOT_ID = settings.TG_BOT_ID
ID = settings.TG_USER_ID

async def tg_sender(msg=None):
    bot_id = BOT_ID
    id = ID
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        msg = msg.replace(char, f'\\{char}')

    try:
        json_data = {
            'parse_mode':'MarkdownV2',
            'chat_id': id,
            'text': msg
        }
        url = f'https://api.telegram.org/bot{bot_id}/sendMessage'

        async with AsyncSession() as session:
            r = await session.post(url=url, json=json_data)

            return r.json()

    except Exception as err:
        logger.error(f'Send Telegram message error |{err} | {msg}')