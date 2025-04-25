#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import datetime
import logging
import schedule
import asyncio
import random
import sys
import pytz
import requests
from bs4 import BeautifulSoup
import json
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("effective_checker.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

# 설정 정보
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', 5).replace('%', ''))

# 베어크리크 골프장 예약 페이지 URL
BEARCREEK_URL = "https://www.bearcreek.co.kr/Reservation/Reservation.aspx?strLGubun=110&strClubCode=N#aCourseSel"
BEARCREEK_AJAX_URL = "https://www.bearcreek.co.kr/Reservation/XmlCalendarData.aspx"

# 다양한 User-Agent 목록
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (iPad; CPU OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

# 프록시 목록 (필요시 추가)
PROXIES = [
    None,  # 프록시 없음
]

async def send_telegram_message(message):
    """텔레그램 메시지 발송 함수"""
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        logger.error("텔레그램 설정이 완료되지 않았습니다. .env 파일을 확인하세요.")
        return False
    
    try:
        logger.info(f"텔레그램 봇 토큰 유효성 검사 중... (길이: {len(TELEGRAM_BOT_TOKEN)})")
        logger.info(f"텔레그램 채팅 ID 유효성 검사 중... (값: {TELEGRAM_CHAT_ID})")
        
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        logger.info("텔레그램 봇 객체 생성 완료")
        
        # 채팅 ID 처리
        chat_id = TELEGRAM_CHAT_ID
        if isinstance(chat_id, str):
            if chat_id.startswith('-') and chat_id[1:].isdigit():
                chat_id = int(chat_id)
            elif chat_id.isdigit():
                chat_id = int(chat_id)
        
        response = await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
        logger.info(f"텔레그램 메시지가 성공적으로 전송되었습니다. 메시지 ID: {response.message_id}")
        return True
    except TelegramError as e:
        logger.error(f"텔레그램 메시지 전송 중 오류가 발생했습니다: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"텔레그램 메시지 전송 중 예상치 못한 오류가 발생했습니다: {str(e)}")
        return False

def send_telegram_notification(message):
    """텔레그램 메시지 발송을 위한 동기 래퍼 함수"""
    asyncio.run(send_telegram_message(message))

def get_random_headers():
    """랜덤 헤더 생성"""
    user_agent = random.choice(USER_AGENTS)
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.bearcreek.co.kr/',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
    }
    return headers

def fetch_with_retry(url, method='GET', max_retries=3, delay=5, data=None, params=None):
    """재시도 로직이 포함된 HTTP 요청 함수"""
    proxy = random.choice(PROXIES)
    proxies = {'http': proxy, 'https': proxy} if proxy else None
    
    for attempt in range(1, max_retries + 1):
        try:
            headers = get_random_headers()
            logger.info(f"HTTP 요청 시도 {attempt}/{max_retries}: {url} (User-Agent: {headers['User-Agent'][:20]}...)")
            
            # 간헐적으로 실패하는 것을 방지하기 위해 약간의 지연 시간 추가
            if attempt > 1:
                time.sleep(delay * attempt)
            
            session = requests.Session()
            
            # 요청 메소드에 따라 적절한 방식으로 호출
            if method.upper() == 'POST':
                response = session.post(url, headers=headers, proxies=proxies, data=data, params=params, timeout=30)
            else:
                response = session.get(url, headers=headers, proxies=proxies, params=params, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"HTTP 요청 성공: {url} (상태 코드: {response.status_code})")
                
                # Debug: 응답 내용의 일부 로깅
                content_preview = response.text[:200].replace('\n', ' ')
                logger.info(f"응답 내용 미리보기: {content_preview}...")
                
                return response
            else:
                logger.warning(f"HTTP 요청 실패: {url} (상태 코드: {response.status_code})")
        except requests.RequestException as e:
            logger.error(f"HTTP 요청 예외 발생: {str(e)}")
    
    logger.error(f"{max_retries}회 시도 후 요청 실패: {url}")
    return None

def check_available_dates():
    """베어크리크 골프장 예약 가능 날짜 확인"""
    logger.info("베어크리크 골프장 예약 확인을 시작합니다...")
    
    # 현재 날짜 정보
    now = datetime.datetime.now(KST)
    current_year = now.year
    current_month = now.month
    
    # 확인할 년월 설정
    check_year = current_year if current_month <= 11 else current_year + 1
    check_month = (current_month + 1) if current_month <= 11 else 1
    
    # AJAX 요청 파라미터
    params = {
        'strClubCode': 'N',  # 베어크리크 클럽 코드
        'strLGubun': '110',  # 로케이션 구분 코드
        'strReserveDate': f'{check_year}-{check_month:02d}-01',  # 예약 날짜 형식: YYYY-MM-DD
    }
    
    try:
        # 메인 페이지 먼저 방문 (쿠키 수집)
        main_response = fetch_with_retry(BEARCREEK_URL)
        if not main_response:
            logger.error("메인 페이지 로드 실패")
            return False
        
        # 조금 대기 (자연스러운 흐름 모방)
        time.sleep(random.uniform(2, 4))
        
        # 캘린더 데이터 요청 (XML/JSON 형식)
        calendar_response = fetch_with_retry(BEARCREEK_AJAX_URL, params=params)
        if not calendar_response:
            logger.error("캘린더 데이터 요청 실패")
            return False
        
        # 응답 내용 저장 (디버깅용)
        with open(f"calendar_data_{check_year}_{check_month:02d}.txt", "w", encoding="utf-8") as f:
            f.write(calendar_response.text)
        
        # 응답 분석
        available_dates = []
        
        # XML 또는 JSON 응답 형식에 따라 파싱 시도
        try:
            # 먼저 JSON으로 파싱 시도
            data = json.loads(calendar_response.text)
            # JSON 구조에 따라 예약 가능 날짜 추출 로직 추가
            # (구체적인 키와 값은 실제 응답 형식에 맞게 수정 필요)
            logger.info("JSON 응답 파싱 성공")
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 XML로 시도
            soup = BeautifulSoup(calendar_response.text, 'html.parser')
            # XML 구조에 따라 예약 가능 날짜 추출 로직 추가
            available_elements = soup.select('날짜 선택자')
            for element in available_elements:
                date_str = element.get('date')
                if date_str:
                    available_dates.append(date_str)
            logger.info("XML 응답 파싱 성공")
        
        # 예약 가능 날짜가 있을 경우 알림 전송
        if available_dates:
            logger.info(f"예약 가능 날짜 발견: {available_dates}")
            
            # 알림 메시지 구성
            message = f"🏌️ <b>베어크리크 예약 알림</b>\n\n"
            message += f"다음 날짜에 예약이 가능합니다:\n\n"
            
            for date_str in available_dates:
                message += f"- {date_str}\n"
            
            message += f"\n예약 페이지: {BEARCREEK_URL}"
            
            # 텔레그램 알림 전송
            send_telegram_notification(message)
            return True
        else:
            logger.info("예약 가능한 날짜를 찾을 수 없습니다.")
            return False
            
    except Exception as e:
        logger.error(f"예약 확인 중 예외 발생: {str(e)}")
        return False

def run_scheduler():
    """스케줄러 실행"""
    logger.info(f"베어크리크 예약 확인 스케줄러가 시작되었습니다. 확인 주기: {CHECK_INTERVAL_MINUTES}분")
    
    # 즉시 한 번 실행
    check_available_dates()
    
    # 스케줄 설정
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_available_dates)
    
    # 스케줄러 무한 루프
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Ctrl+C로 프로그램이 중단되었습니다.")
    except Exception as e:
        logger.error(f"스케줄러 실행 중 오류 발생: {str(e)}")
    finally:
        logger.info("프로그램을 종료합니다.")

if __name__ == "__main__":
    logger.info("베어크리크 예약 확인 서비스가 시작되었습니다.")
    
    # 커맨드라인 인자 확인
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        # 단일 실행 모드
        logger.info("단일 실행 모드로 실행합니다.")
        check_available_dates()
    else:
        # 스케줄러 모드
        run_scheduler() 