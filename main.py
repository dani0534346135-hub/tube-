from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse, FileResponse
import yt_dlp
import os
import subprocess

app = FastAPI()

DOWNLOAD_DIR = "audio_files"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.get("/search_and_play", response_class=PlainTextResponse)
def search_and_play(search_query: str = Query(...)):
    try:
        # הגדרות לעקיפת חסימת בוטים בשרתי ענן
        ydl_opts = {
            'format': 'bestaudio/best',
            'default_search': 'ytsearch1:',
            'outtmpl': f'{DOWNLOAD_DIR}/temp.%(ext)s',
            'noplaylist': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios']
                }
            },
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=True)
            if 'entries' in info and len(info['entries']) > 0:
                video_info = info['entries'][0]
            else:
                video_info = info
                
            video_id = video_info['id']
            downloaded_file = ydl.prepare_filename(video_info)

        # המרת הקובץ לפורמט WAV המותאם לטלפוניה (8kHz Mono)
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
        
        # מחיקת הקובץ המקורי
        if os.path.exists(downloaded_file):
            os.remove(downloaded_file)

        # החזרת הפקודה להשמעה במערכת ימות המשיח
        file_url = f"https://my-yt-telephony-api.onrender.com/files/{video_id}.wav"
        return f"id_list_message=t-נמצא הקטע המבוקש&playfile={file_url}"

    except Exception as e:
        print(f"Error: {e}")
        return "id_list_message=t-תרחשה שגיאה בחיפוש הקטע"

# נתיב להורדת קובץ השמע המורד והמומר
@app.get("/files/{file_name}")
def get_file(file_name: str):
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/wav")
    return PlainTextResponse("File not found", status_code=404)
