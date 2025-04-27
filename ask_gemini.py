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
    here = os.path.dirname(os.path.abspath(__file__))
    # 레포 루트가 scripts/ask_gemini.py 아래에 있다고 가정하면
    repo_root = os.path.abspath(os.path.join(here, os.pardir))
    print("Repo root is:", repo_root)