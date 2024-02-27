import asyncio
import json

from pytok.tiktok import PyTok

username = 'therock'
id = '7296444945991224622'

async def main():
    async with PyTok() as api:
        video = api.video(username=username, id=id)

        # Bytes of the TikTok video
        video_data = await video.info()
        network_data = await video.network_info()
        video_bytes = await video.bytes()
        bytes_network_data = await video.bytes_network_info()

        all_data = {
            "video_data": video_data,
            "network_data": network_data,
            "bytes_network_data": bytes_network_data
        }

        with open("out.json", "w") as out_file:
            json.dump(all_data, out_file)

        with open("out.mp4", "wb") as out_file:
            out_file.write(video_bytes)

if __name__ == "__main__":
    asyncio.run(main())

