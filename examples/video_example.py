import asyncio

from pytok.tiktok import PyTok

async def main():
    async with PyTok() as api:
        video = api.video(id="7041997751718137094")

        # Bytes of the TikTok video
        video_data = video.info_full()

        with open("out.json", "w") as out_file:
            out_file.write(video_data)

if __name__ == "__main__":
    asyncio.run(main())
