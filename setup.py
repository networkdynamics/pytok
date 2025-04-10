from distutils.core import setup
import os.path
import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pytok",
    packages=setuptools.find_packages(),
    version="0.0.1",
    license="MIT",
    description="Playwright based version of The Unofficial TikTok API Wrapper in Python 3.",
    author="Ben Steel",
    author_email="bendavidsteel@gmail.com",
    url="https://github.com/networkdynamics/pytok",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=["tiktok", "python3", "api", "unofficial", "tiktok-api", "tiktok api"],
    install_requires=["requests", "playwright", "undetected_playwright", "pyvirtualdisplay", "tqdm", "opencv-python", "brotli", "patchright", "pyclick"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
