# -*- coding: utf-8 -*-
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask
from tuya_iot import TuyaOpenAPI # 모듈 이름 tuya_iot 로 유지
from datetime import datetime
import pytz

app = Flask(__name__)

# --- 환경 변수 ---
ACCESS_ID = os.environ.get("TUYA_ACCESS_ID")
ACCESS_KEY = os.environ.get("TUYA_ACCESS_KEY")
API_ENDPOINT = os.environ.get("TUYA_API_ENDPOINT")
DEVICE_ID = os.environ.get("TUYA_DEVICE_ID")

GOOGLE_SHEET_NAME = os.environ.get("GOOGLE_SHEET_NAME")
GOOGLE_CREDENTIALS_JSON_STR = os.environ.get("GOOGLE_CREDENTIALS_JSON")

# (로그 기록 함수는 그대로 사용)
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
    except Exception as e:
        print(f"[로깅 실패] Google Sheets 기록 중 오류 발생: {e}")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def main_handler(path):
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
