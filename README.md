# 주차 예약 자동 알림 (Parking Alert) 

날짜 + 체크주기를 Google Sheets에 등록해두면, GitHub Actions가 주기적으로
아마노파크 예약 가능여부 API를 호출해서 자리가 나면 ntfy로 폰에 알림을 보내줍니다.

비용: Google Sheets API, GitHub Actions(public 저장소), ntfy.sh 모두 개인 사용
수준에서는 무료입니다. 신용카드 등록 없이 진행 가능합니다.

---

## 1단계. Google Cloud 서비스 계정 만들기

1. https://console.cloud.google.com 접속 → 구글 계정으로 로그인
   (처음 방문 시 "무료 체험 활성화" 배너가 뜨면 무시하고 건너뛰어도 됩니다 — 이번 작업엔 필요 없음)
2. 상단 바 "프로젝트 선택" 클릭 → 팝업에서 "새 프로젝트" 클릭
3. 프로젝트 이름 입력 (예: parking-alert) → "만들기" 클릭 (생성까지 몇 초 소요)
4. 상단 바에서 방금 만든 프로젝트가 선택돼 있는지 확인
5. 왼쪽 ☰ 메뉴 → "API 및 서비스" → "라이브러리"
6. 검색창에 "Google Sheets API" 입력 → 결과 클릭 → "사용" 버튼 클릭
7. 왼쪽 메뉴 "API 및 서비스" → "사용자 인증 정보"
8. 상단 "+ 사용자 인증 정보 만들기" → "서비스 계정" 선택
9. 서비스 계정 이름 입력 (예: parking-alert-bot) → "만들고 계속하기" → 역할 선택은 건너뛰고 "계속" → "완료"
10. 생성된 서비스 계정 클릭 → 상단 "키" 탭 → "키 추가" → "새 키 만들기" → "JSON" 선택 → "만들기"
11. JSON 파일이 자동 다운로드됨 (예: parking-alert-xxxxx.json) — 잘 보관
12. 다운로드한 JSON을 메모장으로 열어 `"client_email"` 값을 복사해두기
    (예: parking-alert-bot@parking-alert-123456.iam.gserviceaccount.com)

## 2단계. Google Sheet 준비

1. https://sheets.google.com → "+"로 새 스프레드시트 생성
2. 하단 시트 탭 더블클릭 → 이름을 "Requests"로 변경
3. A1~E1에 순서대로 입력: 날짜, 체크주기(분), 상태, 마지막체크시각, 메모
4. 우측 상단 "공유" 클릭
5. 1단계 12번에서 복사한 client_email 주소 붙여넣기 → 권한 "편집자" → "보내기"
   (알림 이메일 전송 체크는 꺼도 무방)
6. 주소창 URL에서 SHEET_ID 복사
   `https://docs.google.com/spreadsheets/d/`**여기 부분**`/edit`

## 3단계. ntfy 알림 설정

1. 스마트폰 앱스토어(iOS) / 플레이스토어(Android)에서 "ntfy" 검색 후 설치
2. 앱 실행 → "+"로 새 구독 추가
3. 토픽 이름을 추측하기 어려운 문자열로 입력 (예: jerry-parking-9f3ka2) → "구독"
4. 이 토픽 이름 메모해두기 (4단계에서 사용)
5. (선택) 브라우저로 `https://ntfy.sh/내토픽이름` 접속해 테스트 메시지를 보내보면
   폰에 알림이 뜨는지 바로 확인 가능

## 4단계. GitHub 저장소 설정

1. https://github.com → 우측 상단 "+" → "New repository"
2. 저장소 이름 입력 (예: parking-alert) → Visibility "Public" 선택 → "Create repository"
3. 아래 4개 파일을 저장소에 업로드 (폴더 구조 그대로 유지):
   - `check_parking.py`
   - `requirements.txt`
   - `.github/workflows/check-parking.yml`
   - `README.md`
   웹 UI에서 폴더 구조를 유지하려면 "Add file" → "Create new file"에서
   파일명 칸에 `.github/workflows/check-parking.yml`처럼 전체 경로를 입력하면
   폴더가 자동 생성됩니다.
4. 저장소 메뉴 "Settings" → 좌측 "Secrets and variables" → "Actions"
5. "New repository secret"을 3번 눌러 각각 등록:
   - `SHEET_ID` = 2단계 6번에서 복사한 값
   - `NTFY_TOPIC` = 3단계 3번 토픽 이름
   - `GOOGLE_SERVICE_ACCOUNT_JSON` = 1단계 11번 JSON 파일을 메모장으로 열어 전체 내용 복사+붙여넣기

## 5단계. 테스트

1. 저장소 상단 "Actions" 탭 클릭
2. 좌측 "Parking Availability Check" 워크플로 클릭
3. 우측 "Run workflow" → 다시 "Run workflow" 확인 클릭 (수동 실행)
4. 몇 초 후 생성된 실행 항목 클릭 → "check" 잡 클릭 → 로그에 오류 없는지 확인
5. Google Sheet로 돌아가서 감시할 날짜를 넣어둔 행의 "마지막체크시각" 칸이
   채워졌는지 확인

## 6단계. 실사용

1. 감시하고 싶은 날짜가 생기면 시트에 새 행 추가: A열 날짜(YYYY-MM-DD),
   B열 체크주기(분)만 입력, 나머지 칸은 비워두면 됨
2. 5분마다 자동 실행되며, 자리가 생기면 폰에 ntfy 알림 도착 + 상태가
   "완료"로 자동 변경
3. 알림 메시지 안의 링크를 눌러 실제 예약 페이지에서 예약 진행

## 참고 / 유의사항

- Google Sheets API, GitHub Actions(public 저장소), ntfy.sh 모두 이 사용 규모에서는
  무료입니다. 신용카드 등록이 필요 없습니다.
- GitHub Actions의 cron은 5분 단위가 실질적인 한계이며, 서버 부하 시 예약된 시각보다
  몇 분 늦게 실행될 수 있습니다. "10분마다"는 "10분 내외"로 이해하는 것이 정확합니다.
- 자리 발견 후에도 예약은 자동으로 진행되지 않습니다 (알림의 링크를 눌러 직접 진행).
- API를 너무 잦은 주기로 호출하면 사이트 측에서 접근을 차단할 수 있으니, 체크주기를
  5분 미만으로 설정하는 것은 권장하지 않습니다.
- 배포 전에 `check_parking.py`가 호출하는 API가 별도 인증 없이 정상 응답하는지
  브라우저나 curl로 한 번 직접 확인해보는 것을 권장합니다.
