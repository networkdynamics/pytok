from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Iterator, Type
from urllib.parse import urlencode

import seleniumwire
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from .user import User
from .sound import Sound
from .hashtag import Hashtag
from .video import Video
from .base import Base
from ..exceptions import *

if TYPE_CHECKING:
    from ..tiktok import TikTokApi



class Search(Base):
    """Contains static methods about searching."""

    parent: TikTokApi

    def __init__(self, search_term):
        self.search_term = search_term

    def videos(self, count=28, offset=0, **kwargs) -> Iterator[Video]:
        """
        Searches for Videos

        - Parameters:
            - search_term (str): The phrase you want to search for.
            - count (int): The amount of videos you want returned.
            - offset (int): The offset of videos from your data you want returned.

        Example Usage
        ```py
        for video in api.search.videos('therock'):
            # do something
        ```
        """
        return self.search_type(
            "item", count=count, offset=offset, **kwargs
        )

    def users(self, count=28, offset=0, **kwargs) -> Iterator[User]:
        """
        Searches for users using an alternate endpoint than Search.users

        - Parameters:
            - search_term (str): The phrase you want to search for.
            - count (int): The amount of videos you want returned.

        Example Usage
        ```py
        for user in api.search.users_alternate('therock'):
            # do something
        ```
        """
        return self.search_type(
            "user", count=count, offset=offset, **kwargs
        )

    def search_type(self, obj_type, count=28, offset=0, **kwargs) -> Iterator:
        """
        Searches for users using an alternate endpoint than Search.users

        - Parameters:
            - search_term (str): The phrase you want to search for.
            - count (int): The amount of videos you want returned.
            - obj_type (str): user | item

        Just use .video & .users
        ```
        """

        if obj_type == "user":
            subdomain = "www"
            subpath = "user"
        elif obj_type == "item":
            subdomain = "us"
            subpath = "video"
        else:
            raise TypeError("invalid obj_type")

        driver = Search.parent._browser

        driver.get(f"https://{subdomain}.tiktok.com/search/{subpath}?q={self.search_term}")

        toks_delay = 10
        CAPTCHA_WAIT = 999999

        WebDriverWait(driver, toks_delay).until(EC.any_of(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e=search_video-item]')), EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container'))))

        if driver.find_elements(By.CLASS_NAME, 'captcha_verify_container'):
            WebDriverWait(driver, CAPTCHA_WAIT).until_not(EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container')))

        processed_urls = []
        num_fetched = 0
        while num_fetched < count:

            path = f"api/search/{obj_type}"
            WebDriverWait(driver, toks_delay).until_not(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e=video-skeleton-container]')))
            search_requests = [request for request in driver.requests if path in request.url and request.response is not None and request.url not in processed_urls]
            for request in search_requests:
                processed_urls.append(request.url)
                body_bytes = seleniumwire.utils.decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity'))
                body = body_bytes.decode('utf-8')
                api_response = json.loads(body)
                if api_response.get('type') == 'verify':
                    # this is the captcha denied response
                    continue

                # When I move to 3.10+ support make this a match switch.
                if obj_type == "user":
                    for result in api_response.get("user_list", []):
                        yield User(data=result)
                        num_fetched += 1

                if obj_type == "item":
                    for result in api_response.get("item_list", []):
                        yield Video(data=result)
                        num_fetched += 1

                if api_response.get("has_more", 0) == 0:
                    Search.parent.logger.info(
                        "TikTok is not sending videos beyond this point."
                    )
                    return

            #vid_results = driver.find_element(by=By.CSS_SELECTOR, value="[data-e2e=search_video-item-list]")

            self.check_and_wait_for_captcha()

            load_more_button = driver.find_element(by=By.CSS_SELECTOR, value="[data-e2e=search-load-more]")
            load_more_button.click()
            time.sleep(toks_delay)

            self.check_and_wait_for_captcha()

