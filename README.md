
# pytok

This is a Selenium based version of David Teacher's unofficial api wrapper for TikTok.com in python. It re-implements a currently limited set of the features of the original library, with a shifted focus on using browser automation to allow manual captcha solves with a hopefully minor trade-off in performance.


## Quick Start Guide

Here's a quick bit of code to get the videos from a particular hashtag on TikTok. There's more examples in the [examples](https://github.com/networkdynamics/pytok/tree/master/examples) directory.

```py
from pytok import PyTok

with PyTok() as api:
    for video in api.hashtag(name=hashtag).videos(count=100):
        # print the info of the top 100 videos for this hashtag
        print(video.info())
```
