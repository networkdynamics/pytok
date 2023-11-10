import asyncio
import os

from pytok.tiktok import PyTok

# username = "brianjordanalvarez"
username = 'marierenaudstab'


async def test_user_videos():
    async with PyTok(headless=True) as api:
        user = api.user(username=username)
        user_data = await user.info()
        count = 0
        async for video in api.user(username=username).videos(count=100):
            count += 1

        assert count >= 120


if __name__ == '__main__':
    asyncio.run(test_user_videos())