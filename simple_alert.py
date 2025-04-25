#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import asyncio
import schedule
import datetime
import pytz
import logging
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
        logging.FileHandler("simple_alert.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

# 설정 정보
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', 30))

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

def generate_alert_message():
    """알림 메시지 생성"""
    now = datetime.datetime.now(KST)
    
    message = f"🏌️ <b>베어크리크 예약 알림 서비스</b>\n\n"
    message += f"현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    message += f"<b>알림</b>: 베어크리크 골프장 예약 페이지를 수동으로 확인해주세요.\n"
    message += f"서버 환경 제한으로 자동 확인이 불가능합니다.\n\n"
    message += f"예약 페이지: {BEARCREEK_URL}\n"
    message += f"🕒 다음 알림: {(now + datetime.timedelta(minutes=CHECK_INTERVAL_MINUTES)).strftime('%H:%M')}"
    
    return message

def check_and_notify():
    """알림 발송 함수"""
    logger.info("알림 확인 중...")
    
    # 시스템 자원 사용량 확인
    try:
        statvfs = os.statvfs("/")
        free_space_mb = (statvfs.f_frsize * statvfs.f_bavail) / (1024 * 1024)
        used_percent = 100 - (statvfs.f_bavail / statvfs.f_blocks * 100)
        logger.info(f"디스크 여유 공간: {free_space_mb:.2f}MB ({used_percent:.1f}% 사용 중)")
    except Exception as e:
        logger.error(f"디스크 공간 확인 중 오류: {str(e)}")
    
    # 텔레그램 메시지 발송
    message = generate_alert_message()
    logger.info("알림 메시지 생성 완료")
    
    try:
        send_telegram_notification(message)
    except Exception as e:
        logger.error(f"텔레그램 메시지 발송 중 예외 발생: {str(e)}")
    
    # 임시 파일 정리
    try:
        logger.info("임시 파일 정리 중...")
        os.system("rm -rf /tmp/chrome* /tmp/*profile* /tmp/tmp* 2>/dev/null || true")
        os.system("find . -name '*.png' -mtime +7 -delete 2>/dev/null || true")
        os.system("find . -name '*.html' -mtime +7 -delete 2>/dev/null || true")
        logger.info("임시 파일 정리 완료")
    except Exception as e:
        logger.warning(f"임시 파일 정리 중 오류 (무시됨): {str(e)}")
    
    logger.info("알림 확인 완료")

def run_scheduler():
    """스케줄러 실행"""
    logger.info(f"알림 스케줄러가 시작되었습니다. 알림 주기: {CHECK_INTERVAL_MINUTES}분")
    
    # 즉시 한 번 실행
    check_and_notify()
    
    # 스케줄 설정
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_and_notify)
    
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
    logger.info("베어크리크 예약 알림 서비스가 시작되었습니다.")
    
    # 커맨드라인 인자 확인
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        # 단일 실행 모드
        logger.info("단일 실행 모드로 실행합니다.")
        check_and_notify()
    else:
        # 스케줄러 모드
        run_scheduler() 