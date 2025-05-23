import logging
import os
import re
import time
from typing import Optional

from patchright.async_api import async_playwright

from .api.sound import Sound
from .api.user import User
from .api.search import Search
from .api.hashtag import Hashtag
from .api.video import Video
from .api.trending import Trending

from .exceptions import *
from .utils import LOGGER_NAME
from .captcha_solver import CaptchaSolver
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
            browser: Optional[str] = "chromium",
            manual_captcha_solves: Optional[bool] = False,
            log_captcha_solves: Optional[bool] = False,
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
        self._request_delay = request_delay
        self._browser = browser
        self._manual_captcha_solves = manual_captcha_solves
        self._log_captcha_solves = log_captcha_solves

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
            from pyvirtualdisplay import Display
            self._display = Display()
            self._display.start()

        # options = uc.ChromeOptions()
        # options.add_argument('--ignore-ssl-errors=yes')
        # options.add_argument('--ignore-certificate-errors')
        # # options.page_load_strategy = 'eager'

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        fingerprint_options = {}
        if self._browser == "firefox":
            self._browser = await self._playwright.firefox.launch(headless=self._headless)
            # fingerprint_options['browser'] = [ForgeBrowser("firefox")]
        elif self._browser == "chromium":
            self._browser = await self._playwright.chromium.launch(
                # user_data_dir="...",
                channel="chrome",
                headless=False,
                # no_viewport=True,
                # do NOT add custom browser headers or user_agent
            )
            # fingerprint_options['browser'] = 'chrome'
        else:
            raise Exception("Browser not supported")
        # self._context = await AsyncNewContext(self._browser, fingerprint_options=fingerprint_options)
        # device_config = self._playwright.devices['Desktop Chrome']
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()

        # move mouse to 0, 0 to have known mouse start position
        await self._page.mouse.move(0, 0)

        self._requests = []
        self._responses = []

        self._page.on("request", lambda request: self._requests.append(request))

        async def save_responses_and_body(response):
            self._responses.append(response)
            try:
                response._body = await response.body()
            except Exception:
                pass

        self._page.on("response", save_responses_and_body)

        self._user_agent = await self._page.evaluate("() => navigator.userAgent")
        self._is_context_manager = True
        return self

    async def request_delay(self):
        if self._request_delay is not None:
            await self._page.wait_for_timeout(self._request_delay * 1000)

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

    async def shutdown(self) -> None:
        try:
            await self._context.close()
            await self._browser.close()
            await self._playwright.stop()
        except Exception:
            pass
        finally:
            if self._headless:
                display = getattr(self, "_display", None)
                if display:
                    display.stop()

    async def __aexit__(self, type, value, traceback):
        await self.shutdown()

    async def get_ms_tokens(self):
        all_cookies = await self._context.cookies()
        cookie_name = 'msToken'
        cookies = []
        for cookie in all_cookies:
            if cookie["name"] == cookie_name and cookie['secure']:
                cookies.append(cookie['value'])
        if len(cookies) == 0:
            raise Exception(f"Could not find {cookie_name} cookie")
        return cookies
