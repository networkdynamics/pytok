from pytok.tiktok import PyTok

with PyTok() as api:
    user = api.user(username="therock")

    for video in user.videos():
        print(video.id)
