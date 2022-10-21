from pytok import PyTok

with PyTok() as api:
    tag = api.hashtag(name="funny")

    print(tag.info())

    for video in tag.videos():
        print(video.id)
