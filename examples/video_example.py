import asyncio
import json
import logging

from pytok.tiktok import PyTok

username = 'therock'
id = '7296444945991224622'

async def main():
    async with PyTok() as api:
        video = api.video(username=username, id=id)

        # Bytes of the TikTok video
        video_data = await video.info()
        related_videos = []
        async for related_video in video.related_videos():
            related_videos.append(related_video)

        with open("out.json", "w") as out_file:
            json.dump(video_data, out_file)

        with open("related.json", "w") as out_file:
            json.dump(list(related_videos), out_file)

if __name__ == "__main__":
    asyncio.run(main())

