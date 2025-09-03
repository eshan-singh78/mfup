import argparse
from InquirerPy import inquirer
from mfup.downloader import download_audio, download_video, download_video_only, get_video_formats

def main():
    parser = argparse.ArgumentParser(description="mfup - Media Fire Up")
    parser.add_argument("url", help="Media link (YouTube, etc.)")
    parser.add_argument("--debug", action="store_true", help="Show detailed yt-dlp logs")
    args = parser.parse_args()


    debug_mode = args.debug

    choice = inquirer.select(
        message="What do you want to download?",
        choices=["Audio only", "Video (with audio)", "Video only (no audio)"],
    ).execute()

    if choice in ["Video (with audio)", "Video only (no audio)"]:
        formats = get_video_formats(args.url, debug=debug_mode)
        quality = inquirer.select(
            message="Choose video quality:",
            choices=formats,
        ).execute()

        if choice == "Video (with audio)":
            download_video(args.url, quality, debug=debug_mode)
        else:
            download_video_only(args.url, quality, debug=debug_mode)

    elif choice == "Audio only":
        audio_format = inquirer.select(
            message="Choose audio format:",
            choices=["mp3", "wav"],
        ).execute()
        download_audio(args.url, audio_format, debug=debug_mode)

if __name__ == "__main__":
    main()
