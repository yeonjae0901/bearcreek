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
import random
from pathlib import Path
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError
from playwright.async_api import async_playwright, Page

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("playwright_checker.log", encoding='utf-8'),
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

# 베어크리크 골프장 예약 페이지 URL
BEARCREEK_URL = "https://www.bearcreek.co.kr/Reservation/Reservation.aspx?strLGubun=110&strClubCode=N#aCourseSel"

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

async def setup_stealth_page():
    """스텔스 모드가 적용된 Playwright 브라우저 페이지 설정"""
    try:
        # Playwright 시작
        playwright = await async_playwright().start()
        
        # 브라우저 시작 옵션 설정
        browser_type = playwright.chromium
        browser = await browser_type.launch(
            headless=True,  # 서버에서는 headless 모드 사용
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-extensions',
                '--disable-component-extensions-with-background-pages',
                '--disable-default-apps',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-background-networking',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-infobars',
            ]
        )
        
        # 브라우저 컨텍스트 생성
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            locale='ko-KR',
            timezone_id='Asia/Seoul',
            geolocation={'latitude': 37.5665, 'longitude': 126.9780},  # 서울 위치
            color_scheme='light',  # 라이트 모드
            java_script_enabled=True,
            ignore_https_errors=True
        )
        
        # Stealth 적용을 위한 JS 스크립트 평가
        await context.add_init_script("""
        // WebDriver 속성 덮어쓰기
        Object.defineProperty(navigator, 'webdriver', {
          get: () => false,
        });
        
        // 사용자 에이전트 변조 (추가 랜덤성)
        if(!window.chrome) {
          window.chrome = {
            runtime: {},
          };
        }
        
        // 플러그인 모방
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
          parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
        );
        """)
        
        # 페이지 생성
        page = await context.new_page()
        
        # 페이지 속성 설정 및 타임아웃 증가
        page.set_default_navigation_timeout(60000)
        page.set_default_timeout(60000)
        
        # 캐시 쿠키 활성화
        await context.add_cookies([{
            'name': 'session_id',
            'value': f'user_{random.randint(10000, 99999)}',
            'domain': '.bearcreek.co.kr',
            'path': '/',
        }])
        
        return page, browser, context, playwright
    except Exception as e:
        logger.error(f"Playwright 브라우저 설정 중 오류 발생: {str(e)}")
        return None, None, None, None

async def clean_up_resources(page=None, browser=None, context=None, playwright=None):
    """리소스 정리 함수"""
    try:
        if page:
            await page.close()
            logger.info("페이지가 정상적으로 닫혔습니다.")
        
        if context:
            await context.close()
            logger.info("브라우저 컨텍스트가 정상적으로 닫혔습니다.")
        
        if browser:
            await browser.close()
            logger.info("브라우저가 정상적으로 닫혔습니다.")
        
        if playwright:
            await playwright.stop()
            logger.info("Playwright가 정상적으로 종료되었습니다.")
    except Exception as e:
        logger.error(f"리소스 정리 중 오류: {str(e)}")

async def check_available_dates_async():
    """베어크리크 골프장 예약 가능 날짜 확인 (비동기)"""
    page, browser, context, playwright = None, None, None, None
    
    try:
        logger.info("Playwright를 사용하여 베어크리크 골프장 예약 확인을 시작합니다...")
        
        page, browser, context, playwright = await setup_stealth_page()
        if not page:
            logger.error("Playwright 페이지 설정 실패")
            return False
        
        # 메인 페이지 접속
        logger.info(f"베어크리크 예약 페이지로 이동 중: {BEARCREEK_URL}")
        response = await page.goto(BEARCREEK_URL, wait_until='domcontentloaded')
        
        # 응답 확인
        if not response or response.status != 200:
            logger.error(f"페이지 로드 실패: 상태 코드 {response.status if response else 'unknown'}")
            
            # 실패 시 페이지 스크린샷 저장
            screenshot_path = "access_failed.png"
            await page.screenshot(path=screenshot_path)
            logger.info(f"실패 페이지 스크린샷 저장됨: {screenshot_path}")
            
            # 페이지 소스 저장
            html_content = await page.content()
            with open("access_failed.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info("실패 페이지 소스 저장됨: access_failed.html")
            
            return False
        
        # 페이지 로딩 대기
        logger.info("페이지 완전히 로드될 때까지 대기 중...")
        await page.wait_for_load_state('networkidle')
        await asyncio.sleep(3)  # 추가 대기
        
        # 예약 페이지 접속 성공 확인
        title = await page.title()
        logger.info(f"페이지 제목: {title}")
        
        # 페이지 스크린샷 저장
        screenshot_path = "bearcreek_main.png"
        await page.screenshot(path=screenshot_path)
        logger.info(f"메인 페이지 스크린샷 저장됨: {screenshot_path}")
        
        # 페이지 소스 저장
        html_content = await page.content()
        with open("bearcreek_main.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info("메인 페이지 소스 저장됨: bearcreek_main.html")
        
        # 달력 선택 (년/월)
        logger.info(f"날짜 선택: {YEAR}년 {MONTH}월")
        
        # 페이지 내 달력 표시 확인
        calendar_selector = "table.calendar"
        try:
            await page.wait_for_selector(calendar_selector, timeout=10000)
            logger.info("달력 테이블 발견됨")
        except Exception as e:
            logger.error(f"달력 테이블을 찾을 수 없음: {str(e)}")
            return False
        
        # 달력에서 예약 가능한 날짜 찾기
        available_dates = []
        
        # 달력 테이블의 날짜 셀 확인
        date_cells = await page.query_selector_all("table.calendar td[onclick]")
        logger.info(f"발견된 날짜 셀: {len(date_cells)}개")
        
        for cell in date_cells:
            # 클릭 가능한 날짜인지 확인 (빨간색 아님)
            class_attr = await cell.get_attribute("class")
            if "red" not in (class_attr or ""):
                # 날짜 텍스트 추출
                date_text = await cell.inner_text()
                if date_text.strip():
                    # 현재 년월과 셀의 날짜를 조합
                    day = date_text.strip()
                    date_str = f"{YEAR}-{MONTH:02d}-{int(day):02d}"
                    available_dates.append(date_str)
                    logger.info(f"예약 가능한 날짜 발견: {date_str}")
        
        # 예약 가능 날짜가 있을 경우 알림 전송
        if available_dates:
            logger.info(f"총 {len(available_dates)}개의 예약 가능 날짜를 찾았습니다.")
            
            # 알림 메시지 구성
            message = f"🏌️ <b>베어크리크 예약 알림</b>\n\n"
            message += f"{YEAR}년 {MONTH}월에 다음 날짜에 예약이 가능합니다:\n\n"
            
            for date_str in available_dates:
                message += f"- {date_str}\n"
            
            message += f"\n예약 페이지: {BEARCREEK_URL}"
            
            # 텔레그램 알림 전송
            await send_telegram_message(message)
            return True
        else:
            logger.info(f"{YEAR}년 {MONTH}월에 예약 가능한 날짜를 찾을 수 없습니다.")
            return False
    
    except Exception as e:
        logger.error(f"예약 확인 중 예외 발생: {str(e)}")
        
        # 오류 발생 시 스크린샷
        if page:
            try:
                await page.screenshot(path="error.png")
                logger.info("오류 페이지 스크린샷 저장됨: error.png")
            except:
                pass
        
        return False
    
    finally:
        # 리소스 정리
        await clean_up_resources(page, browser, context, playwright)

def check_available_dates():
    """베어크리크 골프장 예약 가능 날짜 확인 (동기 래퍼)"""
    return asyncio.run(check_available_dates_async())

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