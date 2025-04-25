#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import datetime
import logging
import schedule
import asyncio
import sys
import pytz
import json
import random
import re
import cloudscraper
from pathlib import Path
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError
from playwright.async_api import async_playwright

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ultimate_checker.log", encoding='utf-8'),
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
MONTH = int(os.getenv('MONTH', 4).replace('%', ''))
YEAR = int(os.getenv('YEAR', 2025).replace('%', ''))

# 베어크리크 골프장 URL 정보
BEARCREEK_URL = "https://www.bearcreek.co.kr/Reservation/Reservation.aspx?strLGubun=110&strClubCode=N#aCourseSel"
BEARCREEK_API_URL = "https://www.bearcreek.co.kr/Reservation/XmlCalendarData.aspx"

# 클라우드스크레이퍼 세션 (전역변수)
scraper = None

# 사용자 에이전트 목록
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

# 테스트용 쿠키가 존재하는 파일 경로
COOKIES_FILE = 'bearcreek_cookies.json'

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

def get_random_user_agent():
    """무작위 사용자 에이전트 선택"""
    return random.choice(USER_AGENTS)

def load_cookies_from_file():
    """저장된the 쿠키 파일에서 쿠키 로드"""
    try:
        if os.path.exists(COOKIES_FILE):
            with open(COOKIES_FILE, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"쿠키 파일을 찾을 수 없습니다: {COOKIES_FILE}")
            return []
    except Exception as e:
        logger.error(f"쿠키 파일 로드 중 오류: {str(e)}")
        return []

def save_cookies_to_file(cookies):
    """쿠키를 파일에 저장"""
    try:
        with open(COOKIES_FILE, 'w') as f:
            json.dump(cookies, f)
        logger.info(f"쿠키가 {COOKIES_FILE}에 저장되었습니다.")
    except Exception as e:
        logger.error(f"쿠키 저장 중 오류: {str(e)}")

async def generate_cookies_with_playwright():
    """Playwright를 사용하여 쿠키 생성"""
    logger.info("Playwright를 사용하여 새 쿠키 생성 중...")
    
    playwright = None
    browser = None
    context = None
    page = None
    
    try:
        playwright = await async_playwright().start()
        browser_type = playwright.chromium
        
        # 브라우저 시작 (스텔스 모드)
        browser = await browser_type.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--no-sandbox',
                '--disable-web-security',
            ]
        )
        
        # 브라우저 컨텍스트 생성
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=get_random_user_agent(),
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            java_script_enabled=True
        )
        
        # WebDriver 속성 덮어쓰기 등 스텔스 기능 추가
        await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
          get: () => false,
        });
        
        if(!window.chrome) {
          window.chrome = {
            runtime: {},
          };
        }
        
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
          parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
        );
        """)
        
        # 페이지 생성 및 타임아웃 설정
        page = await context.new_page()
        page.set_default_navigation_timeout(60000)
        
        # 메인 페이지 접속
        logger.info(f"베어크리크 메인 페이지 접속 중: {BEARCREEK_URL}")
        await page.goto(BEARCREEK_URL, wait_until='networkidle')
        
        # 페이지 로드 대기 (추가 여유)
        await page.wait_for_timeout(5000)
        
        # CF 우회를 위한 인터랙션 시뮬레이션 (마우스 이동 및 스크롤)
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
        # 마우스 휠 스크롤 (delta_x, delta_y) - x축 스크롤은 0으로 설정
        await page.mouse.wheel(0, random.randint(100, 300))
        await page.wait_for_timeout(1000)
        
        # 페이지 소스 확인
        content = await page.content()
        if "Checking your browser" in content or "cloudflare" in content.lower():
            logger.info("Cloudflare 확인 화면 감지됨, 추가 대기 중...")
            await page.wait_for_timeout(10000)  # 추가 대기
        
        # 쿠키 추출
        cookies = await context.cookies()
        logger.info(f"생성된 쿠키 개수: {len(cookies)}")
        
        # 쿠키 저장
        if cookies:
            save_cookies_to_file(cookies)
            return cookies
        else:
            logger.warning("쿠키가 생성되지 않았습니다.")
            return []
            
    except Exception as e:
        logger.error(f"Playwright로 쿠키 생성 중 오류: {str(e)}")
        return []
    finally:
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

def setup_cloudscraper():
    """CloudScraper 설정"""
    global scraper
    
    try:
        # 이미 생성된 경우 재사용
        if scraper:
            return scraper
        
        # 새로운 CloudScraper 인스턴스 생성
        logger.info("CloudScraper 인스턴스 생성 중...")
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            },
            delay=5,  # 각 요청 사이 지연 시간
            debug=False
        )
        
        # 사용자 에이전트 설정
        scraper.headers.update({
            'User-Agent': get_random_user_agent(),
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Referer': 'https://www.bearcreek.co.kr/',
        })
        
        # 저장된 쿠키 로드
        cookies = load_cookies_from_file()
        if cookies:
            logger.info(f"저장된 쿠키 {len(cookies)}개 로드됨")
            # CloudScraper 요구 형식으로 쿠키 변환
            for cookie in cookies:
                scraper.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
        else:
            logger.warning("저장된 쿠키가 없습니다. 쿠키를 새로 생성합니다.")
            # 비동기 함수 호출을 위한 임시 실행
            new_cookies = asyncio.run(generate_cookies_with_playwright())
            if new_cookies:
                for cookie in new_cookies:
                    scraper.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
        
        return scraper
    except Exception as e:
        logger.error(f"CloudScraper 설정 중 오류: {str(e)}")
        return None

def extract_valid_dates(html_content):
    """HTML에서 예약 가능한 날짜 추출"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        available_dates = []
        
        # 달력 테이블 찾기
        calendar_table = soup.select_one('table.calendar')
        if not calendar_table:
            logger.warning("달력 테이블을 찾을 수 없습니다.")
            return []
        
        # 클릭 가능한 날짜 찾기 (onclick 속성이 있는 td)
        date_cells = calendar_table.select('td[onclick]')
        logger.info(f"발견된 날짜 셀: {len(date_cells)}개")
        
        for cell in date_cells:
            # 예약 불가능한 날짜 제외 (class에 'red'가 포함된 경우)
            if 'red' in cell.get('class', []):
                continue
            
            # 날짜 텍스트 추출
            date_text = cell.text.strip()
            if date_text and date_text.isdigit():
                day = int(date_text)
                date_str = f"{YEAR}-{MONTH:02d}-{day:02d}"
                available_dates.append(date_str)
                logger.info(f"예약 가능한 날짜 발견: {date_str}")
        
        return available_dates
    except Exception as e:
        logger.error(f"HTML에서 날짜 추출 중 오류: {str(e)}")
        return []

def check_available_dates():
    """베어크리크 골프장 예약 가능 날짜 확인 (CloudScraper 사용)"""
    logger.info("베어크리크 골프장 예약 확인을 시작합니다...")
    
    # CloudScraper 설정
    global scraper
    scraper = setup_cloudscraper()
    if not scraper:
        logger.error("CloudScraper 설정 실패")
        return False
    
    try:
        # 1. 메인 페이지 접속 (쿠키 및 토큰 수집)
        logger.info(f"메인 페이지 접속 중: {BEARCREEK_URL}")
        
        # Cloudflare 우회를 위한 추가 헤더
        scraper.headers.update({
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Chromium";v="110", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        })
        
        response = scraper.get(BEARCREEK_URL, timeout=30)
        if response.status_code != 200:
            logger.error(f"메인 페이지 접속 실패: 상태 코드 {response.status_code}")
            
            # 응답 내용 저장 (디버깅용)
            with open("cloudflare_challenge.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            logger.info("응답 내용이 cloudflare_challenge.html에 저장되었습니다.")
            
            # Cloudflare 우회 실패 시 새 쿠키 생성 시도
            new_cookies = asyncio.run(generate_cookies_with_playwright())
            if new_cookies:
                for cookie in new_cookies:
                    scraper.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
                
                # 재시도
                logger.info("새 쿠키로 메인 페이지 접속 재시도 중...")
                response = scraper.get(BEARCREEK_URL, timeout=30)
                if response.status_code != 200:
                    logger.error(f"재시도 실패: 상태 코드 {response.status_code}")
                    return False
            else:
                return False
        
        # 응답 내용 저장 (디버깅용)
        with open("main_page.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        logger.info("메인 페이지 내용이 main_page.html에 저장되었습니다.")
        
        # 2. AJAX 요청을 통해 캘린더 데이터 가져오기
        # 요청 파라미터 설정
        calendar_params = {
            'strClubCode': 'N', 
            'strLGubun': '110',
            'strReserveDate': f'{YEAR}-{MONTH:02d}-01'
        }
        
        # AJAX 요청 헤더 설정 (더 자연스러운 요청 흉내)
        ajax_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': BEARCREEK_URL,
            'Origin': 'https://www.bearcreek.co.kr',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
        }
        
        # 일단 메인 페이지 HTML로 직접 달력 파싱 시도
        available_dates = extract_valid_dates(response.text)
        if available_dates:
            # 달력 데이터가 메인 페이지에서 추출되면 API 호출 불필요
            logger.info("메인 페이지에서 달력 데이터 추출 성공")
        else:
            # 메인 페이지에서 달력 추출 실패 시 API 호출 시도
            logger.info(f"캘린더 데이터 요청 중: {BEARCREEK_API_URL}")
            try:
                calendar_response = scraper.post(
                    BEARCREEK_API_URL, 
                    headers=ajax_headers,
                    data=calendar_params,
                    timeout=30
                )
                
                if calendar_response.status_code != 200:
                    logger.error(f"캘린더 데이터 요청 실패: 상태 코드 {calendar_response.status_code}")
                else:
                    # 응답 내용 저장 (디버깅용)
                    with open(f"calendar_data_{YEAR}_{MONTH:02d}.html", "w", encoding="utf-8") as f:
                        f.write(calendar_response.text)
                    logger.info(f"캘린더 데이터가 calendar_data_{YEAR}_{MONTH:02d}.html에 저장되었습니다.")
                    
                    # 응답된 XML/HTML에서 날짜 추출 시도
                    soup = BeautifulSoup(calendar_response.text, 'html.parser')
                    logger.info(f"캘린더 데이터 길이: {len(calendar_response.text)}")
                    
                    # 디버깅용 API 응답 출력
                    preview = calendar_response.text[:200].replace('\n', ' ')
                    logger.info(f"캘린더 API 응답 미리보기: {preview}...")
            except Exception as e:
                logger.error(f"캘린더 API 요청 중 예외 발생: {str(e)}")
        
        # 4. 결과 처리
        if available_dates:
            logger.info(f"총 {len(available_dates)}개의 예약 가능 날짜를 찾았습니다.")
            
            # 알림 메시지 구성
            message = f"🏌️ <b>베어크리크 예약 알림</b>\n\n"
            message += f"{YEAR}년 {MONTH}월에 다음 날짜에 예약이 가능합니다:\n\n"
            
            for date_str in available_dates:
                message += f"- {date_str}\n"
            
            message += f"\n예약 페이지: {BEARCREEK_URL}"
            
            # 텔레그램 알림 전송
            send_telegram_notification(message)
            return True
        else:
            logger.info(f"{YEAR}년 {MONTH}월에 예약 가능한 날짜를 찾을 수 없습니다.")
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