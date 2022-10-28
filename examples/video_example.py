from pytok import PyTok

with PyTok() as api:
    video = api.video(id="7041997751718137094")

    # Bytes of the TikTok video
    video_data = video.info_full()

    with open("out.json", "w") as out_file:
        out_file.write(video_data)
