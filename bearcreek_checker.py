#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import datetime
import logging
import schedule
import asyncio
import platform
import sys
import pytz
import uuid
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

# 로깅 시간 포맷터 클래스 - 한국 시간으로 변환
class KSTFormatter(logging.Formatter):
    def converter(self, timestamp):
        dt = datetime.datetime.fromtimestamp(timestamp, tz=pytz.UTC)
        return dt.astimezone(KST)
    
    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bearcreek_checker.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 모든 핸들러에 KST 포맷터 적용
for handler in logging.getLogger().handlers:
    handler.setFormatter(KSTFormatter('%(asctime)s - %(levelname)s - %(message)s'))

logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

# 설정 정보
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# MONTH와 YEAR 환경변수 로드 및 기본값 설정
try:
    MONTH = int(os.getenv('MONTH', 5))
except ValueError:
    # 환경변수에 주석이 포함된 경우 처리
    month_str = os.getenv('MONTH', '5')
    if '#' in month_str:
        month_str = month_str.split('#')[0].strip()
    MONTH = int(month_str)

# 월 설정 값 강제 지정
MONTH = 5

try:
    YEAR = int(os.getenv('YEAR', 2025))
except ValueError:
    # 환경변수에 주석이 포함된 경우 처리
    year_str = os.getenv('YEAR', '2025')
    if '#' in year_str:
        year_str = year_str.split('#')[0].strip()
    YEAR = int(year_str)

try:
    CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', 30))
except ValueError:
    # 환경변수에 주석이 포함된 경우 처리
    interval_str = os.getenv('CHECK_INTERVAL_MINUTES', '30')
    if '#' in interval_str:
        interval_str = interval_str.split('#')[0].strip()
    CHECK_INTERVAL_MINUTES = int(interval_str)

# 베어크리크 골프장 예약 페이지 URL
BEARCREEK_URL = "https://www.bearcreek.co.kr/Reservation/Reservation.aspx?strLGubun=110&strClubCode=N#aCourseSel"


def setup_driver():
    """Selenium 웹드라이버 설정"""
    try:
        # 기존 크롬 관련 프로세스 및 임시 폴더 정리
        try:
            os.system("pkill -f chrome 2>/dev/null")
            os.system("pkill -f chromium 2>/dev/null")
            os.system("rm -rf /tmp/chrome* /tmp/*profile* /tmp/chromedata* 2>/dev/null")
            logger.info("기존 Chrome 프로세스 및 임시 파일 정리 완료")
        except Exception as e:
            logger.warning(f"Chrome 정리 중 오류 (무시됨): {str(e)}")
        
        # Chrome 옵션 설정 - 최소한의 옵션만 사용
        chrome_options = Options()
        chrome_options.binary_location = "/usr/bin/chromium-browser"
        
        # 핵심 옵션만 설정
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # 드라이버 생성
        try:
            # Linux 서버 환경
            service = Service()
            logger.info("Chrome 드라이버 생성 중...")
            
            # 고유한 데이터 디렉토리 설정
            temp_dir = f"/tmp/chromedata-{time.time()}-{random.randint(10000, 99999)}"
            os.makedirs(temp_dir, exist_ok=True)
            chrome_options.add_argument(f"--user-data-dir={temp_dir}")
            
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 페이지 로딩 타임아웃 설정
            driver.set_page_load_timeout(60)
            
            logger.info("Chrome 드라이버 설정 완료")
            return driver
        except Exception as e:
            logger.error(f"ChromeDriver 설정 중 오류 발생: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"Chrome 드라이버 설정 중 심각한 오류: {str(e)}")
        raise


async def send_telegram_message(message):
    """텔레그램 메시지 발송 함수"""
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        logger.error("텔레그램 설정이 완료되지 않았습니다. .env 파일을 확인하세요.")
        logger.error(f"Bot Token: '{TELEGRAM_BOT_TOKEN}'")
        logger.error(f"Chat ID: '{TELEGRAM_CHAT_ID}'")
        return False
    
    try:
        logger.info(f"텔레그램 봇 토큰 유효성 검사 중... (길이: {len(TELEGRAM_BOT_TOKEN)})")
        logger.info(f"텔레그램 채팅 ID 유효성 검사 중... (값: {TELEGRAM_CHAT_ID})")
        
        # 봇 토큰 형식 확인
        if ":" not in TELEGRAM_BOT_TOKEN:
            logger.error("봇 토큰 형식이 잘못되었습니다. 올바른 형식: 123456789:AbCdEfGhIjKlMnOpQrStUvWxYz")
            return False
        
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        logger.info("텔레그램 봇 객체 생성 완료")
        
        # 채팅 ID 처리
        chat_id = TELEGRAM_CHAT_ID
        if isinstance(chat_id, str):
            # 음수 값 유지하면서 변환 시도
            if chat_id.startswith('-') and chat_id[1:].isdigit():
                chat_id = int(chat_id)
                logger.info(f"채팅 ID를 음수 값으로 변환: {chat_id}")
            elif chat_id.isdigit():
                chat_id = int(chat_id)
                logger.info(f"채팅 ID를 숫자로 변환: {chat_id}")
        
        response = await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
        logger.info(f"텔레그램 메시지가 성공적으로 전송되었습니다. 메시지 ID: {response.message_id}")
        return True
    except TelegramError as e:
        logger.error(f"텔레그램 메시지 전송 중 오류가 발생했습니다: {str(e)}")
        logger.error(f"오류 유형: {type(e).__name__}")
        # 추가 디버깅 정보
        if "Unauthorized" in str(e):
            logger.error("봇 토큰이 유효하지 않습니다. 새로운 토큰을 생성하거나 토큰 값을 확인하세요.")
        elif "Chat not found" in str(e):
            logger.error("채팅 ID를 찾을 수 없습니다. 채팅 ID가 올바른지 확인하세요.")
        elif "Bad Request" in str(e):
            logger.error("잘못된 요청입니다. 메시지 형식이나 매개변수를 확인하세요.")
        return False
    except Exception as e:
        logger.error(f"텔레그램 메시지 전송 중 예상치 못한 오류가 발생했습니다: {str(e)}")
        return False


def send_telegram_notification(message):
    """텔레그램 메시지 발송을 위한 동기 래퍼 함수"""
    asyncio.run(send_telegram_message(message))


def check_available_dates(single_run=False):
    """베어크리크 골프장 예약 가능 날짜 확인"""
    logger.info("베어크리크 골프장 예약 확인을 시작합니다...")
    
    # 디스크 공간 확인
    try:
        statvfs = os.statvfs("/")
        free_space_mb = (statvfs.f_frsize * statvfs.f_bavail) / (1024 * 1024)
        used_percent = 100 - (statvfs.f_bavail / statvfs.f_blocks * 100)
        logger.info(f"디스크 여유 공간: {free_space_mb:.2f}MB ({used_percent:.1f}% 사용 중)")
        
        # 디스크 여유 공간이 500MB 미만이면 임시 파일 정리
        if free_space_mb < 500:
            logger.warning("디스크 여유 공간이 부족합니다. 임시 파일 정리를 시도합니다.")
            os.system("rm -rf /tmp/chrome* /tmp/*profile* /tmp/*.png /tmp/*.html 2>/dev/null")
    except Exception as e:
        logger.error(f"디스크 공간 확인 중 오류: {str(e)}")
    
    driver = None
    available_dates = []
    available_times = {}  # 날짜별 예약 가능 시간을 저장할 딕셔너리
    
    try:
        driver = setup_driver()
        
        # 베어크리크 골프장 예약 페이지 접속
        driver.get(BEARCREEK_URL)
        logger.info("웹페이지에 접속했습니다.")
        
        # 쿠키 설정 및 JavaScript 실행을 위한 시간 대기
        time.sleep(10)
        
        # 페이지 로딩 문제 시 스크린샷 저장
        driver.save_screenshot("calendar_page.png")
        logger.info("현재 페이지 스크린샷을 저장했습니다: calendar_page.png")
        
        # 페이지 HTML 출력 (디버깅용)
        page_source = driver.page_source
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(page_source)
        logger.info("페이지 소스를 저장했습니다: page_source.html")
        
        # 예약 가능한 날짜 찾기
        try:
            logger.info("페이지에서 예약 가능한 날짜 찾는 중...")
            
            # "예약가능" 텍스트가 포함된 title 속성을 가진 td 요소 찾기
            available_tds = driver.find_elements(By.XPATH, "//td[contains(@title, '예약가능')]")
            logger.info(f"'예약가능' title 속성을 가진 td 요소 수: {len(available_tds)}")
            
            # 예약 가능한 날짜 정보를 미리 추출
            date_infos = []
            for td in available_tds:
                try:
                    title = td.get_attribute('title')
                    logger.info(f"예약가능 td의 title: '{title}'")
                    
                    # href 속성에서 날짜 정보 추출 시도
                    a_tag = td.find_element(By.TAG_NAME, 'a')
                    onclick_attr = a_tag.get_attribute('onclick')
                    logger.info(f"클릭 이벤트: {onclick_attr}")
                    
                    # 날짜 추출
                    import re
                    
                    # YYYY년 MM월 DD일 패턴 추출
                    date_match = re.search(r'(\d{4})년\s*(\d{2})월\s*(\d{2})일', title)
                    if date_match:
                        year, month, day = map(int, date_match.groups())
                        date_str = f"{year}-{month:02d}-{day:02d}"
                        if date_str not in available_dates:
                            available_dates.append(date_str)
                            date_infos.append((date_str, onclick_attr))
                            logger.info(f"예약 가능한 날짜 찾음 (title년월일): {date_str}")
                        continue
                    
                    # MM월 DD일 패턴 추출
                    date_match = re.search(r'(\d{1,2})월\s*(\d{1,2})일', title)
                    if date_match:
                        month, day = map(int, date_match.groups())
                        date_str = f"{YEAR}-{month:02d}-{day:02d}"
                        if date_str not in available_dates:
                            available_dates.append(date_str)
                            date_infos.append((date_str, onclick_attr))
                            logger.info(f"예약 가능한 날짜 찾음 (title월일): {date_str}")
                        continue
                    
                    # DD일 패턴 추출
                    day_match = re.search(r'(\d{1,2})일', title)
                    if day_match:
                        day = int(day_match.group(1))
                        date_str = f"{YEAR}-{MONTH:02d}-{day:02d}"
                        if date_str not in available_dates:
                            available_dates.append(date_str)
                            date_infos.append((date_str, onclick_attr))
                            logger.info(f"예약 가능한 날짜 찾음 (title일): {date_str}")
                except Exception as e:
                    logger.warning(f"예약가능 td 처리 중 오류: {str(e)}")
            
            # 모든 날짜에 대한 시간 정보 가져오기
            for date_str, onclick in date_infos:
                try:
                    # 페이지 다시 로드
                    driver.get(BEARCREEK_URL)
                    time.sleep(5)
                    
                    # 클릭할 날짜 요소 다시 찾기
                    date_xpath = f"//td[contains(@title, '{date_str.replace('-', '년 ', 1).replace('-', '월 ')}일')]//a"
                    logger.info(f"날짜 요소 찾는 XPath: {date_xpath}")
                    
                    try:
                        date_element = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, date_xpath))
                        )
                        # 날짜 클릭
                        driver.execute_script("arguments[0].click();", date_element)
                        logger.info(f"{date_str} 날짜 클릭됨, 시간 정보 로딩 중...")
                        
                        # 시간 정보가 로드될 때까지 충분히 기다림
                        time.sleep(10)
                        
                        # 해당 날짜에 대한 시간 정보 페이지 스크린샷 저장
                        screenshot_file = f"time_info_{date_str}.png"
                        driver.save_screenshot(screenshot_file)
                        logger.info(f"시간 정보 페이지 스크린샷 저장: {screenshot_file}")
                        
                        # 페이지 소스 저장
                        html_file = f"time_page_{date_str}.html"
                        with open(html_file, "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                        logger.info(f"시간 정보 페이지 소스 저장: {html_file}")
                        
                        # 시간 정보 행 찾기
                        time_rows = driver.find_elements(By.XPATH, "//table[@class='table-body']//tr")
                        
                        if not time_rows:
                            logger.info(f"{date_str}에 예약 가능한 시간이 없거나 이미 예약된 상태입니다. 건너뜁니다.")
                            continue
                        
                        logger.info(f"시간 정보 행 찾음 ({len(time_rows)}개): //table[@class='table-body']//tr")
                        
                        # 시간 정보 추출 및 저장
                        time_info = []
                        for row in time_rows:
                            try:
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) >= 4:
                                    course = cells[0].text.strip()
                                    tee_time = cells[1].text.strip()
                                    price = cells[3].text.strip()
                                    
                                    if course and tee_time:  # 의미 있는 데이터인지 확인
                                        time_info.append(f"{course} {tee_time} ({price}원)")
                                        logger.info(f"시간 정보 추출: {course} {tee_time} ({price}원)")
                            except Exception as e:
                                logger.warning(f"시간 정보 행 처리 중 오류: {str(e)}")
                        
                        if time_info:
                            available_times[date_str] = time_info
                            logger.info(f"{date_str}에 {len(time_info)}개의 이용 가능 시간 찾음")
                        else:
                            logger.warning(f"{date_str}에 이용 가능한 시간 정보를 찾지 못함")
                            # 시간 정보가 없으면 예약 가능한 날짜에서 제외
                            if date_str in available_dates:
                                available_dates.remove(date_str)
                                logger.info(f"{date_str}는 시간 정보가 없어 예약 가능한 날짜에서 제외되었습니다.")
                    except Exception as e:
                        logger.error(f"날짜 요소 클릭 또는 시간 정보 테이블 대기 중 오류: {str(e)}")
                        driver.save_screenshot(f"click_error_{date_str.replace('-', '_')}.png")
                except Exception as e:
                    logger.error(f"{date_str} 시간 정보 추출 중 오류: {str(e)}")
                    driver.save_screenshot(f"time_error_{date_str.replace('-', '_')}.png")
            
            # 콘솔에 예약 가능한 날짜 출력
            print("\n===== 예약 가능한 날짜 =====")
            print(f"🏌️ 베어크리크 춘천 {MONTH}월 예약 가능 알림")
            
            # 설정된 월의 예약만 필터링
            target_month_dates = [date for date in available_dates if date.startswith(f"{YEAR}-{MONTH:02d}")]
            
            if target_month_dates:
                print(f"현재 베어크리크 춘천 골프장에 {MONTH}월 예약 가능한 날짜가 있습니다!")
                print("\n예약 가능 날짜:")
                for date in target_month_dates:
                    print(f"• {date}")
                    if date in available_times and available_times[date]:
                        print("  이용 가능 시간:")
                        for time_slot in available_times[date]:
                            print(f"  - {time_slot}")
            else:
                print(f"현재 베어크리크 춘천 골프장에 {MONTH}월 예약 가능한 날짜가 없습니다.")
            print(f"\n예약 페이지: {BEARCREEK_URL}")
            print(f"알림 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("===========================\n")
            
            # 텔레그램 메시지 발송 (설정된 월 예약만)
            if target_month_dates:
                logger.info(f"{MONTH}월 예약 가능한 날짜를 {len(target_month_dates)}개 찾았습니다!")
                
                # 텔레그램 메시지 생성 및 발송
                telegram_message = f"🏌️ <b>베어크리크 춘천 {MONTH}월 예약 가능 알림</b>\n\n"
                telegram_message += f"현재 베어크리크 춘천 골프장에 {MONTH}월 예약 가능한 날짜가 있습니다!\n\n"
                telegram_message += "<b>예약 가능 날짜:</b>\n"
                
                for date in target_month_dates:
                    telegram_message += f"• <b>{date}</b>\n"
                    
                    # 해당 날짜의 예약 가능 시간 추가
                    if date in available_times and available_times[date]:
                        telegram_message += "  <u>이용 가능 시간:</u>\n"
                        for time_slot in available_times[date]:
                            telegram_message += f"  - {time_slot}\n"
                    
                telegram_message += f"\n예약 페이지: {BEARCREEK_URL}\n"
                telegram_message += f"알림 시간: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                # 텔레그램 봇 토큰과 채팅 ID 확인
                logger.info(f"Telegram Bot Token 확인: {TELEGRAM_BOT_TOKEN[:5]}...{TELEGRAM_BOT_TOKEN[-5:] if TELEGRAM_BOT_TOKEN else ''}")
                logger.info(f"Telegram Chat ID 확인: {TELEGRAM_CHAT_ID}")
                
                try:
                    send_telegram_notification(telegram_message)
                except Exception as e:
                    logger.error(f"텔레그램 메시지 발송 중 예외 발생: {str(e)}")
                    logger.warning("텔레그램 메시지 발송은 실패했지만, 위 콘솔 출력에서 예약 가능한 날짜를 확인할 수 있습니다.")
            else:
                logger.info(f"{MONTH}월에 예약 가능한 날짜가 없습니다. 텔레그램 알림 생략.")
        except Exception as e:
            logger.error(f"달력 확인 중 오류 발생: {str(e)}")
            driver.save_screenshot("date_check_error.png")
    except TimeoutException:
        logger.error("페이지 로딩 시간이 초과되었습니다.")
        if driver:
            driver.save_screenshot("timeout_error.png")
    except WebDriverException as e:
        logger.error(f"웹드라이버 오류 발생: {str(e)}")
    except Exception as e:
        logger.error(f"예약 확인 중 오류 발생: {str(e)}")
        if driver:
            driver.save_screenshot("error.png")
    finally:
        # 드라이버 종료
        if driver:
            driver.quit()
        
        # 임시 파일 정리
        try:
            logger.info("임시 파일 정리 중...")
            os.system("rm -rf /tmp/chrome* /tmp/*profile* /tmp/chromedata* 2>/dev/null")
            # 현재 디렉토리의 오래된 PNG 및 HTML 파일 정리 (7일 이상)
            os.system("find . -name '*.png' -mtime +7 -delete 2>/dev/null")
            os.system("find . -name '*.html' -mtime +7 -delete 2>/dev/null")
            logger.info("임시 파일 정리 완료")
        except Exception as e:
            logger.warning(f"임시 파일 정리 중 오류 (무시됨): {str(e)}")
            
        logger.info("베어크리크 골프장 예약 확인이 완료되었습니다.")
        
        # 단일 실행 모드인 경우 종료
        if single_run:
            logger.info("단일 실행 모드로 실행되어 프로그램을 종료합니다.")
            sys.exit(0)
    
    return available_dates


def run_scheduler():
    """스케줄러 실행"""
    logger.info(f"베어크리크 예약 확인 스케줄러가 시작되었습니다. 확인 주기: {CHECK_INTERVAL_MINUTES}분")
    
    # 즉시 한 번 실행
    check_available_dates()
    
    # 스케줄 설정
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_available_dates)
    
    # 스케줄러 무한 루프
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    logger.info("베어크리크 알리미가 시작되었습니다.")
    
    # 커맨드라인 인자 확인
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        # 단일 실행 모드
        logger.info("단일 실행 모드로 실행합니다.")
        check_available_dates(single_run=True)
    else:
        # 스케줄러 모드
        run_scheduler() 