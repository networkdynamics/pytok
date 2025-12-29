import asyncio
import logging
import os
import re
import time
from typing import Any, Awaitable, Callable, Optional

from patchright.async_api import (
    async_playwright,
    BrowserContext,
    Playwright,
    Page,
    ProxySettings
)
from proxyproviders import ProxyProvider
from proxyproviders.algorithms import Algorithm

from TikTokApi import TikTokApi
from TikTokApi.helpers import random_choice

from .api.sound import Sound
from .api.user import User
from .api.search import Search
from .api.hashtag import Hashtag
from .api.video import Video
from .api.trending import Trending

from .exceptions import *
from .utils import LOGGER_NAME

os.environ["no_proxy"] = "127.0.0.1,localhost"

BASE_URL = "https://m.tiktok.com/"
DESKTOP_BASE_URL = "https://www.tiktok.com/"

class PatchrightTikTokApi(TikTokApi):
    async def create_sessions(
        self,
        num_sessions: int = 5,
        headless: bool = True,
        ms_tokens: list[str] | None = None,
        proxies: list[dict[str, Any] | ProxySettings] | None = None,
        proxy_provider: Optional[ProxyProvider] = None,
        proxy_algorithm: Optional[Algorithm] = None,
        sleep_after: int = 1,
        starting_url: str = "https://www.tiktok.com",
        context_options: dict[str, Any] = {},
        override_browser_args: list[str] | None = None,
        cookies: list[dict[str, Any]] | None = None,
        suppress_resource_load_types: list[str] | None = None,
        browser: str = "chromium",
        executable_path: str | None = None,
        page_factory: Callable[[BrowserContext], Awaitable[Page]] | None = None,
        browser_context_factory: (
            Callable[[Playwright], Awaitable[BrowserContext]] | None
        ) = None,
        timeout: int = 30000,
        enable_session_recovery: bool = True,
        allow_partial_sessions: bool = False,
        min_sessions: int | None = None,
    ):
        """
        Create sessions for use within the TikTokApi class.

        These sessions are what will carry out requesting your data from TikTok.

        Args:
            num_sessions (int): The amount of sessions you want to create.
            headless (bool): Whether or not you want the browser to be headless.
            ms_tokens (list[str]): A list of msTokens to use for the sessions, you can get these from your cookies after visiting TikTok.
                                   If you don't provide any, the sessions will try to get them themselves, but this is not guaranteed to work.
            proxies (list): **DEPRECATED - Use proxy_provider instead.** A list of proxies to use for the sessions.
                           This parameter is maintained for backwards compatibility but will be removed in a future version.
            proxy_provider (ProxyProvider | None): A ProxyProvider instance for smart proxy rotation.
                                                   See examples/proxy_provider_example.py for usage examples. Full documentation: https://davidteather.github.io/proxyproviders/
            proxy_algorithm (Algorithm | None): Algorithm for proxy selection (RoundRobin, Random, First, or custom) per session.
                                               Only used with proxy_provider. Defaults to RoundRobin if not specified.
            sleep_after (int): The amount of time to sleep after creating a session, this is to allow the msToken to be generated.
            starting_url (str): The url to start the sessions on, this is usually https://www.tiktok.com.
            context_options (dict): Options to pass to the playwright context.
            override_browser_args (list[dict]): A list of dictionaries containing arguments to pass to the browser.
            cookies (list[dict]): A list of cookies to use for the sessions, you can get these from your cookies after visiting TikTok.
            suppress_resource_load_types (list[str]): Types of resources to suppress playwright from loading, excluding more types will make playwright faster.. Types: document, stylesheet, image, media, font, script, textrack, xhr, fetch, eventsource, websocket, manifest, other.
            browser (str): firefox, chromium, or webkit; default is chromium
            executable_path (str): Path to the browser executable
            page_factory (Callable[[BrowserContext], Awaitable[Page]]) | None: Optional async function for instantiating pages.
            browser_context_factory (Callable[[Playwright], Awaitable[BrowserContext]]) | None: Optional async function for creating browser contexts. When provided, you can choose any browser (chromium/firefox/webkit) inside the factory, and the 'browser' parameter is ignored.
            timeout (int): The timeout in milliseconds for page navigation
            enable_session_recovery (bool): Enable automatic session recovery on failures (default: True)
            allow_partial_sessions (bool): If True, succeed even if some sessions fail to create. If False (default), fail if any session fails
            min_sessions (int | None): Minimum number of sessions required. Only used if allow_partial_sessions=True. If None, defaults to 1.

        Example Usage:
            .. code-block:: python

                from TikTokApi import TikTokApi

                async with TikTokApi() as api:
                    await api.create_sessions(num_sessions=5, ms_tokens=['msToken1', 'msToken2'])

        Proxy Provider Usage:
            For proxy provider examples with different algorithms and configurations,
            see examples/proxy_provider_example.py

        Custom Launchers:
            To implement custom functionality, such as login or captcha solving, when the session is being created,
            you may use the keyword arguments `browser_context_factory` and `page_factory`.
            These arguments are callable functions that TikTok-Api will use to launch your browser and pages,
            and allow you to perform custom actions on the page before the session is created.
            You can find examples in the test file: tests/test_custom_launchers.py
        """
        self._session_recovery_enabled = enable_session_recovery
        self._proxy_provider = proxy_provider
        self._proxy_algorithm = proxy_algorithm

        if proxies is not None and proxy_provider is not None:
            raise ValueError(
                "Cannot use both 'proxies' and 'proxy_provider' parameters. "
                "Please use 'proxy_provider' (recommended) or 'proxies' (deprecated)."
            )

        self.playwright = await async_playwright().start()
        if browser_context_factory is not None:
            self.browser = await browser_context_factory(self.playwright)
        elif browser == "chromium":
            if headless and override_browser_args is None:
                override_browser_args = ["--headless=new"]
                headless = False  # managed by the arg
            self.browser = await self.playwright.chromium.launch(
                channel='chrome',
                headless=headless,
                args=override_browser_args,
                proxy=random_choice(proxies),
                executable_path=executable_path,
            )
        elif browser == "firefox":
            self.browser = await self.playwright.firefox.launch(
                headless=headless,
                args=override_browser_args,
                proxy=random_choice(proxies),
                executable_path=executable_path,
            )
        elif browser == "webkit":
            self.browser = await self.playwright.webkit.launch(
                headless=headless,
                args=override_browser_args,
                proxy=random_choice(proxies),
                executable_path=executable_path,
            )
        else:
            raise ValueError("Invalid browser argument passed")

        # Create sessions concurrently
        # Use return_exceptions only if partial sessions are allowed
        if allow_partial_sessions:
            results = await asyncio.gather(
                *(
                    self._TikTokApi__create_session(
                        proxy=(
                            random_choice(proxies) if proxy_provider is None else None
                        ),
                        ms_token=random_choice(ms_tokens),
                        url=starting_url,
                        context_options=context_options,
                        sleep_after=sleep_after,
                        cookies=random_choice(cookies),
                        suppress_resource_load_types=suppress_resource_load_types,
                        timeout=timeout,
                        page_factory=page_factory,
                        browser_context_factory=browser_context_factory,
                    )
                    for _ in range(num_sessions)
                ),
                return_exceptions=True,
            )

            # Count failures and provide feedback
            failed_count = sum(1 for r in results if isinstance(r, Exception))
            success_count = len(self.sessions)
            minimum_required = min_sessions if min_sessions is not None else 1

            if success_count < minimum_required:
                # Didn't meet minimum requirements
                error_messages = [str(r) for r in results if isinstance(r, Exception)]
                raise Exception(
                    f"Failed to create minimum required sessions. "
                    f"Created {success_count}/{num_sessions}, needed at least {minimum_required}.\n"
                    f"Errors: {error_messages[:3]}"  # Show first 3 errors
                )
            elif failed_count > 0:
                # Some sessions failed but we have enough - log warning and continue
                self.logger.warning(
                    f"Created {success_count}/{num_sessions} sessions successfully. "
                    f"{failed_count} session(s) failed to create."
                )
                # Log individual errors at debug level
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.debug(f"Session {i} creation failed: {result}")
        else:
            await asyncio.gather(
                *(
                    self._TikTokApi__create_session(
                        proxy=(
                            random_choice(proxies) if proxy_provider is None else None
                        ),
                        ms_token=random_choice(ms_tokens),
                        url=starting_url,
                        context_options=context_options,
                        sleep_after=sleep_after,
                        cookies=random_choice(cookies),
                        suppress_resource_load_types=suppress_resource_load_types,
                        timeout=timeout,
                        page_factory=page_factory,
                        browser_context_factory=browser_context_factory,
                    )
                    for _ in range(num_sessions)
                )
            )

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
            num_sessions: int = 1,
    ):
        """The PyTok class. Used to interact with TikTok. This is a singleton
            class to prevent issues from arising with playwright

        ##### Parameters
        * logging_level: The logging level you want the program to run at, optional
            These are the standard python logging module's levels.

        * request_delay: The amount of time in seconds to wait before making a request, optional
            This is used to throttle your own requests as you may end up making too
            many requests to TikTok for your IP.

        * num_sessions: Number of browser sessions to create (used by TikTok-Api), optional

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
        self._num_sessions = num_sessions

        self.logger.setLevel(logging_level)

        # Add classes from the api folder
        User.parent = self
        Search.parent = self
        Sound.parent = self
        Hashtag.parent = self
        Video.parent = self
        Trending.parent = self

        self.request_cache = {}

        # Create TikTokApi instance for API requests
        self.tiktok_api = PatchrightTikTokApi(logging_level=logging_level)

        if self._headless:
            from pyvirtualdisplay import Display
            self._display = Display()
            self._display.start()

        # options = uc.ChromeOptions()
        # options.add_argument('--ignore-ssl-errors=yes')
        # options.add_argument('--ignore-certificate-errors')
        # # options.page_load_strategy = 'eager'

    async def __aenter__(self):
        # Create TikTok-Api sessions
        # suppress_resource_load_types = ['document', 'stylesheet', 'image', 'media', 'font', 'script', 'textrack', 'xhr', 'fetch', 'eventsource', 'websocket', 'manifest', 'other']
        suppress_resource_load_types = []
        await self.tiktok_api.create_sessions(
            num_sessions=self._num_sessions,
            headless=self._headless,
            browser=self._browser,
            suppress_resource_load_types=suppress_resource_load_types,
            starting_url='https://www.tiktok.com',
        )

        # Use TikTok-Api's browser and playwright, but create a separate context
        # for PyTok's scraping - this keeps TikTokApi's session untouched for signing
        self._playwright = self.tiktok_api.playwright
        self._browser = self.tiktok_api.browser
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        await self._page.goto('https://www.tiktok.com')

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
            # Close TikTok-Api sessions (which closes browser, contexts, and playwright)
            await self.tiktok_api.close_sessions()
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
