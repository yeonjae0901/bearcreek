# 베어크리크 골프장 예약 알리미

베어크리크 춘천 골프장의 예약 가능한 날짜를 자동으로 확인하고 텔레그램으로 알려주는 프로그램입니다.

## 프로젝트 소개

이 프로젝트는 베어크리크 골프장의 예약 시스템을 자동으로 모니터링하여 새로운 예약 가능 날짜가 있을 때 텔레그램으로 즉시 알림을 보내는 자동화 도구입니다. 특히 인기 있는 예약 날짜를 놓치지 않도록 도와줍니다.

### 작동 방식

1. Selenium 웹드라이버를 사용하여 베어크리크 골프장 예약 페이지에 접속합니다.
2. 설정한 월(기본값: 5월)의 예약 가능한 날짜를 자동으로 스캔합니다.
3. 예약 가능한 날짜가 발견되면 텔레그램 봇을 통해 알림 메시지를 보냅니다.
4. 설정된 시간 간격으로 위 과정을 반복합니다.

## 기능

- 설정한 월(기본값: 5월)의 예약 가능한 날짜를 자동으로 확인
- 예약 가능한 날짜가 있으면 텔레그램으로 알림
- 정기적인 스케줄링을 통해 자동으로 반복 확인 (기본값: 5분 간격)
- 디버깅을 위한 스크린샷 및 로그 기능

## 설치 방법

1. 이 저장소를 클론합니다:
   ```bash
   git clone https://github.com/yeonjae0901/bearcreek.git
   cd bearcreek
   ```

2. Python 3.8 이상이 필요합니다.

3. 필요한 패키지 설치:
   ```bash
   pip install -r requirements.txt
   ```

4. Chrome 브라우저가 설치되어 있어야 합니다.

5. 환경 변수 설정:
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

### 단일 실행 모드

한 번만 실행하고 종료하려면:

```bash
python bearcreek_checker.py --single
```

### 백그라운드 실행 (리눅스/MacOS)

서버에서 백그라운드로 실행:

```bash
nohup python bearcreek_checker.py > bearcreek.log 2>&1 &
```

## EC2 서버 설정

AWS EC2와 같은 클라우드 서버에서 실행하려면:

1. Chromium 설치:
   ```bash
   sudo apt-get update
   sudo apt-get install -y chromium-browser
   ```

2. 필요한 Python 패키지 설치:
   ```bash
   pip install -r requirements.txt
   ```

3. 백그라운드에서 실행:
   ```bash
   nohup python bearcreek_checker.py > bearcreek.log 2>&1 &
   ```

## 주의사항

- 이 프로그램은 베어크리크 골프장의 웹사이트 구조 변경에 따라 작동하지 않을 수 있습니다.
- 웹사이트의 과도한 접속은 차단될 수 있으니 CHECK_INTERVAL_MINUTES 값을 적절히 설정하세요.
- 개인적인 용도로만 사용하세요.

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
