"""
아마노파크 발렛 주차 예약 가능여부 자동 체크 & ntfy 알림 스크립트

Google Sheets의 각 행(날짜/체크주기)을 읽어서,
설정한 주기가 지난 행만 실제로 예약 가능여부 API를 호출합니다.
자리가 있으면 ntfy로 알림을 보내고 상태를 '완료'로 변경합니다.

시트 컬럼 구성 (1행은 헤더):
  A: 날짜 (YYYY-MM-DD)
  B: 체크주기(분)
  C: 상태 (비어있으면 대기 / 완료 / 만료)
  D: 마지막체크시각 (자동 기록, ISO 8601)
  E: 메모 (자유롭게 사용, 로직에서는 사용 안 함)
"""

import os
import json
import time
import random
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import gspread
from google.oauth2.service_account import Credentials

# ---------- 설정 ----------
API_CHECK_URL = "https://api.amanopark.co.kr/api/web/setting/booking/check"
BOOKING_URL = "https://valet.amanopark.co.kr/booking"
KST = ZoneInfo("Asia/Seoul")

SHEET_ID = os.environ["SHEET_ID"]
SHEET_NAME = os.environ.get("SHEET_NAME", "Requests")
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
GOOGLE_CREDS_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]

HEADERS = ["날짜", "체크주기(분)", "상태", "마지막체크시각", "메모"]
COL_DATE, COL_INTERVAL, COL_STATUS, COL_LAST_CHECK, COL_MEMO = range(1, 6)

STATUS_DONE = "완료"
STATUS_EXPIRED = "만료"

DEFAULT_INTERVAL_MIN = 5  # 체크주기 미입력 시 기본값


def get_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_info = json.loads(GOOGLE_CREDS_JSON)
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)


def check_availability(date_text: str) -> bool:
    resp = requests.get(
        API_CHECK_URL,
        params={"date": date_text, "type": "BASIC"},
        timeout=10,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            )
        },
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("data") is True


def send_notification(date_text: str):
    message = f"{date_text} 주차 예약 가능! 지금 바로 예약하세요.\n{BOOKING_URL}"
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        params={"title": "주차 자리 발견", "priority": "high", "tags": "car,rotating_light"},
        data=message.encode("utf-8"),
        timeout=10,
    )


def parse_dt(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def now_kst() -> datetime:
    return datetime.now(KST)


def main():
    sheet = get_sheet()
    rows = sheet.get_all_values()

    if not rows:
        print("시트가 비어 있습니다. 헤더 행을 먼저 입력해 주세요.")
        return

    if rows[0][:5] != HEADERS:
        print(f"[경고] 헤더가 예상과 다릅니다: {rows[0]}")

    now = now_kst()
    today_text = now.strftime("%Y-%m-%d")

    updates = []  # (row_index, col_index, value)
    checked_count = 0

    for i, row in enumerate(rows[1:], start=2):  # 시트 2행부터 (1행은 헤더)
        row = row + [""] * (5 - len(row))
        date_text, interval_text, status, last_check_text, _memo = row[:5]
        date_text = date_text.strip()

        if not date_text:
            continue
        if status in (STATUS_DONE, STATUS_EXPIRED):
            continue
        if date_text < today_text:
            updates.append((i, COL_STATUS, STATUS_EXPIRED))
            continue

        try:
            interval_min = float(interval_text) if interval_text else DEFAULT_INTERVAL_MIN
        except ValueError:
            interval_min = DEFAULT_INTERVAL_MIN

        last_check = parse_dt(last_check_text)
        if last_check and (now - last_check).total_seconds() < interval_min * 60:
            continue  # 아직 다시 체크할 시점이 아님

        try:
            available = check_availability(date_text)
        except Exception as e:
            print(f"[오류] {date_text} 체크 실패: {e}")
            continue

        checked_count += 1
        updates.append((i, COL_LAST_CHECK, now.isoformat(timespec="seconds")))

        if available:
            print(f"[발견] {date_text} 예약 가능! 알림 전송")
            send_notification(date_text)
            updates.append((i, COL_STATUS, STATUS_DONE))
        else:
            print(f"[확인] {date_text} 아직 자리 없음")

        time.sleep(random.uniform(0.5, 1.5))  # 연속 호출 과도 방지

    for row_i, col_i, value in updates:
        sheet.update_cell(row_i, col_i, value)

    print(f"실행 완료 — 이번 회차 실제 API 체크: {checked_count}건 / 시트 업데이트: {len(updates)}건")


if __name__ == "__main__":
    main()
