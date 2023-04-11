from __future__ import annotations

from urllib.parse import urlencode
from ..helpers import extract_video_id_from_url, extract_user_id_from_url
from typing import TYPE_CHECKING, ClassVar, Optional
from datetime import datetime
import re
import json

import requests

if TYPE_CHECKING:
    from ..tiktok import PyTok
    from .user import User
    from .sound import Sound
    from .hashtag import Hashtag

from .base import Base
from ..helpers import extract_tag_contents, add_if_not_replace


class Video(Base):
    """
    A TikTok Video class

    Example Usage
    ```py
    video = api.video(id='7041997751718137094')
    ```
    """

    parent: ClassVar[PyTok]

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
            self.username = extract_user_id_from_url(url)

        if self.id is None or self.username is None:
            raise TypeError("You must provide id and username or url parameter.")

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
        self.view()
        url = self._get_url()

        # get initial html data
        initial_html_request = self.get_requests(url)[0]
        html_body = self.get_response_body(initial_html_request)
        contents = extract_tag_contents(html_body)
        res = json.loads(contents)

        video = list(res['ItemModule'].values())[0]

        video_users = res['UserModule']['users']
        video['author'] = video_users[video['author']]

        return video

    def _get_url(self) -> str:
        return f"https://www.tiktok.com/@{self.username}/video/{self.id}"

    def view(self, **kwargs) -> None:
        """
        Opens the TikTok Video in your default browser.

        Example Usage
        ```py
        api.video(id='7041997751718137094').view()
        ```
        """
        driver = self.parent._browser
        url = self._get_url()
        driver.get(url)
        self.check_initial_call(url)
        # TODO check with something else, sometimes no comments so this breaks
        self.wait_for_content_or_unavailable_or_captcha('comment-level-1', 'Video currently unavailable')

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
        raise NotImplementedError()

    def _get_comments_and_req(self, count):
        self.view()

        # get initial html data
        html_request_path = f"@{self.username}/video/{self.id}"
        initial_html_request = self.get_requests(html_request_path)[0]
        html_body = self.get_response_body(initial_html_request)
        contents = extract_tag_contents(html_body)
        res = json.loads(contents)

        amount_yielded = 0
        all_comments = []

        if 'CommentItem' in res:
            comments = list(res['CommentItem'].values())

            comment_users = res['UserModule']['users']
            for comment in comments:
                comment['user'] = comment_users[comment['user']]

            amount_yielded += len(comments)
            all_comments += comments

            if amount_yielded >= count:
                return all_comments, True

            has_more = res['Comment']['hasMore']
            if not has_more:
                self.parent.logger.info(
                    "TikTok isn't sending more TikToks beyond this point."
                )
                return all_comments, True
            

        data_request_path = "api/comment/list"
        # scroll down to induce request
        self.scroll_to_bottom()
        self.wait_for_requests(data_request_path)

        # get request
        data_requests = self.get_requests(data_request_path)

        for data_request in data_requests:
            res_body = self.get_response_body(data_request)

            res = json.loads(res_body)
            comments = res.get("comments", [])

            amount_yielded += len(comments)
            all_comments += comments

            if amount_yielded > count:
                return all_comments, True

            has_more = res.get("has_more")
            if has_more != 1:
                self.parent.logger.info(
                    "TikTok isn't sending more TikToks beyond this point."
                )
                return all_comments, True

        self.parent.request_cache['comments'] = data_request

        return all_comments, False

    def _get_comment_replies(self, comment, batch_size):
        data_request = self.parent.request_cache['comments']
        num_already_fetched = len(comment.get('reply_comment', []) if comment.get('reply_comment', []) is not None else [])
        num_comments_to_fetch = comment['reply_comment_total'] - num_already_fetched
        while num_comments_to_fetch > 0:
            next_url = re.sub("cursor=([0-9]+)", f"cursor={num_already_fetched}", data_request.url)
            next_url = re.sub("&aweme_id=([0-9]+)", '', next_url)
            next_url = re.sub("count=([0-9]+)", f"count={min(num_comments_to_fetch, batch_size)}", next_url)
            next_url = re.sub("api/comment/list/", "api/comment/list/reply/", next_url)
            next_url = re.sub("focus_state=false", "focus_state=true", next_url)
            next_url += f"&item_id={comment['aweme_id']}"
            next_url += f"&comment_id={comment['cid']}"

            r = requests.get(next_url, headers=data_request.headers)
            res = r.json()

            if res.get('type') == 'verify':
                # force new request for cache
                self._get_comments_and_req()

            reply_comments = res.get("comments", [])

            if reply_comments:
                comment['reply_comment'] = comment['reply_comment'] + reply_comments if comment['reply_comment'] else reply_comments

            has_more = res.get("has_more")
            if has_more != 1:
                self.parent.logger.info(
                    "TikTok isn't sending more TikToks beyond this point."
                )
                break

            self.parent.request_delay()

            num_already_fetched = len(comment['reply_comment'])
            num_comments_to_fetch = comment['reply_comment_total'] - num_already_fetched

    def comments(self, count=200, batch_size=100):

        # TODO allow multi layer comment fetch

        amount_yielded = 0
        if 'comments' not in self.parent.request_cache:
            all_comments, finished = self._get_comments_and_req(count)

            for comment in all_comments:
                self._get_comment_replies(comment, batch_size)

            amount_yielded += len(all_comments)
            yield from all_comments

            if finished:
                return

        data_request = self.parent.request_cache['comments']

        while amount_yielded < count:
            
            next_url = add_if_not_replace(data_request.url, "cursor=([0-9]+)", f"cursor={amount_yielded}", f"&cursor={amount_yielded}")
            next_url = add_if_not_replace(next_url, "aweme_id=([0-9]+)", f"aweme_id={self.id}", f"&aweme_id={self.id}")
            next_url = add_if_not_replace(next_url, "count=([0-9]+)", f"count={batch_size}", f"&count={batch_size}")

            r = requests.get(next_url, headers=data_request.headers)
            res = r.json()

            if res.get('type') == 'verify':
                # force new request for cache
                self._get_comments_and_req()

            comments = res.get("comments", [])

            if comments:
                for comment in comments:
                    self._get_comment_replies(comment, batch_size)

                amount_yielded += len(comments)
                yield from comments

            has_more = res.get("has_more")
            if has_more != 1:
                self.parent.logger.info(
                    "TikTok isn't sending more TikToks beyond this point."
                )
                return

            self.parent.request_delay()

    def __extract_from_data(self) -> None:
        data = self.as_dict
        keys = data.keys()

        if "author" in keys:
            self.id = data["id"]
            self.username = data["author"]["uniqueId"]
            self.create_time = datetime.fromtimestamp(int(data["createTime"]))
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
        return f"PyTok.video(id='{self.id}')"

    def __getattr__(self, name):
        # Handle author, sound, hashtags, as_dict
        if name in ["author", "sound", "hashtags", "stats", "create_time", "as_dict"]:
            self.as_dict = self.info()
            self.__extract_from_data()
            return self.__getattribute__(name)

        raise AttributeError(f"{name} doesn't exist on PyTok.api.Video")
