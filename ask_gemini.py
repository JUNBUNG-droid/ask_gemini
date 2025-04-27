# ask_gemini.py

import threading, time, os
import google.generativeai as genai

API_KEY = os.getenv("API_KEY")  # GitHub Secrets 에 등록된 값

def call_gemini(prompt: str):
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
    full_text = ""

    for chunk in model.generate_content(prompt, stream=True):
        if hasattr(chunk, 'text') and chunk.text:
            full_text += chunk.text

    return full_text

if __name__ == "__main__":
    # (여기에 원하는 질문을 하드코딩하거나, 파일·환경변수에서 읽어오세요)
    prompt = "오늘 서울 날씨 어때?"
    answer = call_gemini(prompt)
    print(answer)
