import asyncio
import json

from pytok.tiktok import PyTok

videos = [
    {
        'id': '7058106162235100462',
        'author': {
            'uniqueId': 'charlesmcbryde'
        }
    }
]

async def main():
    async with PyTok(headless=True) as api:
        for video in videos:
            comments = []
            async for comment in api.video(id=video['id'], username=video['author']['uniqueId']).comments(count=1000):
                comments.append(comment)

            with open("out.json", "w") as f:
                json.dump(comments, f)

if __name__ == "__main__":
    asyncio.run(main())
