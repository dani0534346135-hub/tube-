from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse, FileResponse
import requests
import os
import subprocess

app = FastAPI()

DOWNLOAD_DIR = "audio_files"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# רשימת שרתי Invidious אמינים למקרה שאחד מהם לא זמין
INVIDIOUS_INSTANCES = [
    "https://invidious.nerdvpn.de",
    "https://inv.tux.pizza",
    "https://invidious.drgns.space"
]

@app.get("/search_and_play", response_class=PlainTextResponse)
def search_and_play(search_query: str = Query(...)):
    # אם התקבל המילה val בטעות, מציגים הודעת שגיאה מובנית
    if search_query.strip().lower() == "val":
        return "id_list_message=t-לא הוקש קוד חיפוש תקין"

    try:
        video_id = None
        
        # 1. חיפוש ה-Video ID דרך Invidious API
        for instance in INVIDIOUS_INSTANCES:
            try:
                search_url = f"{instance}/api/v1/search?q={search_query}&type=video"
                res = requests.get(search_url, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    if data and len(data) > 0:
                        video_id = data[0]['videoId']
                        break
            except Exception:
                continue

        if not video_id:
            return "id_list_message=t-לא נמצאו תוצאות לחיפוש"

        output_wav = f"{DOWNLOAD_DIR}/{video_id}.wav"

        # אם הקובץ כבר קיים בשרת, מחזירים אותו מיידית
        if os.path.exists(output_wav):
            file_url = f"https://my-yt-telephony-api.onrender.com/files/{video_id}.wav"
            return f"id_list_message=t-נמצא הקטע המבוקש&playfile={file_url}"

        # 2. קבלת לינק ישיר להורדת השמע דרך Invidious
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
            except Exception:
                continue

        if not audio_url:
            return "id_list_message=t-שגיאה בחילוץ השמע"

        # 3. המרת השמע באמצעות FFmpeg ישירות מה-URL ל-WAV
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
        return f"id_list_message=t-נמצא הקטע המבוקש&playfile={file_url}"

    except Exception as e:
        print(f"Error: {e}")
        return "id_list_message=t-תרחשה שגיאה בעיבוד הקטע"

@app.get("/files/{file_name}")
def get_file(file_name: str):
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/wav")
    return PlainTextResponse("File not found", status_code=404)
