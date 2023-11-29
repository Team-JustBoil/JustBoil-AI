from fastapi import FastAPI, HTTPException
import pytube
from ai_utils import youtube_to_mp3, mp3_to_text, summarize_text
from openai import OpenAI
import pymysql
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()  # .env 파일에서 환경 변수를 불러옵니다.
app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

    try:
        # DB에 record가 없으면, youtube_id로 youtube_to_mp3를 실행한다.    
        mp3_file_path = youtube_to_mp3(youtube_id)
    except pytube.exceptions.AgeRestrictedError:
        return {"summary": "채널 사용자의 보안 설정으로 인해 영상 정보를 불러올 수 없습니다."}
    
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
    
@app.get("/recommend")
def get_recipe_recommendation():
    # OpenWeatherMap API로 현재 날씨 정보 가져오기
    weather_response = requests.get(os.getenv("WEATHER_API_URL"))
    weather_json = json.loads(weather_response.text)

    # 현재 날씨 정보 출력
    current_time = weather_json['location']['localtime']  # 현재 시간
    current_temp = weather_json['current']['temp_c']  # 현재 온도
    current_condition = weather_json['current']['condition']['text']  # 현재 날씨

    # OpenAI API를 사용하여 요리 추천
    prompt = """
    현재 시간은 %s이고, 온도는 %s도, 날씨는 %s입니다. 상황에 맞는 음식을 추천해주세요. 중요도는 온도가 가장 높으며, 그 다음으로 날씨와 시간이 옵니다. 
    추천된 음식과 그에 대한 코멘트를 JSON 형식으로 반환해주세요. 예를 들어, 추천 음식이 '된장찌개'라면, 반환 형식은 다음과 같습니다:

    {
    "recommend": "된장찌개",
    "comment": "오늘은 날씨가 추워 '된장찌개'를 추천합니다."
    }
    """ % (current_time, current_temp, current_condition)

    # ChatGPT에게 요청
    completion = client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=300,  # 음식 추천 텍스트의 최대 길이
        temperature=0.7  # 응답의 다양성 조절
    )

    # 결과에서 JSON 형식의 음식 추천 가져오기
    try:
        recipe_recommendation = json.loads(completion.choices[0].text.strip())
    except json.JSONDecodeError:
        # JSON 파싱 에러 처리
        recipe_recommendation = "JSON 파싱 에러 발생"

    return recipe_recommendation
    
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)
