import pytube
import os
import os.path
from moviepy.editor import AudioFileClip
from openai import OpenAI

client = OpenAI()

def youtube_to_mp3(youtube_id):
    link = "https://www.youtube.com/watch?v=" + youtube_id
    yt = pytube.YouTube(link)

    path = os.getcwd()  # Get the current working directory (cwd)
    file_name = youtube_id
    path = os.getcwd()
    full_path = str(path + "/file/" + str(file_name))

    mp4_file = full_path + '.mp4'
    mp3_file = full_path + '.mp3'

    if os.path.exists(mp3_file):
        print("mp3 파일이 이미 존재합니다.")
        return mp3_file
    
    yt.streams.filter(only_audio=True).first().download(path, mp4_file)

    try:
        os.rename(mp4_file, mp3_file)

        # Check and trim audio length
        audio_clip = AudioFileClip(mp3_file)
        if audio_clip.duration > 1800:  # 1800 seconds = 30 minutes
            trimmed_audio = audio_clip.subclip(0, 1800)  # Trim to first 30 minutes
            trimmed_audio.write_audiofile(mp3_file, codec='libmp3lame')
            print("mp3 파일 길이 줄였음")

        return mp3_file

    except Exception as e:
        print(f"mp3 변환 실패: {e}")
        return None

def mp3_to_text(mp3_file_path):
    try:
        with open(mp3_file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file, 
                response_format="text"
            )
        # Check if the transcript is longer than 4000 characters
        if len(transcript) > 4000:
            transcript = transcript[:4000]  # Trim the transcript to 4000 characters
            print("텍스트 길이 줄였음")

        print("텍스트 변환 완료: " + transcript)
        return transcript

    except Exception as e:
        print(f"텍스트 변환 실패: {e}")
        return None

def summarize_text(text_to_summarize, client):
    try:
        prompt_message = read_message_from_file("prompt_engineering.txt")

        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt_message},
                {"role": "user", "content": text_to_summarize}
            ]
        )
        summary = response.choices[0].message.content
        print("텍스트 요약 성공:", summary)
        return summary
    
    except Exception as e:
        print(f"텍스트 요약 오류 발생: {e}")
        return None
    
def read_message_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read().strip()