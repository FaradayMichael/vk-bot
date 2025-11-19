import asyncio
import os

import yt_dlp

from app.utils.files import DOWNLOADS_DIR


async def download_video(url: str, folder: str = DOWNLOADS_DIR) -> str:
    ydl_opts = {
        "outtmpl": f"{folder}/%(title)s.mp4",
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        filename = await asyncio.to_thread(_download, ydl, url)
    return os.path.join(folder, filename)


def _download(ydl: yt_dlp.YoutubeDL, url: str) -> str:
    ydl.download([url])
    info = ydl.extract_info(url, download=True)
    return f"{info['title']}.{info['video_ext']}"


def reformat_short(url: str) -> str:
    if "shorts" in url:
        return f"https://youtu.be/{url.split('/')[-1]}"
    return url
