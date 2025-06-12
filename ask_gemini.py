import threading, time, os
import google.generativeai as genai
import requests
import base64
import json
from datetime import datetime

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

# 식단 데이터의 날짜가 오늘인지 확인하는 함수
def is_today_data(summary_data):
    try:
        data = json.loads(summary_data)
        # JSON에서 날짜 정보 추출 (여러 가능한 키 확인)
        date_str = data.get("date") or data.get("날짜") or data.get("analysis_date")
        
        if not date_str:
            return False
            
        # 날짜 문자열을 datetime 객체로 변환
        if isinstance(date_str, str):
            # 다양한 날짜 형식 지원 (시간 포함 형식 추가)
            date_formats = [
                '%Y-%m-%d %H:%M:%S',  # 2025-05-11 23:10:54
                '%Y-%m-%d',           # 2025-05-11
                '%Y/%m/%d',           # 2025/05/11
                '%m/%d/%Y',           # 05/11/2025
                '%d/%m/%Y',           # 11/05/2025
                '%Y-%m-%d %H:%M',     # 2025-05-11 23:10
            ]
            
            file_date = None
            for fmt in date_formats:
                try:
                    file_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
                    
            if file_date is None:
                return False
        else:
            return False
            
        # 오늘 날짜와 비교
        today = datetime.now().date()
        return file_date == today
        
    except Exception as e:
        return False

# Gemini API 호출 함수
def call_gemini(instruction: str):
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')
    full_text = ""
    
    # 안전 설정 - 모든 필터 비활성화
    safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH", 
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE"
        }
    ]
    
    # 프롬프트 템플릿 설정
    template = """
    [날짜] 식단 분석 피드백
    
    1. 기본 정보
    성별: [남/여], 나이: [숫자]세, 키: [숫자]cm, 체중: [숫자]kg
    활동수준: [매우적음/적음/보통/많음/매우많음], 목표: [체중감량/유지/증가]
    
    2. 오늘의 식단 분석
    칼로리 섭취: [실제 섭취량]kcal / [권장량]kcal ([부족/초과] [수치]kcal)
    주요 음식: [음식1, 음식2, 음식3]
    음식별 특징: [각 음식군의 특징 간단히]
    문제점: [건강에 미치는 핵심 문제 1-2가지만 간단히]
    
    3. 개선 방안
    즉시 개선사항:
    - [가장 중요한 개선점 1개]
    - [두 번째 중요한 개선점 1개]

    추천 메뉴:
    - [부족한 영양소를 보충할 수 있는 간단한 요리 1-2가지]
    - [현재 섭취한 음식과 궁합이 좋은 대체/보완 음식 1-2가지]

    조리법 개선:
    - [현재 섭취한 음식의 더 건강한 조리 방법 1-2가지]
    - [나트륨, 당분, 지방 등을 줄이는 구체적인 팁]
    
    장기 목표:
    - [지속 가능한 식습관 1-2가지]

    4. 요약
   - [전체 분석 결과를 간략하게 정리]
    
    *** 요청사항
    - 각 섹션당 3-4줄 이내로 간결하게 작성
    - 전문용어 최소화, 실용적인 조언 위주
    - 숫자는 명확히 제시하되 설명은 간단히
    - 모바일에서 읽기 쉽도록 짧은 문단으로 구성
    - 기호는 - 와 : 만 
    - 반드시 프롬프트의 형식대로 작성
    - 추천 메뉴/레시피는 간단하게 만들 수 있고 실용적인 것으로 제안
    - 대체음식은 현재 섭취 음식의 문제점을 보완할 수 있는 것으로 추천
    - 조리법 개선은 현재 먹은 음식을 더 건강하게 만드는 구체적인 방법 제시
    - 나트륨, 당분, 지방 줄이는 팁은 실제 적용 가능한 것으로 추천
    - 오늘 날짜의 음식 정보가 아닐시 "오늘 음식 정보가 없어 분석을 건너뜁니다"라고 안내
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
    
    # 페이로드를 사용하여 API 호출 (안전 설정 포함)
    try:
        for chunk in model.generate_content(contents, stream=True, safety_settings=safety_settings):
            if hasattr(chunk, 'text') and chunk.text:
                full_text += chunk.text
        return full_text
    except Exception as e:
        return f"API 호출 오류: {str(e)}"

if __name__ == "__main__":
    try:
        # 오늘 날짜 출력
        today = datetime.now().strftime('%Y-%m-%d')
        print(f"오늘 날짜: {today}")
        print("="*50)
        
        # 1) data 폴더에서 모든 파일의 user_id 추출  
        user_ids = extract_user_id_from_files()
        print(f"추출된 user_id 목록: {user_ids}")
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

            # 2-2) 날짜 확인 및 프롬프트 생성
            is_today = is_today_data(summary_json)
            
            if is_today:
                prompt = f"내 정보는 {summary_json} 입니다. 이것을 기반으로 현 상태를 평가해주세요"
                print(f"{uid}: 오늘 데이터 확인됨. 분석 진행...")
            else:
                prompt = f"내 정보는 {summary_json} 입니다. 단, 이 데이터는 오늘 날짜가 아닙니다. 오늘 음식 정보가 없어 분석을 건너뜁니다."
                print(f"{uid}: 오늘 데이터가 아님. 안내 메시지 생성...")

            # 2-3) Gemini API 호출
            try:
                answer = call_gemini(prompt)
                print(answer)
            except Exception as e:
                print(f"{uid} Gemini 호출 실패: {e}")
                continue

            # 2-4) 결과를 파일로 저장 (날짜 포함)
            today = datetime.now().strftime('%Y-%m-%d')
            result_file = f"feedback_{today}_{uid}.txt"
            try:
                # feedback 폴더가 없으면 생성
                if not os.path.exists('feedback'):
                    os.makedirs('feedback')
                    
                with open(f"feedback/{result_file}", "w", encoding="utf-8") as f:
                    f.write(answer)
                print(f"{uid} 피드백 저장 완료: {result_file}")
            except Exception as e:
                print(f"{uid} 파일 저장 실패: {e}")

            # API Rate-limit 방지용 짧은 대기
            time.sleep(1)

        print(f"\n{'='*50}")
        print("=== 전체 처리 완료 ===")

    except Exception as e:
        print(f"전체 처리 중 에러 발생: {e}")
