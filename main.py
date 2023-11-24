from fastapi import FastAPI, HTTPException
from ai_utils import youtube_to_mp3, mp3_to_text, summarize_text
from openai import OpenAI
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()  # .env 파일에서 환경 변수를 불러옵니다.
app = FastAPI()
client = OpenAI()

mysql_params = {
    "host": os.getenv("DB_HOST"),
    "port": 3306,
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "cursorclass": pymysql.cursors.DictCursor,
    "charset": "utf8"
}
conn = pymysql.connect(**mysql_params)
def get_summary_from_db(youtube_id):
    with conn.cursor() as cursor:
        query = "SELECT summary FROM recipe WHERE youtube_id = %s"
        cursor.execute(query, (youtube_id,))
        result = cursor.fetchone()
        return result
def insert_summary_into_db(youtube_id, summary):
    try:
        with conn.cursor() as cursor:
            query = "UPDATE recipe SET summary = %s WHERE youtube_id = %s"
            cursor.execute(query, (summary, youtube_id))
            conn.commit()
    except Exception as e:
        print(f"An error occurred: {e}")

@app.get("/summary/{youtube_id}")
async def process_video(youtube_id: str):

    # youtube_id로 DB의 record를 찾고, record의 summary가 null이 아니면 summary 값을 가져온다.
    db_record = get_summary_from_db(youtube_id)
    if db_record and db_record['summary']:
        print(db_record['summary'])
        return {"summary": db_record['summary']}

    # DB에 record가 없으면, youtube_id로 youtube_to_mp3를 실행한다.    
    mp3_file_path = youtube_to_mp3(youtube_id)
    
    if mp3_file_path:
        text = mp3_to_text(mp3_file_path)
        if text:
            summary = summarize_text(text, client)
            insert_summary_into_db(youtube_id, summary)
            return {"summary": summary}
        else:
            raise HTTPException(status_code=500, detail="Error in converting MP3 to text")
    else:
        raise HTTPException(status_code=500, detail="Error in converting YouTube video to MP3")
    
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)