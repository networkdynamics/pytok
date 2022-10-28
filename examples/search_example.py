from pytok import PyTok

with PyTok() as api:
    for user in api.search("therock").users():
        print(user.username)

    for sound in api.search('funny').videos():
        print(sound.title)
