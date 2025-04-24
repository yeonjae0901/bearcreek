import time
import schedule
from log import logger

def run_scheduler():
    """스케줄러 실행"""
    logger.info(f"베어크리크 예약 확인 스케줄러가 시작되었습니다. 확인 주기: {CHECK_INTERVAL_MINUTES}분")
    
    # 즉시 한 번 실행
    check_available_dates()
    
    # 스케줄 설정
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(check_available_dates)
    
    # 매일 자정에 파일 정리 스케줄 추가
    try:
        from cleanup import cleanup_old_files
        schedule.every().day.at("00:00").do(cleanup_old_files)
        logger.info("파일 정리 스케줄러가 설정되었습니다. 매일 자정에 실행됩니다.")
    except Exception as e:
        logger.error(f"파일 정리 스케줄러 설정 중 오류: {str(e)}")
    
    # 스케줄러 무한 루프
    while True:
        schedule.run_pending()
        time.sleep(1) 