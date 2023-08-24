import json
import logging
import os
import threading
import asyncio
import random
import re
import string
import time
from typing import ClassVar, Optional
from urllib import request
from urllib.parse import quote, urlencode

import pyvirtualdisplay
from selenium import webdriver
import seleniumwire.undetected_chromedriver as uc

from .api.sound import Sound
from .api.user import User
from .api.search import Search
from .api.hashtag import Hashtag
from .api.video import Video
from .api.trending import Trending

from .exceptions import *
from .utils import LOGGER_NAME
from dataclasses import dataclass

os.environ["no_proxy"] = "127.0.0.1,localhost"

BASE_URL = "https://m.tiktok.com/"
DESKTOP_BASE_URL = "https://www.tiktok.com/"


class PyTok:
    _is_context_manager = False
    user = User
    search = Search
    sound = Sound
    hashtag = Hashtag
    video = Video
    trending = Trending
    logger = logging.getLogger(LOGGER_NAME)

    def __init__(
        self,
        logging_level: int = logging.WARNING,
        request_delay: Optional[int] = 0,
        headless: Optional[bool] = False,
        chromedriver_path: Optional[str] = None,
        chrome_version: Optional[int] = 102
    ):
        """The PyTok class. Used to interact with TikTok. This is a singleton
            class to prevent issues from arising with playwright

        ##### Parameters
        * logging_level: The logging level you want the program to run at, optional
            These are the standard python logging module's levels.

        * request_delay: The amount of time in seconds to wait before making a request, optional
            This is used to throttle your own requests as you may end up making too
            many requests to TikTok for your IP.

        * **kwargs
            Parameters that are passed on to basically every module and methods
            that interact with this main class. These may or may not be documented
            in other places.
        """

        self._headless = headless
        self._chrome_version = chrome_version
        self._request_delay = request_delay

        self.logger.setLevel(logging_level)

        # Add classes from the api folder
        User.parent = self
        Search.parent = self
        Sound.parent = self
        Hashtag.parent = self
        Video.parent = self
        Trending.parent = self

        self.request_cache = {}

        if self._headless:
            self._display = pyvirtualdisplay.Display()
            self._display.start()

        options = uc.ChromeOptions()
        options.add_argument('--ignore-ssl-errors=yes')
        options.add_argument('--ignore-certificate-errors')
        # options.page_load_strategy = 'eager'
        # if self._headless:
        #     options.add_argument('--headless=new')
        #     options.add_argument("--window-size=1920,1080")
        kwargs = {"options": options}
        if chromedriver_path:
            kwargs["driver_executable_path"] = chromedriver_path
        self._browser = uc.Chrome(**kwargs)
        self._user_agent = self._browser.execute_script("return navigator.userAgent")

    def request_delay(self):
        if self._request_delay is not None:
            time.sleep(self._request_delay)

    
    def __del__(self):
        """A basic cleanup method, called automatically from the code"""
        if not self._is_context_manager:
            self.logger.debug(
                "PyTok was shutdown improperlly. Ensure the instance is terminated with .shutdown()"
            )
            self.shutdown()
        return

    #
    # PRIVATE METHODS
    #

    def r1(self, pattern, text):
        m = re.search(pattern, text)
        if m:
            return m.group(1)

    def shutdown(self) -> None:
        try:
            self._browser.close()
        except Exception:
            pass
        finally:
            if getattr(self, "_browser", None):
                self._browser.quit()
            if self._headless:
                self._display.stop()

    def __enter__(self):
        self._is_context_manager = True
        return self

    def __exit__(self, type, value, traceback):
        self.shutdown()
