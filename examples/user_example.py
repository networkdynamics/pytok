import asyncio
import json

from pytok.tiktok import PyTok

async def main():
    async with PyTok() as api:
        user = api.user(username="therock")
        user_data = await user.info()

        videos = []
        async for video in user.videos():
            video_data = video.info()
            videos.append(video_data)

        with open("out.json", "w") as f:
            json.dump(videos, f)

if __name__ == "__main__":
    asyncio.run(main())
