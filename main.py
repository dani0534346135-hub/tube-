from fastapi import FastAPI, Query, Request
from fastapi.responses import PlainTextResponse, FileResponse
from typing import Optional
import requests
import os
import subprocess

app = FastAPI()

DOWNLOAD_DIR = "audio_files"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

INVIDIOUS_INSTANCES = [
    "https://invidious.nerdvpn.de",
    "https://inv.tux.pizza",
    "https://invidious.drgns.space"
]

def clean_query(q: str) -> str:
    if not q:
        return ""
    # ניקוי תווים מיוחדים
    return q.replace("*", "").replace("#", "").strip()

@app.get("/search_and_play", response_class=PlainTextResponse)
def search_and_play(request: Request, search_query: Optional[str] = Query(None)):
    # הדפסת ה-URL המלא שנרשם בלוגים של Render לבדיקה
    print(f"--- Incoming Request URL: {request.url} ---")
    print(f"--- Received search_query: '{search_query}' ---")

    # אם לא התקבל קלט או שהתקבל ערך ריק
    if not search_query or search_query.strip().lower() in ["val", "none", ""]:
        # readdigits משמיע למאזין את הספרות שהוא מקיש
        return "read=t-אנא הקש את קוד החיפוש ולאחריו סולמית=search_query,1,20,5,Y,readdigits,*,no"

    search_term = clean_query(search_query)
    print(f"--- Cleaned search_term: '{search_term}' ---")

    if not search_term:
        return "read=t-הקש קוד חיפוש תקין ולאחריו סולמית=search_query,1,20,5,Y,readdigits,*,no"

    try:
        video_id = None
        
        # חיפוש ה-Video ID
        for instance in INVIDIOUS_INSTANCES:
            try:
                search_url = f"{instance}/api/v1/search?q={search_term}&type=video"
                print(f"Searching at: {search_url}")
                res = requests.get(search_url, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    if data and len(data) > 0:
                        video_id = data[0]['videoId']
                        print(f"Found Video ID: {video_id}")
                        break
            except Exception as e:
                print(f"Invidious search error ({instance}): {e}")
                continue

        if not video_id:
            print("No video ID found for this query.")
            return "id_list_message=t-לא נמצאו תוצאות לחיפוש&go_to_folder=hangup"

        output_wav = f"{DOWNLOAD_DIR}/{video_id}.wav"

        # אם הקובץ כבר קיים
        if os.path.exists(output_wav):
            file_url = f"https://my-yt-telephony-api.onrender.com/files/{video_id}.wav"
            return f"playfile={file_url}"

        # חילוץ כתובת השמע
        audio_url = None
        for instance in INVIDIOUS_INSTANCES:
            try:
                video_data_url = f"{instance}/api/v1/videos/{video_id}"
                res = requests.get(video_data_url, timeout=5)
                if res.status_code == 200:
                    adaptive_formats = res.json().get('adaptiveFormats', [])
                    for fmt in adaptive_formats:
                        if fmt.get('type', '').startswith('audio/'):
                            audio_url = fmt.get('url')
                            break
                    if audio_url:
                        break
            except Exception as e:
                print(f"Invidious video data error ({instance}): {e}")
                continue

        if not audio_url:
            print("Audio URL extraction failed.")
            return "id_list_message=t-שגיאה בחילוץ השמע&go_to_folder=hangup"

        # המרה ל-WAV
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', audio_url,
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
