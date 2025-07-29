import os
import random
import sys
from pathlib import Path
from typing import Dict, List

from loguru import logger
from dotenv import load_dotenv
import asyncio


load_dotenv()


if getattr(sys, 'frozen', False):
    ROOT_DIR = Path(sys.executable).parent.absolute()
else:
    ROOT_DIR = Path(__file__).parent.parent.absolute()

FILES_DIR = os.path.join(ROOT_DIR, 'files')
WALLETS_DB = os.path.join(FILES_DIR, 'wallets.db')

SALT_PATH = os.path.join(FILES_DIR, 'salt.dat')

CIPHER_SUITE = None