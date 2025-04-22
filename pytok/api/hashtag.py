from __future__ import annotations

import json
import urllib.parse

from typing import TYPE_CHECKING, ClassVar, Iterator, Optional

import requests

if TYPE_CHECKING:
    from ..tiktok import PyTok
    from .video import Video

from .base import Base
from ..helpers import edit_url, extract_tag_contents
from ..exceptions import *


class Hashtag(Base):
    """
    A TikTok Hashtag/Challenge.

    Example Usage
    ```py
    hashtag = api.hashtag(name='funny')
    ```
    """

    parent: ClassVar[PyTok]

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
        else:
            self.as_dict = None

    async def info(self, **kwargs) -> dict:
        """
        Returns TikTok's dictionary representation of the hashtag object.
        """
        if self.as_dict is None:
            return await self.info_full(**kwargs)
        return self.as_dict

    async def info_full(self, **kwargs) -> dict:
        """
        Returns all information sent by TikTok related to this hashtag.

        Example Usage
        ```py
        hashtag_data = api.hashtag(name='funny').info_full()
        ```
        """
        page = self.parent._page

        url = f"https://www.tiktok.com/tag/{self.name}"
        await page.goto(url)

        await self.wait_for_content_or_unavailable_or_captcha('[data-e2e=challenge-item]', 'Not available')
        await self.check_and_close_signin()

        challenge_responses = self.get_responses("api/challenge/detail")
        challenge_responses = [request for request in challenge_responses if f"challengeName={urllib.parse.quote_plus(self.name)}" in request.url]
        if len(challenge_responses) == 0:
            raise ApiFailedException("Failed to get challenge request")
        else:
            challenge_response = challenge_responses[0]

        rep_body = await self.get_response_body(challenge_response)
        rep_d = json.loads(rep_body.decode('utf-8'))

        if 'challengeInfo' not in rep_d:
            raise ApiFailedException("Failed to get challengeInfo from response")

        self.as_dict = rep_d['challengeInfo']
        return self.as_dict

    async def videos(self, count=30, offset=0, **kwargs) -> Iterator[Video]:
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
        await self.info()

        try:
            async for video in self._get_videos_api(count, offset, **kwargs):
                yield video
        except ApiFailedException:
            async for video in self._get_videos_scraping(count, offset, **kwargs):
                yield video


    async def _get_videos_scraping(self, count=30, offset=0, **kwargs):
        processed_urls = []
        amount_yielded = 0
        pull_method = 'browser'
        tries = 0
        MAX_TRIES = 5
        data_request_path = "api/challenge/item_list"

        while amount_yielded < count:
            await self.parent.request_delay()

            search_requests = self.get_requests(data_request_path)
            search_requests = [response for response in search_requests if f"challengeID={self.as_dict['challenge']['id']}" in response.url]
            search_requests = [request for request in search_requests if request.url not in processed_urls]
            for request in search_requests:
                processed_urls.append(request.url)
                response = await request.response()
                try:
                    body = await self.get_response_body(response)
                    res = json.loads(body)
                except:
                    continue
                if res.get('type') == 'verify':
                    # this is the captcha denied response
                    continue

                videos = res.get("itemList", [])
                amount_yielded += len(videos)
                for video in videos:
                    yield self.parent.video(data=video)

                if not res.get("hasMore", False):
                    self.parent.logger.info(
                        "TikTok isn't sending more TikToks beyond this point."
                    )
                    return

            for _ in range(tries):
                await self.slight_scroll_up()
                await self.scroll_to_bottom()
                await self.parent.request_delay()
            
                search_requests = self.get_requests(data_request_path)
                search_requests = [request for request in search_requests if request.url not in processed_urls]

            if len(search_requests) == 0:
                tries += 1
                if tries > MAX_TRIES:
                    raise
                continue
                

    async def _get_videos_api(self, count=30, offset=0, **kwargs):
        responses = self.get_responses("api/challenge/item_list")
        responses = [response for response in responses if f"challengeID={self.as_dict['challenge']['id']}" in response.url]

        amount_yielded = 0
        cursor = 0
        while amount_yielded < count:
            for response in responses:
                next_url = edit_url(response.url, {"cursor": cursor})
                cookies = await self.parent._context.cookies()
                cookies = {cookie['name']: cookie['value'] for cookie in cookies}
                r = requests.get(next_url, headers=response.headers, cookies=cookies)
                try:
                    res = r.json()
                except json.decoder.JSONDecodeError:
                    raise ApiFailedException("Failed to decode JSON from TikTok API response")

                cursor = res["cursor"]
                videos = res.get("itemList", [])

                amount_yielded += len(videos)
                for video in videos:
                    yield self.parent.video(data=video)

                # if not res.get("hasMore", False):
                #     self.parent.logger.info(
                #         "TikTok isn't sending more TikToks beyond this point."
                #     )
                #     return

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
        return f"PyTok.hashtag(id='{self.id}', name='{self.name}')"

    def __getattr__(self, name):
        # TODO: Maybe switch to using @property instead
        if name in ["id", "name", "as_dict"]:
            self.as_dict = self.info()
            self.__extract_from_data()
            return self.__getattribute__(name)

        raise AttributeError(f"{name} doesn't exist on PyTok.api.Hashtag")
