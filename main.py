from fastapi import FastAPI, Query, Request
from fastapi.responses import PlainTextResponse, FileResponse
from typing import Optional
from pytubefix import YouTube
import requests
import os
import subprocess
import re

app = FastAPI()

DOWNLOAD_DIR = "audio_files"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

INVIDIOUS_INSTANCES = [
    "https://inv.tux.pizza",
    "https://invidious.nerdvpn.de",
    "https://invidious.drgns.space"
]

def clean_query(q: str) -> str:
    if not q:
        return ""
    return q.replace("*", "").replace("#", "").strip()

def get_video_id_from_youtube(search_term: str) -> Optional[str]:
    try:
        url = f"https://www.youtube.com/results?search_query={search_term}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            matches = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", res.text)
            if matches:
                return matches[0]
    except Exception as e:
        print(f"Search extraction error: {e}")
    return None

@app.get("/search_and_play", response_class=PlainTextResponse)
def search_and_play(request: Request, search_query: Optional[str] = Query(None)):
    print(f"--- Received search_query: '{search_query}' ---")

    if not search_query or search_query.strip().lower() in ["val", "none", ""]:
        return "read=t-אנא הקש את קוד החיפוש ולאחריו סולמית=search_query,1,20,5,Y,readdigits,*,no"

    search_term = clean_query(search_query)
    print(f"--- Cleaned search_term: '{search_term}' ---")

    if not search_term:
        return "read=t-הקש קוד חיפוש תקין ולאחריו סולמית=search_query,1,20,5,Y,readdigits,*,no"

    try:
        video_id = get_video_id_from_youtube(search_term)
        if not video_id:
            print("No video ID found")
            return "id_list_message=t-לא נמצאו תוצאות לחיפוש&go_to_folder=hangup"

        print(f"Found Video ID: {video_id}")
        output_wav = f"{DOWNLOAD_DIR}/{video_id}.wav"

        if os.path.exists(output_wav):
            file_url = f"https://my-yt-telephony-api.onrender.com/files/{video_id}.wav"
            return f"playfile={file_url}"

        audio_direct_url = None

        # 1. ניסיון חילוץ דרך pytubefix בלקוחות שונים
        for client_name in ['ANDROID_MUSIC', 'WEB', 'IOS']:
            try:
                yt = YouTube(f"https://www.youtube.com/watch?v={video_id}", client=client_name)
                audio_stream = yt.streams.filter(only_audio=True).first()
                if audio_stream:
                    audio_direct_url = audio_stream.url
                    print(f"Audio URL extracted via pytubefix ({client_name})")
                    break
            except Exception as e:
                print(f"pytubefix error ({client_name}): {e}")

        # 2. גיבוי דרך Invidious אם pytubefix נכשל
        if not audio_direct_url:
            for instance in INVIDIOUS_INSTANCES:
                try:
                    res = requests.get(f"{instance}/api/v1/videos/{video_id}", timeout=4)
                    if res.status_code == 200:
                        adaptive_formats = res.json().get('adaptiveFormats', [])
                        for fmt in adaptive_formats:
                            if fmt.get('type', '').startswith('audio/'):
                                audio_direct_url = fmt.get('url')
                                break
                        if audio_direct_url:
                            print(f"Audio URL extracted via Invidious ({instance})")
                            break
                except Exception as e:
                    print(f"Invidious backup error ({instance}): {e}")

        if not audio_direct_url:
            print("Audio extraction failed on all attempts")
            return "id_list_message=t-שגיאה בחילוץ השמע&go_to_folder=hangup"

        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', audio_direct_url,
            '-ar', '8000',
            '-ac', '1',
            '-acodec', 'pcm_s16le',
            output_wav
        ]
        subprocess.run(ffmpeg_cmd, check=True)

        file_url = f"https://my-yt-telephony-api.onrender.com/files/{video_id}.wav"
        return f"playfile={file_url}"

    except Exception as e:
        print(f"General processing error: {e}")
        return "id_list_message=t-התרחשה שגיאה בעיבוד הקטע&go_to_folder=hangup"

@app.get("/files/{file_name}")
def get_file(file_name: str):
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/wav")
    return PlainTextResponse("File not found", status_code=404)
