# שימוש בתמונת בסיס קלה של Python
FROM python:3.10-slim

# התקנת ffmpeg ועדכון חבילות מערכת
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# הגדרת תיקיית העבודה בתוך הקונטיינר
WORKDIR /app

# העתקת קובץ הדרישות והתקנת ספריות Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# העתקת שאר קובצי הפרויקט
COPY . .

# חשיפת הפורט
EXPOSE 10000

# הרצת השרת באמצעות uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
