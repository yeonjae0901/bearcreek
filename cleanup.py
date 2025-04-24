#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import time
import logging
import datetime
import sys

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleanup.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def cleanup_old_files():
    """오래된 스크린샷, HTML 파일, 로그 파일 정리"""
    # 현재 디렉토리
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info(f'현재 디렉토리: {current_dir}')
    
    # 24시간 이상 지난 파일은 삭제
    hours_threshold = 24
    now = time.time()
    cutoff_time = now - (hours_threshold * 3600)
    
    # 스크린샷 및 HTML 파일 삭제
    patterns = ['*.png', '*.html']
    total_removed = 0
    
    for pattern in patterns:
        files = glob.glob(os.path.join(current_dir, pattern))
        for file_path in files:
            if os.path.isfile(file_path):
                file_time = os.path.getmtime(file_path)
                if file_time < cutoff_time:
                    try:
                        os.remove(file_path)
                        logger.info(f'삭제됨: {file_path}')
                        total_removed += 1
                    except Exception as e:
                        logger.error(f'파일 삭제 중 오류: {file_path} - {str(e)}')
    
    # 로그 로테이션 - 큰 로그 파일만 처리
    log_files = ['bearcreek_checker.log', 'bearcreek.log']
    max_log_size = 5 * 1024 * 1024  # 5MB
    
    for log_file in log_files:
        log_path = os.path.join(current_dir, log_file)
        if os.path.exists(log_path) and os.path.getsize(log_path) > max_log_size:
            # 날짜를 포함한 백업 파일명 생성
            backup_date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f'{log_file}.{backup_date}'
            backup_path = os.path.join(current_dir, backup_file)
            
            try:
                # 파일 복사 후 기존 파일 비우기
                with open(log_path, 'rb') as src, open(backup_path, 'wb') as dst:
                    dst.write(src.read())
                with open(log_path, 'w') as f:
                    f.write('')
                logger.info(f'로그 로테이션 완료: {log_file} -> {backup_file}')
                
                # 백업 파일 개수가 3개 이상이면 가장 오래된 것 삭제
                backup_files = sorted(glob.glob(os.path.join(current_dir, f'{log_file}.*')))
                if len(backup_files) > 3:
                    for old_file in backup_files[:-3]:
                        os.remove(old_file)
                        logger.info(f'오래된 로그 백업 삭제: {old_file}')
            except Exception as e:
                logger.error(f'로그 로테이션 중 오류: {log_file} - {str(e)}')
    
    # 여유 공간 확인
    if sys.platform == 'linux':
        try:
            statvfs = os.statvfs(current_dir)
            free_space_mb = (statvfs.f_frsize * statvfs.f_bavail) / (1024 * 1024)
            used_percent = 100 - (statvfs.f_bavail / statvfs.f_blocks * 100)
            logger.info(f'현재 디스크 여유 공간: {free_space_mb:.2f}MB ({used_percent:.1f}% 사용 중)')
            
            # 디스크 사용량이 90% 이상이면 Chrome 캐시 및 임시 파일 추가 정리
            if used_percent > 90:
                logger.warning(f'디스크 사용량이 높습니다: {used_percent:.1f}%')
                logger.info('Chrome 캐시 및 임시 파일 추가 정리 중...')
                os.system('rm -rf ~/.cache/chromium ~/.cache/google-chrome 2>/dev/null')
                os.system('rm -rf /tmp/.com.google.Chrome* /tmp/chromedriver* /tmp/.org.chromium.Chromium* 2>/dev/null')
                os.system('rm -rf /tmp/junk* /tmp/scoped_dir* 2>/dev/null')
        except Exception as e:
            logger.error(f'디스크 공간 확인 중 오류: {str(e)}')
    
    logger.info(f'정리 완료: {total_removed}개 파일 삭제됨')
    return total_removed

if __name__ == '__main__':
    logger.info('파일 정리 스크립트 시작')
    cleanup_old_files()
    logger.info('파일 정리 스크립트 종료') 