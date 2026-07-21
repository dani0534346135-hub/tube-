from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse
import yt_dlp
import os
import subprocess

app = FastAPI()

# תיקייה זמנית לשמירת הקבצים המומרים
DOWNLOAD_DIR = "audio_files"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.get("/search_and_play", response_class=PlainTextResponse)
def search_and_play(search_query: str = Query(...)):
    try:
        # 1. הגדרת yt-dlp לחיפוש והורדת השמע בלבד
        ydl_opts = {
            'format': 'bestaudio/best',
            'default_search': 'ytsearch1:',  # מחפש ומחזיר את התוצאה הראשונה
            'outtmpl': f'{DOWNLOAD_DIR}/temp.%(ext)s',
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=True)
            video_id = info['entries'][0]['id']
            downloaded_file = ydl.prepare_filename(info['entries'][0])

        # 2. המרת הקובץ לפורמט טלפוני מותאם לימות המשיח (WAV 8kHz Mono)
        output_wav = f"{DOWNLOAD_DIR}/{video_id}.wav"
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', downloaded_file,
            '-ar', '8000',
            '-ac', '1',
            '-acodec', 'pcm_s16le',
            output_wav
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        
        # מחיקת הקובץ המקורי שנשמר בלתי מומרי
        if os.path.exists(downloaded_file):
            os.remove(downloaded_file)

        # 3. החזרת פקודת השמעה בפורמט של ימות המשיח
        # יש להחליף את YOUR_SERVER_URL בכתובת השרת שיקודם ב-Render
        file_url = f"https://YOUR_SERVER_URL/files/{video_id}.wav"
        return f"id_list_message=t-נמצא הקטע המבוקש&playfile={file_url}"

    except Exception as e:
        return "id_list_message=t-תרחשה שגיאה בחיפוש הקטע"
