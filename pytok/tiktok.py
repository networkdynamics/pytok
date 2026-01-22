import asyncio
import json
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
import zendriver as zd
from zendriver import cdp

import random

from TikTokApi import TikTokApi
from TikTokApi.tiktok import TikTokPlaywrightSession
from TikTokApi.helpers import random_choice


class PatchedTikTokApi(TikTokApi):
    """TikTokApi subclass with updated session params to match browser behavior."""

    async def _TikTokApi__set_session_params(self, session: TikTokPlaywrightSession):
        """Override session params to match what browser actually sends."""
        user_agent = await session.page.evaluate("() => navigator.userAgent")
        language = await session.page.evaluate(
            "() => navigator.language || navigator.userLanguage"
        )
        platform = await session.page.evaluate("() => navigator.platform")
        device_id = str(random.randint(10**18, 10**19 - 1))
        odin_id = str(random.randint(10**18, 10**19 - 1))
        history_len = str(random.randint(1, 10))
        screen_height = str(random.randint(600, 1080))
        screen_width = str(random.randint(800, 1920))
        web_id_last_time = str(int(time.time()))
        timezone = await session.page.evaluate(
            "() => Intl.DateTimeFormat().resolvedOptions().timeZone"
        )

        browser_version = await session.page.evaluate(
            "() => navigator.appVersion"
        )

        os_name = platform.lower().split()[0] if platform else "windows"

        session_params = {
            "WebIdLastTime": web_id_last_time,
            "aid": "1988",
            "app_language": language,
            "app_name": "tiktok_web",
            "browser_language": language,
            "browser_name": "Mozilla",
            "browser_online": "true",
            "browser_platform": platform,
            "browser_version": browser_version,
            "channel": "tiktok_web",
            "cookie_enabled": "true",
            "data_collection_enabled": "false",
            "device_id": device_id,
            "device_platform": "web_pc",
            "focus_state": "true",
            "from_page": "user",
            "history_len": history_len,
            "is_fullscreen": "false",
            "is_page_visible": "true",
            "language": language,
            "odinId": odin_id,
            "os": os_name,
            "region": "US",
            "screen_height": screen_height,
            "screen_width": screen_width,
            "tz_name": timezone,
            "user_is_login": "false",
            "video_encoding": "mp4",
            "webcast_language": language,
        }
        session.params = session_params

    async def sign_url(self, url: str, **kwargs):
        """Sign a url with X-Bogus and X-Gnarly parameters."""
        try:
            i, session = await self._get_valid_session_index(**kwargs)
        except Exception:
            i, session = self._get_session(**kwargs)

        sign_result = await self.generate_x_bogus(url, session_index=i)

        x_bogus = sign_result.get("X-Bogus")
        if x_bogus is None:
            raise Exception("Failed to generate X-Bogus")

        if "?" in url:
            url += "&"
        else:
            url += "?"
        url += f"X-Bogus={x_bogus}"

        x_gnarly = sign_result.get("X-Gnarly")
        if x_gnarly:
            url += f"&X-Gnarly={x_gnarly}"

        return url

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


class PyTok:
    _is_context_manager = False
    user = User
    search = Search
    sound = Sound
    hashtag = Hashtag
    video = Video
    trending = Trending
    logger = logging.getLogger(LOGGER_NAME)

    # Default browser args for stealth
    _DEFAULT_BROWSER_ARGS = [
        '--disable-blink-features=AutomationControlled',
        '--disable-infobars',
        '--disable-dev-shm-usage',
        '--no-first-run',
        '--disable-background-networking',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
    ]

    def __init__(
            self,
            logging_level: int = logging.WARNING,
            request_delay: Optional[int] = 0,
            headless: Optional[bool] = False,
            browser: Optional[str] = "chromium",
            manual_captcha_solves: Optional[bool] = False,
            log_captcha_solves: Optional[bool] = False,
            num_sessions: int = 1,
            user_data_dir: Optional[str] = None,
            browser_args: Optional[list] = None,
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

        * user_data_dir: Path to Chrome user data directory for profile persistence, optional
            If not provided, uses a fresh profile each session. Set to your Chrome
            profile path (e.g., ~/.config/google-chrome) to reuse cookies/history.
            Note: Don't use a profile that's open in another Chrome instance.

        * browser_args: Additional Chrome command-line arguments, optional
            Merged with default stealth args. Pass empty list [] to disable defaults.
        """
        assert headless is False, "Running in headless currently does not work reliably."

        self._headless = headless
        self._request_delay = request_delay
        self._browser = browser
        self._manual_captcha_solves = manual_captcha_solves
        self._log_captcha_solves = log_captcha_solves
        self._num_sessions = num_sessions
        self._user_data_dir = user_data_dir
        # Merge browser args: use defaults unless explicitly disabled with empty list
        if browser_args is None:
            self._browser_args = self._DEFAULT_BROWSER_ARGS.copy()
        elif browser_args == []:
            self._browser_args = []
        else:
            self._browser_args = self._DEFAULT_BROWSER_ARGS + browser_args

        self.logger.setLevel(logging_level)

        # Add classes from the api folder
        User.parent = self
        Search.parent = self
        Sound.parent = self
        Hashtag.parent = self
        Video.parent = self
        Trending.parent = self

        self.request_cache = {}

        # Create TikTokApi instance for API requests (using patched version)
        self.tiktok_api = PatchedTikTokApi(
            logging_level=logging_level
        )

        if self._headless:
            from pyvirtualdisplay import Display
            self._display = Display()
            self._display.start()

    # URL patterns we care about - TikTok API and video media
    _TRACKED_URL_PATTERNS = [
        '/api/',           # TikTok API endpoints (comments, related videos, etc.)
        'video/tos',       # TikTok video CDN paths
        'v16-webapp',      # TikTok video CDN paths
        'v19-webapp',      # TikTok video CDN paths
    ]

    def _should_track_url(self, url: str) -> bool:
        """Check if URL matches patterns we want to track."""
        return any(pattern in url for pattern in self._TRACKED_URL_PATTERNS)

    def _on_response(self, event: cdp.network.ResponseReceived):
        """Handle network response events from CDP."""
        url = event.response.url
        # Early filter - only track URLs we care about
        if not self._should_track_url(url):
            return
        request_id = event.request_id
        self._pending_requests[request_id] = {
            'url': url,
            'ready': False,
            'response': event.response
        }

    def _on_loading_finished(self, event: cdp.network.LoadingFinished):
        """Handle when response body is ready - schedule immediate fetch."""
        request_id = event.request_id
        if request_id not in self._pending_requests:
            return

        info = self._pending_requests.pop(request_id)
        # Schedule async fetch - zendriver handlers don't await coroutines
        asyncio.create_task(self._fetch_response_body(request_id, info))

    async def _fetch_response_body(self, request_id, info):
        """Fetch response body immediately before Chrome GCs it."""
        try:
            result = await self._page.send(cdp.network.get_response_body(request_id))
            body = result[0] if isinstance(result, tuple) else result.body
            if body:
                self._collected_responses.append({
                    'url': info['url'],
                    'body': body,
                    'response': info['response']
                })
        except Exception:
            # Body may not be available (redirects, cached, etc.) - ignore silently
            pass

    async def process_pending_responses(self, url_pattern=None):
        """Return collected responses matching the URL pattern."""
        # Give a moment for any in-flight handlers to complete
        await asyncio.sleep(0.1)

        results = []
        remaining = []

        for resp in self._collected_responses:
            if url_pattern and url_pattern not in resp['url']:
                remaining.append(resp)
            else:
                results.append(resp)

        self._collected_responses = remaining
        return results

    async def __aenter__(self):
        # Initialize zendriver state for network response tracking
        self._pending_requests = {}
        self._collected_responses = []

        # Create zendriver browser instance for PyTok's scraping
        self._zendriver_browser = await zd.start(
            headless=self._headless,
            user_data_dir=self._user_data_dir,
            browser_args=self._browser_args if self._browser_args else None,
        )

        # Get a page and set up network tracking
        self._page = await self._zendriver_browser.get('about:blank')

        # Enable network tracking via CDP
        await self._page.send(cdp.network.enable())

        # Set up network event handlers
        self._page.add_handler(cdp.network.ResponseReceived, self._on_response)
        self._page.add_handler(cdp.network.LoadingFinished, self._on_loading_finished)

        # Navigate to TikTok (use CDP navigate + wait_for_ready_state to avoid hanging on slow resources)
        await self._page.send(cdp.page.navigate('https://www.tiktok.com'))
        await self._page.wait_for_ready_state(until='complete', timeout=10)
        await asyncio.sleep(3)

        # Get user agent from zendriver page
        self._user_agent = await self._page.evaluate("navigator.userAgent")

        # Create TikTok-Api sessions - let it use its own Playwright cookies
        # (passing zendriver's msToken was counterproductive since TikTok-Api
        # has its own browser session with its own valid msToken)
        suppress_resource_load_types = []
        await self.tiktok_api.create_sessions(
            num_sessions=self._num_sessions,
            headless=self._headless,
            browser=self._browser,
            suppress_resource_load_types=suppress_resource_load_types,
            starting_url='https://www.tiktok.com',
            override_browser_args=[
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
            ]
        )

        self._is_context_manager = True
        return self

    async def request_delay(self):
        if self._request_delay is not None:
            await asyncio.sleep(self._request_delay)

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
            # Close zendriver browser
            zendriver_browser = getattr(self, "_zendriver_browser", None)
            if zendriver_browser:
                await zendriver_browser.stop()
        except Exception:
            pass
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

    async def get_ms_tokens(self, retries=3, delay=2):
        # Use CDP to get cookies from zendriver, with retry logic
        cookie_name = 'msToken'
        for attempt in range(retries):
            result = await self._page.send(cdp.network.get_cookies())
            all_cookies = result
            cookies = []
            for cookie in all_cookies:
                if cookie.name == cookie_name and cookie.secure:
                    cookies.append(cookie.value)
            if cookies:
                return cookies
            if attempt < retries - 1:
                self.logger.debug(f"msToken not found, retrying in {delay}s (attempt {attempt + 1}/{retries})")
                await asyncio.sleep(delay)
        raise Exception(f"Could not find {cookie_name} cookie after {retries} attempts")

    async def login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 300,
        wait_for_input: bool = False
    ) -> bool:
        """Log in to TikTok with username/email and password.

        If credentials are provided, attempts automatic login. Otherwise,
        opens the login page for manual login.

        Note: TikTok often requires additional verification (email/SMS code)
        after entering credentials. When this happens, the automatic login
        will fill in the credentials and click the login button, but you'll
        need to manually complete the verification step in the browser window.
        The method will wait up to `timeout` seconds for login to complete.

        Parameters
        ----------
        username : str, optional
            TikTok username or email address
        password : str, optional
            Account password
        timeout : int, optional
            Maximum time in seconds to wait for login completion (default: 300)
        wait_for_input : bool, optional
            If True (default), waits for you to press Enter after logging in
            manually. If False, polls for login cookies until timeout.

        Returns
        -------
        bool
            True if login was successful

        Raises
        ------
        TimeoutException
            If login is not completed within the timeout period
        LoginException
            If automatic login fails (e.g., invalid credentials)
        """
        if await self._is_logged_in():
            self.logger.info("Already logged in.")
            return True

        login_url = 'https://www.tiktok.com/login/phone-or-email/email'

        # Navigate to login page
        await self._page.send(cdp.page.navigate(login_url))
        await self._page.wait_for_ready_state(until='complete', timeout=30)
        await asyncio.sleep(2)

        if username and password:
            return await self._automatic_login(username, password, timeout)
        else:
            return await self._manual_login(timeout, wait_for_input)

    async def _manual_login(self, timeout: int, wait_for_input: bool = False) -> bool:
        """Wait for user to complete manual login."""
        self.logger.info("Please complete the login process in the browser window...")

        if wait_for_input:
            input("Press Enter after you've logged in...")
            if not await self._is_logged_in():
                raise LoginException("Login failed - no session cookies found")
            await self._refresh_api_tokens()
            self.logger.info("Login complete.")
            return True

        start_time = time.time()
        while time.time() - start_time < timeout:
            if await self._is_logged_in():
                self.logger.info("Login successful!")
                return True
            await asyncio.sleep(2)

        raise TimeoutException(f"Login not completed within {timeout} seconds")

    async def _automatic_login(self, username: str, password: str, timeout: int) -> bool:
        """Perform automatic login with credentials."""
        self.logger.info("Attempting automatic login...")

        # Find and click username field
        username_input = await self._find_login_element(
            'input[name="username"]',
            'input[placeholder*="Email" i]',
            'input[placeholder*="Username" i]',
            'input[type="text"]'
        )
        if not username_input:
            raise LoginException("Could not find username input field")

        self.logger.info("Found username field, entering username...")
        await username_input.mouse_click()
        await asyncio.sleep(0.5)

        # Use element's send_keys method
        await username_input.send_keys(username)
        await asyncio.sleep(0.5)

        # Find and click password field
        password_input = await self._find_login_element(
            'input[name="password"]',
            'input[type="password"]'
        )
        if not password_input:
            raise LoginException("Could not find password input field")

        self.logger.info("Found password field, entering password...")
        await password_input.mouse_click()
        await asyncio.sleep(0.5)

        # Use element's send_keys method
        await password_input.send_keys(password)
        await asyncio.sleep(1)

        # Find and click login button using CDP mouse events (most reliable)
        self.logger.info("Clicking login button...")
        box = await self._page.evaluate("""
            (() => {
                const btn = document.querySelector('button[data-e2e="login-button"]') ||
                           document.querySelector('button[type="submit"]');
                if (btn) {
                    const rect = btn.getBoundingClientRect();
                    return { x: rect.x + rect.width/2, y: rect.y + rect.height/2 };
                }
                return null;
            })()
        """)
        if box:
            await self._page.send(cdp.input_.dispatch_mouse_event(
                type_='mousePressed',
                x=box['x'],
                y=box['y'],
                button=cdp.input_.MouseButton.LEFT,
                click_count=1
            ))
            await self._page.send(cdp.input_.dispatch_mouse_event(
                type_='mouseReleased',
                x=box['x'],
                y=box['y'],
                button=cdp.input_.MouseButton.LEFT,
                click_count=1
            ))
        else:
            # Fallback: press Enter in password field
            self.logger.info("Login button not found, pressing Enter...")
            await password_input.send_keys('\n')

        await asyncio.sleep(3)

        # Handle captcha if it appears
        await self._handle_login_captcha()

        # Wait for login to complete
        start_time = time.time()
        check_count = 0
        while time.time() - start_time < timeout:
            check_count += 1
            # Check for login errors
            error_message = await self._check_login_error()
            if error_message:
                raise LoginException(f"Login failed: {error_message}")

            if await self._is_logged_in():
                self.logger.info("Login successful!")
                # Refresh ms_tokens after login
                await self._refresh_api_tokens()
                return True

            # Check for captcha again (may appear after initial attempt)
            await self._handle_login_captcha()

            # Log current URL periodically
            if check_count % 5 == 0:
                current_url = self._page.url
                self.logger.info(f"Waiting for login... current URL: {current_url}")

            await asyncio.sleep(2)

        raise TimeoutException(f"Login not completed within {timeout} seconds")

    async def _find_login_element(self, *selectors):
        """Try multiple selectors to find a login form element."""
        for selector in selectors:
            try:
                element = await self._page.select(selector, timeout=2)
                if element:
                    return element
            except Exception:
                continue
        return None

    async def _handle_login_captcha(self):
        """Check for and solve captcha during login."""
        from .api.base import CAPTCHA_TEXTS

        for text in CAPTCHA_TEXTS:
            try:
                element = await self._page.find(text, timeout=1)
                if element:
                    self.logger.info(f"Captcha detected during login: '{text}'")
                    if self._manual_captcha_solves:
                        input("Press Enter after solving the captcha manually...")
                        await asyncio.sleep(1)
                        return
                    # Use the Base class captcha solver
                    from .api.base import Base
                    base = Base()
                    base.parent = self
                    try:
                        await base.solve_captcha()
                        self.logger.info("Captcha solve attempt completed")
                    except Exception as e:
                        self.logger.warning(f"Captcha solve failed: {e}")
                    await asyncio.sleep(2)
                    return
            except Exception as e:
                self.logger.debug(f"Error checking for captcha text '{text}': {e}")
                continue

    async def _check_login_error(self) -> Optional[str]:
        """Check for login error messages on the page."""
        # Look for error messages in specific error containers
        error_selectors = [
            '[class*="error" i]',
            '[class*="alert" i]',
            '[data-e2e*="error" i]',
        ]
        error_texts = [
            "incorrect password",
            "invalid username",
            "account doesn't exist",
            "too many attempts",
            "something went wrong",
            "please check your password",
        ]

        for selector in error_selectors:
            try:
                elements = await self._page.select_all(selector, timeout=0.5)
                for element in elements:
                    if hasattr(element, 'text') and element.text:
                        text_lower = element.text.lower()
                        for error_text in error_texts:
                            if error_text in text_lower:
                                return element.text
            except Exception:
                continue
        return None

    async def _get_cookies_for_playwright(self):
        """Get all cookies from zendriver in playwright format."""
        cdp_cookies = await self._page.send(cdp.network.get_cookies())
        playwright_cookies = []
        for c in cdp_cookies:
            cookie = {
                'name': c.name,
                'value': c.value,
                'domain': c.domain,
                'path': c.path,
                'httpOnly': c.http_only,
                'secure': c.secure,
            }
            if c.expires:
                cookie['expires'] = c.expires
            if c.same_site:
                cookie['sameSite'] = c.same_site.value.capitalize()
            playwright_cookies.append(cookie)
        return playwright_cookies

    async def _refresh_api_tokens(self):
        """Refresh session cookies for TikTok-Api after login."""
        try:
            cookies = await self._get_cookies_for_playwright()

            # Update TikTok-Api sessions with cookies from zendriver
            # (don't set session.ms_token - let TikTok-Api use its own Playwright cookies)
            for session in self.tiktok_api.sessions:
                await self.tiktok_api.set_session_cookies(session, cookies)

            self.logger.debug(f"Refreshed {len(cookies)} cookies after login")
        except Exception as e:
            self.logger.warning(f"Failed to refresh API cookies: {e}")

    async def _is_logged_in(self) -> bool:
        """Check if user is logged in by looking for session cookies."""
        result = await self._page.send(cdp.network.get_cookies())
        cookie_names = {cookie.name for cookie in result}
        # TikTok sets these cookies when logged in
        login_cookies = {'sessionid', 'sid_tt', 'sessionid_ss'}
        return bool(cookie_names & login_cookies)
