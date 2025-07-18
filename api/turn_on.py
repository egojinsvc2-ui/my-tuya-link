# -*- coding: utf-8 -*-
import os
import json
import tinytuya
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
from datetime import datetime
import pytz

app = Flask(__name__)

# --- 환경 변수 ---
ACCESS_ID = os.environ.get("TUYA_ACCESS_ID")
ACCESS_KEY = os.environ.get("TUYA_ACCESS_KEY")
REGION = os.environ.get("TUYA_REGION", "us") 
DEVICE_ID = os.environ.get("TUYA_DEVICE_ID")

GOOGLE_SHEET_NAME = os.environ.get("GOOGLE_SHEET_NAME")
GOOGLE_CREDENTIALS_JSON_STR = os.environ.get("GOOGLE_CREDENTIALS_JSON")

def log_to_sheet(result, details):
    try:
        if not all([GOOGLE_SHEET_NAME, GOOGLE_CREDENTIALS_JSON_STR]):
            print("[로깅 오류] Google Sheets 환경 변수가 설정되지 않았습니다.")
            return

        creds_json = json.loads(GOOGLE_CREDENTIALS_JSON_STR)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1
        kst = pytz.timezone('Asia/Seoul')
        timestamp = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
        row = [timestamp, result, str(details)]
        sheet.append_row(row)
        print(f"[로깅 성공] '{result}' 이력을 Google Sheets에 기록했습니다.")
    except Exception as e:
        print(f"[로깅 실패] Google Sheets 기록 중 오류 발생: {e}")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def main_handler(path):
    if not all([ACCESS_ID, ACCESS_KEY, DEVICE_ID]):
        msg = "서버 설정 오류: Tuya API 정보가 설정되지 않았습니다."
        log_to_sheet("서버 오류", msg)
        return f"<h1>오류</h1><p>{msg}</p>", 500

    try:
        # 1. TinyTuya 클라우드 객체 생성
        cloud = tinytuya.Cloud(
            apiRegion=REGION, 
            apiKey=ACCESS_ID, 
            apiSecret=ACCESS_KEY
        )
        
        # 2. '켜기' 명령 준비
        commands = {
            'commands': [
                # 기기에 맞는 표준 명령어를 사용해 보세요.
                # 'switch_led' 또는 'switch' 또는 'switch_1' 등
                {'code': 'switch', 'value': True}
            ]
        }
        
        # 3. 명령 전송 (최신 함수 이름: device_control)
        result = cloud.device_control(DEVICE_ID, action="command", payload=commands)

        # 4. 결과 확인
        # tinytuya는 성공 시에도 응답이 비어있을 수 있고, 실패 시 'Error' 키를 포함할 수 있음
        if result and result.get('Error'):
            # 명백한 실패
            msg = f"명령 전송 실패: {result}"
            log_to_sheet("실패", msg)
            return f"<h1>명령 전송 실패</h1><p>에러: {result}</p>"
        else:
            # 성공 (또는 응답 없음 - 이것도 보통 성공임)
            msg = f"기기(ID: {DEVICE_ID})에 '켜기' 명령을 보냈습니다."
            log_to_sheet("성공", result if result else "응답 없음 (성공 간주)")
            return f"<h1>요청 성공</h1><p>{msg}</p><p>Tuya 응답: {result}</p>"

    except Exception as e:
        msg = f"치명적 오류 발생: {e}"
        log_to_sheet("치명적 오류", msg)
        return f"<h1>치명적 오류 발생</h1><p>오류 내용: {e}</p>"
