
[![DOI](https://zenodo.org/badge/555492190.svg)](https://zenodo.org/doi/10.5281/zenodo.12802713)

# pytok

This is a zendriver based version of David Teacher's unofficial api wrapper for TikTok.com in python. It re-implements a currently limited set of the features of the original library, with a shifted focus on using browser automation to allow automatic captcha solves with a hopefully minor trade-off in performance.

## Installation

```bash
pip install git+https://github.com/networkdynamics/pytok.git@master
```

## Quick Start Guide

Here's a quick bit of code to get the videos from a particular hashtag on TikTok. There's more examples in the [examples](https://github.com/networkdynamics/pytok/tree/master/examples) directory.

```py
import asyncio

from pytok.tiktok import PyTok

async def main():
    async with PyTok() as api:
        user = api.user(username="therock")
        user_data = await user.info()
        print(user_data)

        videos = []
        async for video in user.videos():
            video_data = video.info()
            print(video_data)

if __name__ == "__main__":
    asyncio.run(main())
```


Please note pulling data from TikTok takes a while! We recommend leaving the scripts running on a server for a while for them to finish downloading everything. Feel free to play around with the delay constants to either speed up the process or avoid TikTok rate limiting, like so: `PyTok(request_delay=10)`

Please do not hesitate to make an issue in this repo to get our help with this!

## Citation

If you use this library in your research, please cite it using the following BibTeX entry:

```bibtex
@article{steel2023invasion,
  title={The invasion of ukraine viewed through tiktok: A dataset},
  author={Steel, Benjamin and Parker, Sara and Ruths, Derek},
  journal={arXiv preprint arXiv:2301.08305},
  year={2023}
}

```

## Format and Schema

The JSONable dictionary returned by the `info()` methods contains all of the data that the TikTok API returns. We have provided helper functions to parse that data into Pandas DataFrames, `utils.get_comment_df()`, `utils.get_video_df()` and `utils.get_user_df()` for the data from comments, videos, and users respectively.

The video dataframe will contain the following columns:
|Field name | Description |
|----------|----------|
|`video_id`| Unique video ID |
|`createtime`| UTC datetime of video creation time in YYYY-MM-DD HH:MM:SS format |
|`author_name`| Unique author name |
|`author_id`| Unique author ID |
|`desc`| The full video description from the author |
|`hashtags`| A list of hashtags used in the video description |
|`share_video_id`| If the video is sharing another video, this is the video ID of that original video, else empty |
|`share_video_user_id`| If the video is sharing another video, this the user ID of the author of that video, else empty |
|`share_video_user_name`| If the video is sharing another video, this is the user name of the author of that video, else empty |
|`share_type`| If the video is sharing another video, this is the type of the share, stitch, duet etc. |
|`mentions`| A list of users mentioned in the video description, if any |
|`digg_count`| The number of likes on the video |
|`share_count`| The number of times the video was shared |
|`comment_count`| The number of comments on the video |
|`play_count`| The number of times the video was played |

The comment dataframe will contain the following columns:
|Field name | Description |
|----------|-----------|
|`comment_id`| Unique comment ID |
|`createtime`| UTC datetime of comment creation time in YYYY-MM-DD HH:MM:SS format |
|`author_name`| Unique author name |
|`author_id`| Unique author ID |
|`text`| Text of the comment |
|`mentions`| A list of users that are tagged in the comment |
|`video_id`| The ID of the video the comment is on |
|`comment_language`| The language of the comment, as predicted by the TikTok API |
|`digg_count`| The number of likes the comment got |
|`reply_comment_id`| If the comment is replying to another comment, this is the ID of that comment |

The user dataframe will contain the following columns:
|Field name | Description |
|----------|-----------|
|`id`| Unique author ID |
|`unique_id`| Unique user name |
|`nickname`| Display user name, changeable |
|`signature`| Short user description |
|`verified`| Whether or not the user is verified |
|`num_following`| How many other accounts the user is following |
|`num_followers`| How many followers the user has |
|`num_videos`| How many videos the user has made |
|`num_likes`| How many total likes the user has had |
|`createtime`| When the user account was made. This is derived from the `id` field, and can occasionally be incorrect with a very low unix epoch such as 1971 |

