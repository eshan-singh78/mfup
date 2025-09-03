import yt_dlp
import sys

def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '').strip()
        speed = d.get('_speed_str', '').strip()
        eta = d.get('_eta_str', '').strip()
        sys.stdout.write(f"\rDownloading: {percent} | {speed} | ETA {eta}   ")
        sys.stdout.flush()
    elif d['status'] == 'finished':
        print("\nDownload complete, finalizing...")

def _get_opts(debug=False, extra_opts=None):
    opts = {
        "quiet": not debug,       
        "no_warnings": not debug,
        "progress_hooks": [progress_hook],
        "outtmpl": "%(title)s.%(ext)s",
    }
    if extra_opts:
        opts.update(extra_opts)
    return opts

def get_video_formats(url, debug=False):

    try:
        with yt_dlp.YoutubeDL(_get_opts(debug)) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            for f in info.get("formats", []):
                if f.get("vcodec") != "none":
                    res = f.get("format_note") or f.get("resolution")
                    if res and res not in formats:
                        formats.append(res)
            return formats or ["best"]
    except Exception as e:
        print(f"[!] Error fetching formats: {e}")
        return ["best"]

def download_video(url, quality="best", debug=False):

    opts = _get_opts(debug, {
        "format": f"bestvideo[format_note={quality}]+bestaudio/best / best",
        "merge_output_format": "mp4",
    })
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

def download_video_only(url, quality="best", debug=False):

    opts = _get_opts(debug, {
        "format": f"bestvideo[format_note={quality}] / bestvideo",
    })
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

def download_audio(url, audio_format="mp3", debug=False):

    opts = _get_opts(debug, {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "192",
            }
        ],
    })
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
