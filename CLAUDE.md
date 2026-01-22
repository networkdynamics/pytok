# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyTok is a TikTok web scraping library using a dual-approach architecture:
- **Primary**: Uses the TikTok-Api library for API requests
- **Fallback**: Automatically falls back to browser automation (zendriver) when API fails

All operations are async/await based.

## Commands

```bash
# Install
pip install git+https://github.com/networkdynamics/pytok.git@master

# Run scripts (using a conda environment)
conda run -n <env> python <script>

# Run tests
conda run -n <env> pytest tests/

# Run single test
conda run -n <env> pytest tests/test_user.py::test_user_videos
```

## Architecture

```
PyTok (tiktok.py)
├── zendriver browser - CDP network response tracking
├── TikTok-Api client - API requests with msToken from browser cookies
└── Request cache - stores recent API responses

API Classes (api/*.py) - all inherit from Base
├── User - user info, videos
├── Video - metadata, bytes, comments, related videos
├── Hashtag - hashtag info and videos
├── Search, Sound, Trending (partial implementations)
```

### Key Design Pattern: API-First with Fallback

Every data-fetching method follows this pattern:
```python
try:
    response = await self.parent.tiktok_api.make_request(...)
except ApiFailedException:
    # Fallback to browser scraping
```

### CDP Network Tracking

PyTok tracks network responses via Chrome DevTools Protocol:
- Captures responses matching `/api/`, `video/tos`, `v16-webapp`, `v19-webapp` URL patterns
- Stores response bodies before Chrome garbage collects them
- Used to extract video bytes and API data from page loads

### Captcha Handling

- Automatic solving via OpenCV image matching (`captcha_solver.py`)
- Supports slide and whirl puzzle types
- Manual solving available with `manual_captcha_solves=True`

## Key Files

- `tiktok.py` - Main entry point, manages browser and API client
- `api/base.py` - Base class with DOM interaction, captcha detection, scrolling
- `api/user.py` - User data and video fetching
- `api/video.py` - Video metadata, bytes download, comments
- `helpers.py` - HTML parsing, extracts `__UNIVERSAL_DATA_FOR_REHYDRATION__` JSON from pages
- `utils.py` - DataFrame conversion helpers (`get_video_df`, `get_comment_df`, `get_user_df`)

## PyTok Constructor Options

```python
PyTok(
    logging_level=logging.WARNING,
    request_delay=0,           # seconds between requests
    headless=False,            # headless doesn't work reliably
    manual_captcha_solves=False,
    log_captcha_solves=False,  # save captcha data to JSON files
)
```

## Usage Pattern

```python
async with PyTok() as api:
    user = api.user(username="therock")
    user_data = await user.info()

    async for video in user.videos(count=100):
        video_data = video.info()
        video_bytes = await video.bytes()
```
