# -*- coding: utf-8 -*-
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
from tuya_iot import TuyaOpenAPI
from datetime import datetime
import pytz

app = Flask(__name__)

# --- 이 정보들은 Vercel에 '환경 변수'로 안전하게 저장할 예정입니다. ---
ACCESS_ID = os.environ.get("TUYA_ACCESS_ID")
ACCESS_KEY = os.environ.get("TUYA_ACCESS_KEY")
API_ENDPOINT = os.environ.get("TUYA_API_ENDPOINT")
DEVICE_ID = os.environ.get("TUYA_DEVICE_ID")

# Google Sheets 관련 정보도 환경 변수에서 가져옵니다.
GOOGLE_SHEET_NAME = os.environ.get("GOOGLE_SHEET_NAME")
GOOGLE_CREDENTIALS_JSON_STR = os.environ.get("GOOGLE_CREDENTIALS_JSON")

def log_to_sheet(result, details):
    """Google Sheets에 로그를 기록하는 함수"""
    try:
        if not all([GOOGLE_SHEET_NAME, GOOGLE_CREDENTIALS_JSON_STR]):
            print("[로깅 오류] Google Sheets 관련 환경 변수가 설정되지 않았습니다.")
            return

        creds_json = json.loads(GOOGLE_CREDENTIALS_JSON_STR)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1
        
        # 한국 시간(KST)으로 타임스탬프 기록
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
    """링크가 클릭되면 실행되는 메인 함수"""
    if not all([ACCESS_ID, ACCESS_KEY, API_ENDPOINT, DEVICE_ID]):
        msg = "서버 설정 오류: Tuya API 정보가 설정되지 않았습니다."
        log_to_sheet("서버 오류", msg)
        return f"<h1>오류</h1><p>{msg}</p>", 500

    try:
        openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_KEY)
        response = openapi.connect()
        
        if not response.get('success', False):
            msg = f"클라우드 연결 실패: {response}"
            log_to_sheet("실패", msg)
            return f"<h1>클라우드 연결 실패</h1><p>에러: {response}</p>"

        # '켜기(ON)' 명령입니다. 만약 '클릭' 방식으로 바꾸고 싶다면 아래 부분을 수정하세요.
        # command = {'commands': [{'code': 'mode', 'value': 'click'}]}
        command = {'commands': [{'code': 'switch', 'value': True}]}

        api_path = f"/v1.0/iot-03/devices/{DEVICE_ID}/commands"
        response = openapi.post(api_path, command)
        
        if response.get('success', False):
            msg = f"기기(ID: {DEVICE_ID})에 '켜기' 명령 전송"
            log_to_sheet("성공", msg)
            return f"<h1>요청 성공</h1><p>{msg}</p>"
        else:
            msg = f"명령 전송 실패: {response}"
            log_to_sheet("실패", msg)
            return f"<h1>명령 전송 실패</h1><p>에러: {response}</p>"
    except Exception as e:
        msg = f"치명적 오류 발생: {e}"
        log_to_sheet("치명적 오류", msg)
        return f"<h1>치명적 오류 발생</h1><p>오류 내용: {e}</p>"
