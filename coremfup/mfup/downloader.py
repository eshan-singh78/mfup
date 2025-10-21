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
        "merge_output_format": "mp4",
    }
    if extra_opts:
        opts.update(extra_opts)
    return opts

def get_video_resolutions(url, debug=False):

    try:
        with yt_dlp.YoutubeDL(_get_opts(debug)) as ydl:
            info = ydl.extract_info(url, download=False)
            resolutions = set()
            for f in info.get("formats", []):
                if f.get("vcodec") != "none" and f.get("height"):
                    resolutions.add(f["height"])
            return sorted(resolutions)
    except Exception as e:
        print(f"[!] Error fetching formats: {e}")
        return []

def download_video(url, resolution="best", debug=False):

    if resolution != "best":
        fmt = f"bestvideo[height<={resolution}]+bestaudio/best"
    else:
        fmt = "bestvideo+bestaudio/best"

    opts = _get_opts(debug, {"format": fmt})
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

def download_video_only(url, resolution="best", debug=False):

    if resolution != "best":
        fmt = f"bestvideo[height<={resolution}]"
    else:
        fmt = "bestvideo"

    opts = _get_opts(debug, {"format": fmt})
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

def choose_resolution(url):

    resolutions = get_video_resolutions(url)
    if not resolutions:
        return "best"

    print("Available resolutions:", ", ".join(map(str, resolutions)))
    choice = input("Choose resolution (or press Enter for best): ").strip()
    if choice.isdigit() and int(choice) in resolutions:
        return int(choice)
    return "best"

if __name__ == "__main__":
    url = input("Enter YouTube URL: ").strip()
    mode = input("What do you want to download? (video/audio/video_only) ").strip().lower()

    if mode in ["video", "video_only"]:
        resolution = choose_resolution(url)
        if mode == "video":
            download_video(url, resolution)
        else:
            download_video_only(url, resolution)
    elif mode == "audio":
        audio_format = input("Audio format (mp3/m4a/etc.): ").strip() or "mp3"
        download_audio(url, audio_format)
    else:
        print("Invalid option.")
