# youtube-utils

Small command-line tools for working with YouTube videos.

## yt_transcript.py

A command-line tool that downloads the subtitles (transcript) of a YouTube video.

### What it does

1. **Scans the video for subtitles.** Give it a YouTube link or video ID and it asks
   YouTube which subtitle tracks exist, then lists each one with its language and
   whether it was written by a person (`manual`) or created automatically by
   YouTube (`auto-generated`).
2. **Lets you pick a language.** Choose from the list by number or language code,
   or skip the list entirely with `--lang`.
3. **Downloads the subtitles** and saves them to a file as plain text, or as
   SRT / WebVTT subtitle files, or JSON with timestamps.

Other behaviour:

- **Smart naming.** Files are named after the video title, video ID and language,
  e.g. `My Video - abc123XYZ_0.English (auto-generated).txt`. If the title can't be
  looked up (offline, private video), it falls back to `<video id>.<language>.<format>`.
  Characters Windows doesn't allow in file names are removed.
- **Prefers human subtitles.** If a language has both manual and auto-generated
  tracks, `--lang` picks the manual one.
- **Translation fallback.** If you ask for a language the video doesn't have,
  YouTube's machine translation is used when it's offered.
- **Accepts most link styles**: `youtube.com/watch?v=…`, `youtu.be/…`,
  `/shorts/…`, `/embed/…`, `/live/…`, or a bare 11-character video ID.

No YouTube API key or login is needed.

### Setup

Requires Python 3.9+.

```bash
pip install -r requirements.txt
```

### Usage

```bash
python yt_transcript.py "<youtube-url-or-id>"                # list languages, then pick one
python yt_transcript.py "<url>" --list                       # only list languages
python yt_transcript.py "<url>" --lang en                    # download a language directly
python yt_transcript.py "<url>" --lang es --format srt       # formats: txt (default), srt, vtt, json
python yt_transcript.py "<url>" --lang en -o myfile.txt      # choose the output file name
```

Quote the URL in Bash, otherwise `&` in the URL is treated as a shell operator.

### Example

```
$ python yt_transcript.py "https://www.youtube.com/watch?v=abc123XYZ_0"
Available subtitles:
   1. English [en] (manual)
   2. Japanese [ja] (manual)
   3. English (auto-generated) [en] (auto-generated)

Pick a number or language code (blank to quit): 2
Saved Japanese subtitles to My Video - abc123XYZ_0.Japanese.txt
```

### Troubleshooting

- **`IpBlocked` / `RequestBlocked`** – YouTube is temporarily rate-limiting your IP,
  usually after many requests in a short time. Wait a while and try again.
- **"This video has no subtitles"** – the uploader hasn't added any and YouTube
  hasn't generated them.
- **The pick-a-number prompt freezes in Git Bash** – run it as
  `winpty python yt_transcript.py …`, or use `--lang` to skip the prompt.

## Web page (web.py)

The same downloader as a small password-protected web page, so a few people can
use it from a browser: paste a link, pick a language and format, click Download.

It runs on your own computer and is shared through a free
[Cloudflare quick tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/),
so YouTube sees requests coming from your home connection (YouTube blocks most
cloud-server IPs, which is why this isn't hosted on a cloud service).

### Setup (once)

1. `pip install -r requirements.txt`
2. Install cloudflared: `winget install --id Cloudflare.cloudflared`
3. Choose a password and save it: `echo 'your-password' > .subs_password`
   (this file is git-ignored)

### Start it

```bash
./start.sh
```

Look for the `https://....trycloudflare.com` link in the output and send it, with
the password, to the people using it. When the browser asks for a login, any
username works; only the password is checked.

- The page works only while `start.sh` is running and your computer is on.
- **The link changes every time `start.sh` restarts.** For a permanent address you
  need a domain on a Cloudflare account and a named tunnel.
- To run only the page locally without a tunnel:
  `SUBS_PASSWORD=your-password python web.py`, then open http://127.0.0.1:8080
