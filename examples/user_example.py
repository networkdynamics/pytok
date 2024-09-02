import asyncio
import json

from pytok.tiktok import PyTok

async def main():
    users = ['therock']
    async with PyTok(manual_captcha_solves=True, log_captcha_solves=True) as api:
        for username in users:
            user = api.user(username=username)
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
