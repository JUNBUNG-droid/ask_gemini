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
    model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
    full_text = ""
    
    # 프롬프트 템플릿 설정
    template = """
    (해당 날짜) 식단 데이터 분석 및 피드백
        ex) 4월 7일 식단 데이터 분석 및 피드백
    
    1. 개인 정보
    - 성별: [남/여]
    - 나이: [숫자]세
    - 신체 정보:
      * 키: [숫자]cm
      * 체중: [숫자]kg
      * 허리둘레: [숫자]cm
    - 활동 수준: [매우 적음/적음/보통/많음/매우 많음] 
    - 건강 목표: [체중 감량/체중 유지/체중 증가]
    
    2. 식단 기록 분석
   - 날짜에 해당하는 식단 칼로리 섭취량과 TDEE 대비 초과/부족 여부  
   - 자주 섭취하는 음식 목록과 각 음식의 혈당 부하 지수(GL) 분류  
   - 각 음식군의 특징과 건강에 미치는 영향 (예: 고혈당 부하 음식, 가공식품의 특성, 채소 섭취 여부)

    3. 종합 피드백 및 권장 사항
   - 현재 식단의 전반적인 경향과 문제점 요약  
   - 위험성 인지 및 목표 설정 (체중 감량, 혈당 관리 등)  
   - 단계별 권장 사항: 식단 조절, 고혈당 부하 음식 제한, 채소 섭취 증가, 규칙적인 식사 습관, 신체 활동 증가, 수분 섭취, 정기적인 전문가 상담 등

    4. 요약
   - 전체 분석 결과를 간략하게 정리하고, 시급한 개선 사항 및 장기적인 건강 관리 방안을 제시
    
    *** 요청 사항
    각 섹션은 제목과 소제목을 명확히 하여, 내 정보와 식단을 기반으로 읽는 사람이 쉽게 이해할 수 있도록 구성해 주세요. 숫자 및 계산 과정, 데이터 기반 결론을 명확히 제시해 주시고, 전문적이고 체계적인 언어로 작성해 주세요.
    반드시 프롬프트의 형식대로 작성할 것. 프롬프트에 나와있는 기호를 제외한 나머지 # * - 같은 기호는 쓰지말 것. 가독성 좋게 작성.
    """
    
    # 요청 페이로드 구성
    contents = [
        {
            "role": "user",
            "parts": [{"text": template}]
        },
        {
            "role": "user",
            "parts": [{"text": instruction}]
        }
    ]
    
    # 페이로드를 사용하여 API 호출
    try:
        for chunk in model.generate_content(contents, stream=True):
            if hasattr(chunk, 'text') and chunk.text:
                full_text += chunk.text
        return full_text
    except Exception as e:
        return f"API 호출 오류: {str(e)}"

if __name__ == "__main__":
    try:
        # 1) data 폴더에서 모든 파일의 user_id 추출
        user_ids = extract_user_id_from_files()
        print(user_ids)
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
