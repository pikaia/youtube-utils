"""Small password-protected web page for downloading YouTube subtitles.

Usage:
    SUBS_PASSWORD=yourpassword python web.py      # serves http://127.0.0.1:8080
"""

import hmac
import os
import sys

from flask import Flask, Response, jsonify, request
from waitress import serve
from youtube_transcript_api import YouTubeTranscriptApi

from yt_transcript import FORMATTERS, extract_video_id, get_video_title, safe_filename

PASSWORD = os.environ.get("SUBS_PASSWORD", "")
HOST = os.environ.get("SUBS_HOST", "127.0.0.1")
PORT = int(os.environ.get("SUBS_PORT", "8080"))

app = Flask(__name__)


@app.before_request
def require_password():
    if request.path == "/":
        return None
    auth = request.authorization
    if auth and auth.password and hmac.compare_digest(auth.password, PASSWORD):
        return None
    return Response(
        "Password required.", 401, {"WWW-Authenticate": 'Basic realm="Subtitles"'}
    )


def error_message(e):
    reason = type(e).__name__
    if reason in ("IpBlocked", "RequestBlocked"):
        return "YouTube is temporarily blocking requests. Wait a while and try again."
    if reason == "TranscriptsDisabled":
        return "This video has no subtitles."
    if reason == "VideoUnavailable":
        return "That video is unavailable (private, deleted or the link is wrong)."
    return f"Could not get subtitles ({reason})."


@app.get("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.get("/api/languages")
def languages():
    try:
        video_id = extract_video_id(request.args.get("url", "").strip())
    except ValueError:
        return jsonify(error="That doesn't look like a YouTube link."), 400
    try:
        transcripts = list(YouTubeTranscriptApi().list(video_id))
    except Exception as e:
        return jsonify(error=error_message(e)), 502
    if not transcripts:
        return jsonify(error="This video has no subtitles."), 404
    return jsonify(
        video_id=video_id,
        title=get_video_title(video_id),
        tracks=[
            {"language": t.language, "code": t.language_code, "generated": t.is_generated}
            for t in transcripts
        ],
    )


@app.get("/api/download")
def download():
    video_id = request.args.get("v", "")
    code = request.args.get("code", "")
    generated = request.args.get("generated") == "1"
    fmt = request.args.get("format", "txt")
    if fmt not in FORMATTERS:
        return "Unknown format.", 400
    try:
        video_id = extract_video_id(video_id)
        transcripts = YouTubeTranscriptApi().list(video_id)
        transcript = next(
            t for t in transcripts if t.language_code == code and t.is_generated == generated
        )
        fetched = transcript.fetch()
    except StopIteration:
        return "That subtitle track no longer exists.", 404
    except ValueError:
        return "Bad video ID.", 400
    except Exception as e:
        return error_message(e), 502

    text = FORMATTERS[fmt]().format_transcript(fetched)
    filename = f"{video_id}.{safe_filename(transcript.language)}.{fmt}"
    title = get_video_title(video_id)
    if title and safe_filename(title):
        filename = f"{safe_filename(title)} - {filename}"

    response = Response(text, mimetype="application/octet-stream")
    response.headers.set("Content-Disposition", "attachment", filename=filename)
    return response


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YouTube Subtitle Downloader</title>
<meta property=\"og:title\" content=\"YouTube Subtitle Downloader\">
<meta property=\"og:description\" content=\"Download subtitles from a YouTube video: paste a link, pick a language and a format (text, SRT, WebVTT or JSON), and save the file. Human-written and auto-generated tracks are listed.\">
<meta property=\"og:type\" content=\"website\">
<style>
  :root {
    --bg: #f6f7f9; --card: #ffffff; --text: #1d2330; --muted: #5d6676;
    --border: #d9dde4; --accent: #2f6fde; --accent-text: #ffffff; --error: #b42318;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #14171c; --card: #1d2128; --text: #e7eaf0; --muted: #9aa3b2;
      --border: #333a45; --accent: #5b8ff0; --accent-text: #0d1117; --error: #ff7b72;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  main { max-width: 640px; margin: 0 auto; padding: 32px 16px; }
  h1 { font-size: 1.5rem; margin: 0 0 4px; }
  .sub { color: var(--muted); margin: 0 0 24px; }
  .card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 20px; margin-bottom: 16px;
  }
  form { display: flex; gap: 8px; flex-wrap: wrap; }
  input[type=text], select {
    flex: 1 1 240px; min-width: 0; padding: 10px 12px; font: inherit; color: var(--text);
    background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
  }
  button {
    padding: 10px 16px; font: inherit; font-weight: 600; cursor: pointer;
    background: var(--accent); color: var(--accent-text); border: 0; border-radius: 8px;
  }
  button:disabled { opacity: .6; cursor: default; }
  .title { font-weight: 600; margin: 0 0 12px; overflow-wrap: anywhere; }
  .tracks { list-style: none; margin: 0 0 16px; padding: 0; }
  .tracks label {
    display: flex; align-items: center; gap: 10px; padding: 8px 10px;
    border-radius: 8px; cursor: pointer;
  }
  .tracks label:hover { background: var(--bg); }
  .tag { color: var(--muted); font-size: .85rem; }
  .row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
  .row select { flex: 0 1 200px; }
  .error { color: var(--error); margin: 0; }
  [hidden] { display: none !important; }
</style>
</head>
<body>
<main>
  <h1>Subtitle Downloader</h1>
  <p class="sub">Paste a YouTube link to see which subtitles it has.</p>

  <div class="card">
    <form id="lookup">
      <input type="text" id="url" placeholder="https://www.youtube.com/watch?v=..." required>
      <button id="find">Find subtitles</button>
    </form>
  </div>

  <p class="error" id="error" hidden></p>

  <div class="card" id="results" hidden>
    <p class="title" id="title"></p>
    <ul class="tracks" id="tracks"></ul>
    <div class="row">
      <select id="format" aria-label="Format">
        <option value="txt">Plain text (.txt)</option>
        <option value="srt">SubRip (.srt)</option>
        <option value="vtt">WebVTT (.vtt)</option>
        <option value="json">JSON with timings (.json)</option>
      </select>
      <button id="download" type="button">Download</button>
    </div>
  </div>
</main>
<script>
  const $ = (id) => document.getElementById(id);
  let videoId = null;

  function showError(msg) {
    $("error").textContent = msg;
    $("error").hidden = !msg;
  }

  $("lookup").addEventListener("submit", async (e) => {
    e.preventDefault();
    showError("");
    $("results").hidden = true;
    $("find").disabled = true;
    $("find").textContent = "Looking...";
    try {
      const res = await fetch("api/languages?url=" + encodeURIComponent($("url").value));
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Something went wrong.");
      videoId = data.video_id;
      $("title").textContent = data.title || data.video_id;
      $("tracks").innerHTML = "";
      data.tracks.forEach((t, i) => {
        const li = document.createElement("li");
        const label = document.createElement("label");
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "track";
        radio.value = JSON.stringify({ code: t.code, generated: t.generated });
        radio.checked = i === 0;
        const name = document.createElement("span");
        name.textContent = t.language;
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = t.generated ? "auto-generated" : "manual";
        label.append(radio, name, tag);
        li.append(label);
        $("tracks").append(li);
      });
      $("results").hidden = false;
    } catch (err) {
      showError(err.message);
    } finally {
      $("find").disabled = false;
      $("find").textContent = "Find subtitles";
    }
  });

  $("download").addEventListener("click", () => {
    const picked = document.querySelector("input[name=track]:checked");
    if (!picked || !videoId) return;
    const t = JSON.parse(picked.value);
    const params = new URLSearchParams({
      v: videoId, code: t.code, generated: t.generated ? "1" : "0", format: $("format").value,
    });
    window.location.href = "api/download?" + params;
  });
</script>
</body>
</html>
"""


if __name__ == "__main__":
    if not PASSWORD:
        sys.exit("Set the SUBS_PASSWORD environment variable before starting the server.")
    print(f"Serving on http://{HOST}:{PORT}")
    serve(app, host=HOST, port=PORT)
