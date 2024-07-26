from __future__ import annotations

import asyncio
from datetime import datetime
import json
from urllib import parse as url_parsers
from typing import TYPE_CHECKING, ClassVar, Optional

import brotli
import requests
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

if TYPE_CHECKING:
    from ..tiktok import PyTok
    from .user import User
    from .sound import Sound
    from .hashtag import Hashtag

from .base import Base
from ..helpers import extract_tag_contents, edit_url, extract_video_id_from_url, extract_user_id_from_url
from .. import exceptions


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

        if self.id is None and url is None:
            raise TypeError("You must provide id or url parameter.")

    async def info(self, **kwargs) -> dict:
        """
        Returns a dictionary of all data associated with a TikTok Video.

        Example Usage
        ```py
        video_data = api.video(id='7041997751718137094').info()
        ```
        """
        if not hasattr(self, 'as_dict'):
            url = self._get_url()
            page = self.parent._page
            if page.url != url:
                await self.view()

            # get initial html data
            initial_html_response = self.get_responses(url)[-1]
            html_body = await self.get_response_body(initial_html_response)
            contents = extract_tag_contents(html_body)
            res = json.loads(contents)

            video_detail = res['__DEFAULT_SCOPE__']['webapp.video-detail']
            if video_detail['statusCode'] != 0:
                raise exceptions.NotAvailableException(
                    f"Content is not available with status message: {video_detail['statusMsg']}")
            video_data = video_detail['itemInfo']['itemStruct']
            self.as_dict = video_data
        else:
            video_data = self.as_dict

        return video_data

    async def network_info(self, **kwargs) -> dict:
        """
        Returns a dictionary of all network data associated with a TikTok Video.

        Example Usage
        ```py
        video_data = api.video(id='7041997751718137094').network_data()
        ```
        """
        url = self._get_url()
        page = self.parent._page
        if page.url != url:
            await self.view()
        initial_html_response = self.get_responses(url)[-1]
        network_info = {}
        network_info['server_addr'] = await initial_html_response.server_addr()
        network_info['headers'] = await initial_html_response.all_headers()
        return network_info

    async def bytes_network_info(self, **kwargs) -> dict:
        """
        Returns a dictionary of all network data associated with a TikTok Video.

        Example Usage
        ```py
        video_data = api.video(id='7041997751718137094').bytes_network_data()
        ```
        """
        play_path = url_parsers.urlparse(self.as_dict['video']['playAddr']).path
        reqs = self.get_requests(play_path)
        if len(reqs) == 0:
            # TODO load page and pull
            raise Exception("No requests found for video")
        for req in reqs:
            try:
                res = await req.response()
                network_info = {}
                network_info['server_addr'] = await res.server_addr()
                network_info['headers'] = await res.all_headers()
                return network_info
            except Exception:
                continue
        else:
            raise Exception("Failed to get video bytes")

    def _get_url(self) -> str:
        if not self.username or not self.id:
            raise ValueError("You must provide the username and id to get the url.")
        return f"https://www.tiktok.com/@{self.username}/video/{self.id}"

    async def view(self, **kwargs) -> None:
        """
        Opens the TikTok Video in your default browser.

        Example Usage
        ```py
        api.video(id='7041997751718137094').view()
        ```
        """
        page = self.parent._page
        url = self._get_url()
        try:
            async with page.expect_request(url) as event:
                await page.goto(url)
                request = await event.value
                response = await request.response()
                if response.status >= 300:
                    raise exceptions.NotAvailableException("Content is not available")
            # TODO check with something else, sometimes no comments so this breaks
            await page.wait_for_load_state('networkidle', timeout=60 * 1000)
            await self.check_for_unavailable_or_captcha('Video currently unavailable')
        except PlaywrightTimeoutError as e:
            raise exceptions.TimeoutException(str(e))

    async def bytes(self, **kwargs) -> bytes:
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
        bytes_url = self.as_dict['video']['playAddr']
        bytes_headers = {}
        play_path = url_parsers.urlparse(bytes_url).path
        reqs = self.get_requests(play_path)
        if len(reqs) > 0:
            for req in reqs:
                try:
                    res = await req.response()
                    body = await res.body()
                except Exception:
                    bytes_url = req.url
                    bytes_headers = req.headers
                    continue
                return body

        # send the request ourselves
        bytes_headers = {
            'sec-ch-ua': '"HeadlessChrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"', 
            'referer': 'https://www.tiktok.com/', 
            'accept-encoding': 'identity;q=1, *;q=0', 
            'sec-ch-ua-mobile': '?0', 
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.4 Safari/537.36', 
            'range': 'bytes=0-', 
            'sec-ch-ua-platform': '"Windows"'
        }
        cookies = await self.parent._context.cookies()
        cookies = {cookie['name']: cookie['value'] for cookie in cookies}
        r = requests.get(bytes_url, headers=bytes_headers, cookies=cookies)
        if r.content is not None or len(r.content) > 0:
            return r.content
        raise Exception("Failed to get video bytes")

    async def _get_comments_and_req(self, count):
        # get request
        data_request_path = "api/comment/list"
        data_responses = self.get_responses(data_request_path)

        amount_yielded = 0
        all_comments = []
        processed_urls = []

        valid_data_request = None
        for data_response in data_responses:
            try:
                res = await data_response.json()

                self.parent.request_cache['comments'] = data_response.request

                processed_urls.append(data_response.url)

                comments = res.get("comments", [])

                amount_yielded += len(comments)
                all_comments += comments

                if amount_yielded > count:
                    return all_comments, processed_urls, True

                has_more = res.get("has_more")
                if has_more != 1:
                    self.parent.logger.info(
                        "TikTok isn't sending more TikToks beyond this point."
                    )
                    return all_comments, processed_urls, True
            except Exception:
                pass

        return all_comments, processed_urls, False

    async def _get_comment_replies(self, comment, batch_size):
        if 'comments' not in self.parent.request_cache:
            return
        data_request = self.parent.request_cache['comments']
        num_already_fetched = len(
            comment.get('reply_comment', []) if comment.get('reply_comment', []) is not None else [])
        num_comments_to_fetch = comment['reply_comment_total'] - num_already_fetched
        while num_comments_to_fetch > 0:

            url_parsed = url_parsers.urlparse(data_request.url)
            params = url_parsers.parse_qs(url_parsed.query)
            params['cursor'] = num_already_fetched
            del params['aweme_id']
            params['count'] = min(num_comments_to_fetch, batch_size)
            params['item_id'] = comment['aweme_id']
            params['comment_id'] = comment['cid']
            params['focus_state'] = 'true'
            url_path = url_parsed.path.replace("api/comment/list", "api/comment/list/reply")
            next_url = f"{url_parsed.scheme}://{url_parsed.netloc}{url_path}?{url_parsers.urlencode(params, doseq=True)}"
            cookies = await self.parent._context.cookies()
            cookies = {cookie['name']: cookie['value'] for cookie in cookies}
            r = requests.get(next_url, headers=data_request.headers, cookies=cookies)
            res = r.json()

            reply_comments = res.get("comments", [])

            if reply_comments:
                comment['reply_comment'] = comment['reply_comment'] + reply_comments if comment[
                    'reply_comment'] else reply_comments

            has_more = res.get("has_more")
            if has_more != 1:
                self.parent.logger.info(
                    "TikTok isn't sending more TikToks beyond this point."
                )
                break

            await self.parent.request_delay()

            num_already_fetched = len(comment['reply_comment'])
            num_comments_to_fetch = comment['reply_comment_total'] - num_already_fetched

    async def comments(self, count=200, batch_size=100):
        if self.id and self.username:
            await self.view()
            await self.wait_for_content_or_unavailable_or_captcha('css=[data-e2e=comment-level-1]',
                                                                  'Be the first to comment!')
            # TODO allow multi layer comment fetch

            amount_yielded = 0
            all_comments, processed_urls, finished = await self._get_comments_and_req(count)

            for comment in all_comments:
                await self._get_comment_replies(comment, batch_size)

            amount_yielded += len(all_comments)
            for comment in all_comments:
                yield comment

            if finished:
                return

            # so that we don't re-yield any comments previously yielded
            comment_ids = set(comment['cid'] for comment in all_comments)
            try:
                async for comment in self._get_api_comments(count, batch_size, comment_ids):
                    yield comment
            except exceptions.ApiFailedException as e:
                async for comment in self._get_scroll_comments(count, amount_yielded, processed_urls):
                    yield comment
        else:
            # if we only have the video id, we need to entirely rely on the api
            async for comment in self._get_api_comments(count, batch_size, set()):
                yield comment

    async def _get_scroll_comments(self, count, amount_yielded, processed_urls):
        page = self.parent._page
        if page.url != self._get_url():
            await self.view()
        tries = 0

        data_request_path = "api/comment/list"
        while amount_yielded < count:
            # scroll down to induce request
            await self.scroll_to(10000)
            await self.slight_scroll_up()
            await self.check_and_wait_for_captcha()
            await self.check_and_close_signin()

            data_responses = self.get_responses(data_request_path)
            data_responses = [data_response for data_response in data_responses if
                              data_response.url not in processed_urls]

            if len(data_responses) == 0:
                if tries > 5:
                    print(f"Not sending anymore!")
                    break
                tries += 1

            for data_response in data_responses:
                try:
                    res = await data_response.json()

                    processed_urls.append(data_response.url)

                    comments = res.get("comments", [])

                    for comment in comments:
                        await self._get_comment_replies(comment, 100)

                    amount_yielded += len(comments)
                    for comment in comments:
                        yield comment

                    if amount_yielded > count:
                        return

                    has_more = res.get("has_more")
                    if has_more != 1:
                        self.parent.logger.info(
                            "TikTok isn't sending more TikToks beyond this point."
                        )
                        return
                except Exception as e:
                    processed_urls.append(data_response.url)

    async def _get_comments_via_requests(self, count, cursor, data_request):
        ms_tokens = await self.parent.get_ms_tokens()
        next_url = edit_url(data_request.url, {'count': count, 'cursor': cursor, 'aweme_id': self.id})
        cookies = await self.parent._context.cookies()
        cookies = {cookie['name']: cookie['value'] for cookie in cookies}
        headers = await data_request.all_headers()
        headers = {k: v for k, v in headers.items() if not k.startswith(':')}
        headers['referer'] = None
        r = requests.get(next_url, headers=headers, cookies=cookies)

        if r.status_code != 200:
            raise Exception(f"Failed to get comments with status code {r.status_code}")

        if len(r.content) == 0:
            print("Failed to comments from API, switching to scroll")
            raise exceptions.ApiFailedException("No content in response")

        try:
            res = r.json()
        except Exception:
            res = json.loads(brotli.decompress(r.content).decode())

        return res

    async def _get_api_comments(self, count, batch_size, comment_ids):

        data_request = self.parent.request_cache['comments']

        try:
            amount_yielded = 0
            cursor = 0
            while amount_yielded < count:
                # try directly requesting through browser
                url = edit_url(data_request.url,
                               {'count': 20, 'cursor': cursor, 'aweme_id': self.id})  # , 'msToken': ms_tokens[-1]})
                page = self.parent._page
                async with page.expect_request(url) as event:
                    await page.goto(url)
                    request = await event.value
                    response = await request.response()
                    if response.status >= 300:
                        raise exceptions.NotAvailableException("Content is not available")

                if response.status != 200:
                    raise Exception(f"Failed to get comments with status code {response.status}")

                content = await response.body()
                if len(content) == 0:
                    raise Exception("No content in response")

                res = await response.json()
                cursor = res.get("cursor", 0)

                comments = res.get("comments", [])
                amount_yielded += len(comments)
                for comment in comments:
                    if comment['cid'] not in comment_ids:
                        try:
                            await self._get_comment_replies(comment, batch_size)
                        except Exception:
                            pass
                        yield comment
        except Exception as e:
            try:
                # try getting all at once
                retries = 5
                for _ in range(retries):
                    try:
                        cursor = '0'
                        res = await self._get_comments_via_requests(count, cursor, data_request)

                        comments = res.get("comments", [])
                        for comment in comments:
                            if comment['cid'] not in comment_ids:
                                try:
                                    await self._get_comment_replies(comment, batch_size)
                                except Exception:
                                    pass
                                yield comment

                        return
                    except Exception as e:
                        pass
                else:
                    print("Failed to get all comments at once")
                    print("Trying batched...")
                    raise Exception("Failed to get comments")
            except Exception as e:

                amount_yielded = len(comment_ids)
                cursor = 0
                while amount_yielded < count:
                    res = await self._get_comments_via_requests(20, cursor, data_request)

                    if res.get('type') == 'verify':
                        # force new request for cache
                        self._get_comments_and_req()

                    cursor = res.get("cursor", 0)
                    comments = res.get("comments", [])

                    if comments:
                        for comment in comments:
                            await self._get_comment_replies(comment, batch_size)

                        amount_yielded += len(comments)
                        for comment in comments:
                            yield comment

                    has_more = res.get("has_more")
                    if has_more != 1:
                        self.parent.logger.info(
                            "TikTok isn't sending more TikToks beyond this point."
                        )
                        return

                    await self.parent.request_delay()

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

    # def __getattr__(self, name):
    #     # Handle author, sound, hashtags, as_dict
    #     if name in ["author", "sound", "hashtags", "stats", "create_time", "as_dict"]:
    #         self.as_dict = self.info()
    #         self.__extract_from_data()
    #         return self.__getattribute__(name)

    #     raise AttributeError(f"{name} doesn't exist on PyTok.api.Video")
