import asyncio
import json

from pytok.tiktok import PyTok

async def main():
    async with PyTok() as api:
        user = api.user(username="therock")
        user_data = await user.info()

        videos = []
        videos_bytes = []
        async for video in user.videos():
            video_data = video.info()
            videos.append(video_data)
            video_bytes = await video.bytes()
            videos_bytes.append(video_bytes)

        assert len(videos) > 0
        assert len(videos_bytes) > 0
        with open("out.json", "w") as f:
            json.dump(videos, f)

if __name__ == "__main__":
    asyncio.run(main())
