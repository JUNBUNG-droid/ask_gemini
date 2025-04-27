import threading, time, os
import google.generativeai as genai
import requests
import base64

# 환경 변수에서 API 키 및 GitHub 토큰을 가져옵니다.
API_KEY = os.getenv("API_KEY")  # Google Gemini API 키
GITHUB_TOKEN = os.getenv("GIT_TOKEN")  # GitHub Personal Access Token
REPO_OWNER = "JUNBUNG-droid"
REPO_NAME = "ask_gemini"
FILE_PATH = "data/diet_summary.json"

# GitHub에서 파일을 가져오는 함수
def get_github_file():
    # GitHub API URL 생성
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # GitHub API로 받은 JSON 데이터를 디코딩
        file_data = response.json()
        file_content = file_data['content']
        decoded_content = base64.b64decode(file_content).decode('utf-8')
        return decoded_content
    else:
        raise Exception(f"Failed to fetch file: {response.status_code}")

# Gemini API 호출 함수
def call_gemini(prompt: str):
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
    full_text = ""

    # Gemini API를 스트리밍 방식으로 호출
    for chunk in model.generate_content(prompt, stream=True):
        if hasattr(chunk, 'text') and chunk.text:
            full_text += chunk.text

    return full_text

if __name__ == "__main__":
    # GitHub에서 데이터를 읽어옴
    try:
        github_data = get_github_file()

        # 데이터를 프롬프트에 삽입
        prompt = f"내 정보는 {github_data} 입니다. 이것을 기반으로 현 상태를 평가해주세요"

        # Gemini API 호출
        answer = call_gemini(prompt)

        # 결과를 파일로 저장
        with open("result.txt", "w", encoding="utf-8") as f:
            f.write(answer)

        print("결과가 'result.txt' 파일에 저장되었습니다.")
    except Exception as e:
        print(f"에러 발생: {e}")
