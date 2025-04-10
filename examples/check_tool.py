import asyncio
import json

from pytok.tiktok import PyTok

async def main():
    async with PyTok(browser="chromium") as api:
        await api._page.goto("https://www.browserscan.net/")
        pass

if __name__ == "__main__":
    asyncio.run(main())
