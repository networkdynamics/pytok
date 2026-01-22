import asyncio
import logging
import os

from dotenv import load_dotenv

from pytok.tiktok import PyTok

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    # Get credentials from environment variables
    username = os.environ.get('TIKTOK_USERNAME')
    password = os.environ.get('TIKTOK_PASSWORD')

    if not username or not password:
        print("Set TIKTOK_USERNAME and TIKTOK_PASSWORD environment variables")
        print("Example: TIKTOK_USERNAME=user@email.com TIKTOK_PASSWORD=pass python login_example.py")
        return

    async with PyTok(logging_level=logging.INFO) as api:
        print("Attempting login...")
        # Note: TikTok may require email/SMS verification after entering credentials.
        # You'll need to complete verification manually in the browser window.
        await api.login(username=username, password=password, timeout=300)
        print("Login successful!")

        # Verify we're logged in by fetching user info
        user = api.user(username="tiktok")
        user_data = await user.info()
        print(f"Verified: fetched info for @{user_data.get('uniqueId', 'unknown')}")

if __name__ == "__main__":
    asyncio.run(main())
