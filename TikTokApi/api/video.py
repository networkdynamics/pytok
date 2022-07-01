from __future__ import annotations

from urllib.parse import urlencode
from ..helpers import extract_video_id_from_url
from typing import TYPE_CHECKING, ClassVar, Optional
from datetime import datetime
import re
import json

import requests

if TYPE_CHECKING:
    from ..tiktok import TikTokApi
    from .user import User
    from .sound import Sound
    from .hashtag import Hashtag

from .base import Base
from ..helpers import extract_tag_contents


class Video(Base):
    """
    A TikTok Video class

    Example Usage
    ```py
    video = api.video(id='7041997751718137094')
    ```
    """

    parent: ClassVar[TikTokApi]

    id: Optional[str]
    """TikTok's ID of the Video"""
    create_time: Optional[datetime]
    """The creation time of the Video"""
    stats: Optional[dict]
    """TikTok's stats of the Video"""
    author: Optional[User]
    """The User who created the Video"""
    sound: Optional[Sound]
    """The Sound that is associated with the Video"""
    hashtags: Optional[list[Hashtag]]
    """A List of Hashtags on the Video"""
    as_dict: dict
    """The raw data associated with this Video."""

    def __init__(
        self,
        id: Optional[str] = None,
        username: Optional[str] = None,
        url: Optional[str] = None,
        data: Optional[dict] = None,
    ):
        """
        You must provide the id or a valid url, else this will fail.
        """
        self.id = id
        self.username = username
        if data is not None:
            self.as_dict = data
            self.__extract_from_data()
        elif url is not None:
            self.id = extract_video_id_from_url(url)

        if self.id is None:
            raise TypeError("You must provide id or url parameter.")

    def info(self, **kwargs) -> dict:
        """
        Returns a dictionary of TikTok's Video object.

        Example Usage
        ```py
        video_data = api.video(id='7041997751718137094').info()
        ```
        """
        return self.as_dict

    def info_full(self, **kwargs) -> dict:
        """
        Returns a dictionary of all data associated with a TikTok Video.

        Example Usage
        ```py
        video_data = api.video(id='7041997751718137094').info_full()
        ```
        """
        processed = self.parent._process_kwargs(kwargs)
        kwargs["custom_device_id"] = processed.device_id

        device_id = kwargs.get("custom_device_id", None)
        query = {
            "itemId": self.id,
        }
        path = "api/item/detail/?{}&{}".format(
            self.parent._add_url_params(), urlencode(query)
        )

        return self.parent.get_data(path, **kwargs)

    def bytes(self, **kwargs) -> bytes:
        """
        Returns the bytes of a TikTok Video.

        Example Usage
        ```py
        video_bytes = api.video(id='7041997751718137094').bytes()

        # Saving The Video
        with open('saved_video.mp4', 'wb') as output:
            output.write(video_bytes)
        ```
        """
        processed = self.parent._process_kwargs(kwargs)
        kwargs["custom_device_id"] = processed.device_id

        video_data = self.info(**kwargs)
        download_url = video_data["video"]["playAddr"]

        return self.parent.get_bytes(url=download_url, **kwargs)

    def comments(self, count=20):
        driver = self.parent._browser

        driver.get(f"https://www.tiktok.com/@{self.username}/video/{self.id}")

        toks_delay = 20
        CAPTCHA_WAIT = 999999

        self.wait_for_content_or_captcha('comment-level-1')

        # get initial html data
        html_request_path = f"@{self.username}/video/{self.id}"
        initial_html_request = self.get_requests(html_request_path)[0]
        html_body = self.get_response_body(initial_html_request)
        contents = extract_tag_contents(html_body)
        res = json.loads(contents)

        comments = [val for key, val in res['CommentItem'].items()]

        amount_yielded = len(comments)
        yield from comments

        if amount_yielded >= count:
            return

        has_more = res['Comment']['hasMore']
        if not has_more:
            self.parent.logger.info(
                "TikTok isn't sending more TikToks beyond this point."
            )
            return

        data_request_path = "api/comment/list"
        while len(self.get_requests(data_request_path)) == 0:
            # scroll down to induce request
            self.scroll_to_bottom()

        # get request
        data_requests = self.get_requests(data_request_path)

        for data_request in data_requests:
            res_body = self.get_response_body(data_request)

            res = json.loads(res_body)
            comments = res.get("comments", [])

            amount_yielded += len(comments)
            yield from comments

            if amount_yielded > count:
                return

            has_more = res.get("has_more")
            if has_more == 0:
                self.parent.logger.info(
                    "TikTok isn't sending more TikToks beyond this point."
                )
                return

        while amount_yielded < count:
            
            cursor = res["cursor"]
            next_url = re.sub("cursor=([0-9]+)", f"cursor={cursor}", data_request.url)

            r = requests.get(next_url, headers=data_request.headers)
            res = r.json()

            if res.get('type') == 'verify':
                self.check_and_wait_for_captcha()

            comments = res.get("comments", [])

            amount_yielded += len(comments)
            yield from comments

            has_more = res.get("has_more")
            if has_more == 0:
                self.parent.logger.info(
                    "TikTok isn't sending more TikToks beyond this point."
                )
                return

            

    def __extract_from_data(self) -> None:
        data = self.as_dict
        keys = data.keys()

        if "author" in keys:
            self.id = data["id"]
            self.create_time = datetime.fromtimestamp(data["createTime"])
            self.stats = data["stats"]
            self.author = self.parent.user(data=data["author"])
            self.sound = self.parent.sound(data=data["music"])

            self.hashtags = [
                self.parent.hashtag(data=hashtag)
                for hashtag in data.get("challenges", [])
            ]

        if self.id is None:
            Video.parent.logger.error(
                f"Failed to create Video with data: {data}\nwhich has keys {data.keys()}"
            )

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"TikTokApi.video(id='{self.id}')"

    def __getattr__(self, name):
        # Handle author, sound, hashtags, as_dict
        if name in ["author", "sound", "hashtags", "stats", "create_time", "as_dict"]:
            self.as_dict = self.info()
            self.__extract_from_data()
            return self.__getattribute__(name)

        raise AttributeError(f"{name} doesn't exist on TikTokApi.api.Video")
