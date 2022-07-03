from __future__ import annotations
import logging

from urllib.parse import urlencode
from ..exceptions import *
import re
import json
import time

from typing import TYPE_CHECKING, ClassVar, Iterator, Optional

import requests
import seleniumwire
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

if TYPE_CHECKING:
    from ..tiktok import TikTokApi
    from .video import Video


class Hashtag:
    """
    A TikTok Hashtag/Challenge.

    Example Usage
    ```py
    hashtag = api.hashtag(name='funny')
    ```
    """

    parent: ClassVar[TikTokApi]

    id: Optional[str]
    """The ID of the hashtag"""
    name: Optional[str]
    """The name of the hashtag (omiting the #)"""
    as_dict: dict
    """The raw data associated with this hashtag."""

    def __init__(
        self,
        name: Optional[str] = None,
        id: Optional[str] = None,
        data: Optional[dict] = None,
    ):
        """
        You must provide the name or id of the hashtag.
        """
        self.name = name
        self.id = id

        if data is not None:
            self.as_dict = data
            self.__extract_from_data()

    def info(self, **kwargs) -> dict:
        """
        Returns TikTok's dictionary representation of the hashtag object.
        """
        return self.info_full(**kwargs)["challengeInfo"]["challenge"]

    def info_full(self, **kwargs) -> dict:
        """
        Returns all information sent by TikTok related to this hashtag.

        Example Usage
        ```py
        hashtag_data = api.hashtag(name='funny').info_full()
        ```
        """
        processed = self.parent._process_kwargs(kwargs)
        kwargs["custom_device_id"] = processed.device_id

        if self.name is not None:
            query = {"challengeName": self.name}
        elif self.id is not None:
            query = {"challengeId": self.id}
        else:
            self.parent.logger.warning("Malformed Hashtag Object")
            return {}

        path = "api/challenge/detail/?{}&{}".format(
            self.parent._add_url_params(), urlencode(query)
        )

        data = self.parent.get_data(path, **kwargs)

        if data["challengeInfo"].get("challenge") is None:
            raise NotFoundException("Challenge {} does not exist".format(self.name))

        return data

    def videos(self, count=30, offset=0, **kwargs) -> Iterator[Video]:
        """Returns a dictionary listing TikToks with a specific hashtag.

        - Parameters:
            - count (int): The amount of videos you want returned.
            - offset (int): The the offset of videos from 0 you want to get.

        Example Usage
        ```py
        for video in api.hashtag(name='funny').videos():
            # do something
        ```
        """
        driver = self.parent._browser

        driver.get(f"https://www.tiktok.com/tag/{self.name}")

        toks_delay = 10
        CAPTCHA_WAIT = 999999

        WebDriverWait(driver, toks_delay).until(EC.any_of(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e=challenge-item]')), EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container'))))

        if driver.find_elements(By.CLASS_NAME, 'captcha_verify_container'):
            WebDriverWait(driver, CAPTCHA_WAIT).until_not(EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container')))
        
        WebDriverWait(driver, toks_delay).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e=challenge-item]')))

        amount_yielded = 0

        path = "api/challenge/item_list"
        request = [request for request in driver.requests if path in request.url and request.response is not None][-1]

        body_bytes = seleniumwire.utils.decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity'))
        body = body_bytes.decode('utf-8')

        res = json.loads(body)

        while amount_yielded < count:
            
            videos = res.get("itemList", [])

            amount_yielded += len(videos)
            for video in videos:
                yield self.parent.video(data=video)

            if not res.get("hasMore", False):
                self.parent.logger.info(
                    "TikTok isn't sending more TikToks beyond this point."
                )
                return

            cursor = res["cursor"]
            next_url = re.sub("cursor=([0-9]+)", f"cursor={cursor}", request.url)

            r = requests.get(next_url, headers=request.headers)
            res = r.json()

            if res.get('type') == 'verify':
                if driver.find_elements(By.CLASS_NAME, 'captcha_verify_container'):
                    WebDriverWait(driver, CAPTCHA_WAIT).until_not(EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container')))
                else:
                    raise TikTokException("Captcha requested but not found in browser")

            self.parent.request_delay()

    def __extract_from_data(self):
        data = self.as_dict
        keys = data.keys()

        if "title" in keys:
            self.id = data["id"]
            self.name = data["title"]

        if None in (self.name, self.id):
            Hashtag.parent.logger.error(
                f"Failed to create Hashtag with data: {data}\nwhich has keys {data.keys()}"
            )

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"TikTokApi.hashtag(id='{self.id}', name='{self.name}')"

    def __getattr__(self, name):
        # TODO: Maybe switch to using @property instead
        if name in ["id", "name", "as_dict"]:
            self.as_dict = self.info()
            self.__extract_from_data()
            return self.__getattribute__(name)

        raise AttributeError(f"{name} doesn't exist on TikTokApi.api.Hashtag")
