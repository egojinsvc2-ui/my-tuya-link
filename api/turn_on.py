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
# tinytuya는 API_ENDPOINT 대신 REGION을 사용합니다.
# REGION 값: 'us' (미국), 'eu' (유럽), 'in' (인도), 'cn' (중국)
REGION = os.environ.get("TUYA_REGION", "us") # 기본값 미국
DEVICE_ID = os.environ.get("TUYA_DEVICE_ID")

GOOGLE_SHEET_NAME = os.environ.get("GOOGLE_SHEET_NAME")
GOOGLE_CREDENTIALS_JSON_STR = os.environ.get("GOOGLE_CREDENTIALS_JSON")

def log_to_sheet(result, details):
    try:
        # (로그 기록 함수는 이전과 동일)
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
        
        # 2. '켜기' 명령 전송
        # 'switch_led'는 보통의 스위치, 'switch'도 가능합니다.
        # 기기에 따라 'switch_1', 'switch_2' 등일 수 있습니다.
        # 가장 확실한 것은 'turn_on' 입니다.
        commands = {
            'commands': [
                {'code': 'switch_led', 'value': True}, 
                {'code': 'switch', 'value': True}
            ]
        }
        
        # TinyTuya는 이 함수 하나로 명령을 보냅니다.
        result = cloud.send_device_commands(DEVICE_ID, commands['commands'])

        if result.get('success', False):
            msg = f"기기(ID: {DEVICE_ID})에 '켜기' 명령 전송"
            log_to_sheet("성공", result)
            return f"<h1>요청 성공</h1><p>{msg}</p><p>응답: {result}</p>"
        else:
            msg = f"명령 전송 실패: {result}"
            log_to_sheet("실패", msg)
            return f"<h1>명령 전송 실패</h1><p>에러: {result}</p>"

    except Exception as e:
        msg = f"치명적 오류 발생: {e}"
        log_to_sheet("치명적 오류", msg)
        return f"<h1>치명적 오류 발생</h1><p>오류 내용: {e}</p>"
