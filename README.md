
# Unofficial TikTok API in Python

This is a Selenium based version of David Teacher's unofficial api wrapper for TikTok.com in python. It re-implements a currently limited set of the features of the original library, with a shifted focus on using browser automation to allow manual captcha solves with a hopefully minor trade-off in performance.

It's currently in a messy half way point up being gutted and having its innards replaced so use with caution!


## Quick Start Guide

Here's a quick bit of code to get the most recent trending videos on TikTok. There's more examples in the [examples](https://github.com/davidteather/TikTok-Api/tree/master/examples) directory.

```py
from TikTokApi import TikTokApi

# Watch https://www.youtube.com/watch?v=-uCt1x8kINQ for a brief setup tutorial
with TikTokApi() as api:
    for trending_video in api.trending.videos(count=50):
        # Prints the author's username of the trending video.
        print(trending_video.author.username)
```
