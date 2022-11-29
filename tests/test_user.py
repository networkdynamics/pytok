from pytok.tiktok import PyTok
import os

username = "brianjordanalvarez"


def test_user_videos():
    with PyTok() as api:
        count = 0
        for video in api.user(username=username).videos(count=100):
            count += 1

        assert count >= 120


if __name__ == '__main__':
    test_user_videos()