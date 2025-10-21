import yt_dlp
import sys
from typing import Optional

def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '').strip()
        speed = d.get('_speed_str', '').strip()
        eta = d.get('_eta_str', '').strip()
        sys.stdout.write(f"\rDownloading: {percent} | {speed} | ETA {eta}   ")
        sys.stdout.flush()
    elif d['status'] == 'finished':
        print("\nDownload complete, finalizing...")

def _get_opts(debug=False, extra_opts=None, cookies: Optional[str] = None):
    opts = {
        "quiet": not debug,
        "no_warnings": not debug,
        "progress_hooks": [progress_hook],
        "outtmpl": "%(title)s.%(ext)s",
        "merge_output_format": "mp4",
        "noplaylist": True,
        "geo_bypass": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/116.0.0.0 Safari/537.36",
            "Referer": "https://www.youtube.com/"
        }
    }
    if cookies:
        opts["cookiefile"] = cookies
    if extra_opts:
        opts.update(extra_opts)
    return opts

def get_video_resolutions(url, debug=False, cookies: Optional[str] = None):
    try:
        with yt_dlp.YoutubeDL(_get_opts(debug, cookies=cookies)) as ydl:
            info = ydl.extract_info(url, download=False)
            resolutions = set()
            for f in info.get("formats", []):
                if f.get("vcodec") != "none" and f.get("height"):
                    resolutions.add(f["height"])
            return sorted(resolutions)
    except Exception as e:
        print(f"[!] Error fetching formats: {e}")
        return []

def get_video_formats(url, debug=False, cookies: Optional[str] = None):
    """Return resolutions as strings for InquirerPy choices"""
    return [str(r) for r in get_video_resolutions(url, debug, cookies)]

def download_video(url, resolution="best", debug=False, cookies: Optional[str] = None):
    fmt = f"bestvideo[height<={resolution}]+bestaudio/best" if resolution != "best" else "bestvideo+bestaudio/best"
    opts = _get_opts(debug, {"format": fmt}, cookies=cookies)
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

def download_video_only(url, resolution="best", debug=False, cookies: Optional[str] = None):
    fmt = f"bestvideo[height<={resolution}]" if resolution != "best" else "bestvideo"
    opts = _get_opts(debug, {"format": fmt}, cookies=cookies)
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

def download_audio(url, audio_format="mp3", debug=False, cookies: Optional[str] = None):
    opts = _get_opts(debug, {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "192",
            }
        ],
    }, cookies=cookies)
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
