from fastapi import FastAPI, Query, Request
from fastapi.responses import PlainTextResponse, FileResponse
from typing import Optional
import requests
import os
import subprocess
import re

app = FastAPI()

DOWNLOAD_DIR = "audio_files"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# שרתי Invidious מעודכנים לחילוץ הקישור הישיר
INVIDIOUS_NODES = [
    "https://invidious.nerdvpn.de",
    "https://inv.tux.pizza",
    "https://invidious.drgns.space",
    "https://vid.puffyan.us"
]

def clean_query(q: str) -> str:
    if not q:
        return ""
    return q.replace("*", "").replace("#", "").strip()

def get_video_id_from_youtube(search_term: str) -> Optional[str]:
    """מציאת מזהה הסרטון מיוטיוב"""
    try:
        url = f"https://www.youtube.com/results?search_query={search_term}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            matches = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", res.text)
            if matches:
                return matches[0]
    except Exception as e:
        print(f"Search error: {e}")
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

        # אם הקובץ כבר קיים בשרת
        if os.path.exists(output_wav):
            file_url = f"https://my-yt-telephony-api.onrender.com/files/{video_id}.wav"
            return f"playfile={file_url}"

        audio_stream_url = None

        # חילוץ הלינק הישיר לשמע משרתי Invidious
        for node in INVIDIOUS_NODES:
            try:
                api_url = f"{node}/api/v1/videos/{video_id}"
                res = requests.get(api_url, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    adaptive_formats = data.get("adaptiveFormats", [])
                    for fmt in adaptive_formats:
                        if fmt.get("type", "").startswith("audio/"):
                            audio_stream_url = fmt.get("url")
                            break
                    if audio_stream_url:
                        print(f"Successfully extracted stream URL via {node}")
                        break
            except Exception as e:
                print(f"Node error ({node}): {e}")
                continue

        if not audio_stream_url:
            print("Failed to get audio stream URL from all nodes")
            return "id_list_message=t-שגיאה בחילוץ השמע&go_to_folder=hangup"

        # המרה ישירה ל-WAV טלפוני (8kHz Mono PCM) דרך ffmpeg מתוך ה-Stream
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', audio_stream_url,
            '-ar', '8000',
            '-ac', '1',
            '-acodec', 'pcm_s16le',
            output_wav
        ]
        print("Executing ffmpeg stream conversion...")
        subprocess.run(ffmpeg_cmd, check=True, timeout=60)

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
