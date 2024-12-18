import asyncio
import json

from pytok.tiktok import PyTok

hashtag_name = 'fyp'

async def main():
    async with PyTok(manual_captcha_solves=True) as api:
        hashtag = api.hashtag(name=hashtag_name)

        videos = []
        async for video in hashtag.videos(count=1000):
            video_info = await video.info()
            videos.append(video_info)

        with open("out.json", "w") as out_file:
            json.dump(videos, out_file)

if __name__ == "__main__":
    asyncio.run(main())