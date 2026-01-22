import asyncio
import json
import logging

from pytok.tiktok import PyTok

# Enable debug logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    users = ['therock']
    async with PyTok(logging_level=logging.INFO, manual_captcha_solves=True, log_captcha_solves=True) as api:
        for username in users:
            user = api.user(username=username)
            user_data = await user.info()

            videos = []
            videos_bytes = []
            async for video in user.videos(count=30):
                video_data = await video.info()
                videos.append(video_data)

            assert len(videos) > 0, "No videos found"
            print(f"Fetched {len(videos)} videos for user {username}")
            with open("out.json", "w") as f:
                json.dump(videos, f)

if __name__ == "__main__":
    asyncio.run(main())
