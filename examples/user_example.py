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
            video_data = await video.info()
            videos.append(video_data)

        assert len(videos) > 0, "No videos found"
        with open("out.json", "w") as f:
            json.dump(videos, f)

if __name__ == "__main__":
    asyncio.run(main())
