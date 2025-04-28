import threading, time, os
import google.generativeai as genai
import requests
import base64
import json

# 환경 변수에서 API 키 및 GitHub 토큰을 가져옵니다.
API_KEY = os.getenv("API_KEY")  # Google Gemini API 키
GITHUB_TOKEN = os.getenv("GIT_TOKEN")  # GitHub Personal Access Token
REPO_OWNER = "JUNBUNG-droid"
REPO_NAME = "ask_gemini"

# GitHub API URL
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/data"
headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# GitHub에서 data 폴더의 파일 목록을 가져오는 함수
def get_files_from_data_folder():
    response = requests.get(GITHUB_API_URL, headers=headers)

    if response.status_code == 200:
        file_list = response.json()
        print(file_list)
        return file_list  # data 폴더 내 파일 목록 반환
    else:
        raise Exception(f"Failed to fetch file list: {response.status_code}")

# GitHub에서 파일을 가져오는 함수
def get_file_content(file_path):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        file_data = response.json()
        file_content = file_data['content']
        decoded_content = base64.b64decode(file_content).decode('utf-8')
        return decoded_content
    else:
        raise Exception(f"Failed to fetch file: {response.status_code}")

# 각 파일에서 user_id 추출하는 함수
def extract_user_id_from_file(file_path):
    try:
        file_content = get_file_content(file_path)  # 파일 내용 가져오기
        data = json.loads(file_content)  # JSON 데이터로 파싱
        user_id = data.get("user_id")  # user_id 추출
        return user_id
    except Exception as e:
        print(f"파일 {file_path}에서 user_id를 추출하는 중 에러 발생: {e}")
        return None

# 여러 파일에서 user_id를 추출하는 함수
def extract_user_id_from_files():
    file_list = get_files_from_data_folder()
    user_ids = []

    for file in file_list:
        file_path = file['path']
        if file_path.endswith('.json'):  # JSON 파일만 처리
            user_id = extract_user_id_from_file(file_path)
            if user_id:
                user_ids.append(user_id)

    return user_ids

# Gemini API 호출 함수
def call_gemini(instruction: str):
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-pro-exp-03-25')
    full_text = ""
    
    # 시스템 프롬프트와 사용자 입력을 포함한 요청 페이로드 구성
    payload = {
        "contents": [
            {
                "parts": [{"text": "당신은 친절하고 정중한 한국어 비서입니다. 모든 답변을 공손하고 자연스럽게 해주세요."}]
            },
            {
                "parts": [{"text": instruction}]  # 사용자의 입력
            }
        ]
    }
    
    # 페이로드를 사용하여 API 호출
    for chunk in model.generate_content(payload, stream=True):
        if hasattr(chunk, 'text') and chunk.text:
            full_text += chunk.text
    
    return full_text

if __name__ == "__main__":
    try:
        # 1) data 폴더에서 모든 파일의 user_id 추출
        user_ids = extract_user_id_from_files()
        if not user_ids:
            print("user_id를 추출할 수 없습니다.")
            exit(1)
        
        # 2) 각 user_id마다 처리
        for uid in user_ids:
            print(f"\n=== 처리 시작: {uid} ===")

            # 2-1) 해당 유저의 summary JSON 가져오기
            summary_path = f"data/diet_summary_{uid}.json"
            try:
                summary_json = get_file_content(summary_path)
            except Exception as e:
                print(f"{uid} 요약 파일 로딩 실패: {e}")
                continue

            # 2-2) Gemini 프롬프트 생성
            prompt = f"내 정보는 {summary_json} 입니다. 이것을 기반으로 현 상태를 평가해주세요"

            # 2-3) Gemini API 호출
            try:
                answer = call_gemini(prompt)
                print(answer)
            except Exception as e:
                print(f"{uid} Gemini 호출 실패: {e}")
                continue

            # 2-4) 결과를 파일로 저장
            result_file = f"{uid}.txt"
            try:
                with open(result_file, "w", encoding="utf-8") as f:
                    f.write(answer)
                print(f"{uid} 피드백 저장 완료: {result_file}")
            except Exception as e:
                print(f"{uid} 파일 저장 실패: {e}")

            # (선택) 여기에 upload_to_github(result_file, f"feedback/{result_file}") 호출 가능

            # API Rate-limit 방지용 짧은 대기
            time.sleep(1)

    except Exception as e:
        print(f"전체 처리 중 에러 발생: {e}")
