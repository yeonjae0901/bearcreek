# 베어크리크 골프장 예약 알리미

베어크리크 춘천 골프장의 예약 가능한 날짜를 자동으로 확인하고 텔레그램으로 알려주는 프로그램입니다.

## 기능

- 설정한 월(기본값: 5월)의 예약 가능한 날짜를 자동으로 확인
- 예약 가능한 날짜가 있으면 텔레그램으로 알림
- 정기적인 스케줄링을 통해 자동으로 반복 확인 (기본값: 5분 간격)

## 설치 방법

1. Python 3.8 이상이 필요합니다.

2. 필요한 패키지 설치:
   ```bash
   pip install -r requirements.txt
   ```

3. Chrome 브라우저가 설치되어 있어야 합니다.

4. 환경 변수 설정:
   `.env.example` 파일을 `.env`로 복사하고 필요한 정보를 입력합니다.
   ```bash
   cp .env.example .env
   ```

## 환경 변수 설정

`.env` 파일에 다음 정보를 설정해야 합니다:

- `TELEGRAM_BOT_TOKEN`: 텔레그램 봇 토큰
- `TELEGRAM_CHAT_ID`: 텔레그램 채팅 ID
- `MONTH`: 확인할 월 (기본값: 5)
- `YEAR`: 확인할 연도 (기본값: 2025)
- `CHECK_INTERVAL_MINUTES`: 확인 주기 (분 단위, 기본값: 5)

### 텔레그램 봇 설정 방법

1. 텔레그램에서 BotFather(@BotFather)를 검색합니다.
2. `/newbot` 명령을 실행하고 지시에 따라 봇 이름과 사용자 이름을 설정합니다.
3. 생성이 완료되면 봇 토큰을 받게 됩니다. 이 토큰을 `.env` 파일의 `TELEGRAM_BOT_TOKEN`에 입력합니다.
4. 생성한 봇에게 메시지를 보낸 후, 브라우저에서 `https://api.telegram.org/bot<봇_토큰>/getUpdates`에 접속합니다.
5. 응답에서 `chat_id` 값을 확인하고 `.env` 파일의 `TELEGRAM_CHAT_ID`에 입력합니다.

## 실행 방법

```bash
python bearcreek_checker.py
```

## 백그라운드 실행 (리눅스/MacOS)

```bash
nohup python bearcreek_checker.py > bearcreek.log 2>&1 &
```

## 주의사항

- 이 프로그램은 베어크리크 골프장의 웹사이트 구조 변경에 따라 작동하지 않을 수 있습니다.
- 웹사이트의 과도한 접속은 차단될 수 있으니 CHECK_INTERVAL_MINUTES 값을 적절히 설정하세요.
