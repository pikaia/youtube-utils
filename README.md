# youtube-utils

Small command-line tools for working with YouTube videos.

## yt_transcript.py

Lists the subtitle languages a YouTube video has and downloads the one you pick.

### Setup

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

Files are saved as `<video title> - <video id>.<language name>.<format>`,
e.g. `My Video - abc123XYZ_0.English (auto-generated).txt`.

- Manual subtitles are preferred over auto-generated ones for the same language.
- If a requested language isn't available, YouTube's machine translation is used when offered.
- If YouTube rate-limits you (`IpBlocked`), wait a while and try again.
