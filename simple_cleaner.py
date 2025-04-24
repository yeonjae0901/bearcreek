#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import glob
import logging
import datetime
import sys
import schedule

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleaner.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def cleanup_system():
    '''시스템 정리: 임시 파일, 로그 등'''
    logger.info('시스템 정리 작업 시작')
    
    # 현재 디렉토리
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 먼저 디스크 사용량 체크
    disk_usage_percent = 0
    free_space_mb = 0
    if sys.platform == 'linux':
        try:
            statvfs = os.statvfs('/')
            free_space_mb = (statvfs.f_frsize * statvfs.f_bavail) / (1024 * 1024)
            disk_usage_percent = 100 - (statvfs.f_bavail / statvfs.f_blocks * 100)
            logger.info(f'디스크 여유 공간: {free_space_mb:.2f}MB ({disk_usage_percent:.1f}% 사용 중)')
        except Exception as e:
            logger.error(f'디스크 공간 확인 오류: {e}')
    
    # 오래된 이미지 및 HTML 파일 삭제
    total_removed = 0
    patterns = ['*.png', '*.html']
    for pattern in patterns:
        files = glob.glob(os.path.join(current_dir, pattern))
        for file_path in files:
            try:
                os.remove(file_path)
                logger.info(f'파일 삭제: {file_path}')
                total_removed += 1
            except Exception as e:
                logger.error(f'파일 삭제 오류: {file_path} - {e}')
    
    # 로그 로테이션
    log_files = ['bearcreek_checker.log', 'bearcreek.log', 'new_log.txt', 'final_log.txt', 'starter.log']
    for log_file in log_files:
        log_path = os.path.join(current_dir, log_file)
        if os.path.exists(log_path):
            try:
                with open(log_path, 'w') as f:
                    f.write(f'로그 정리됨: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
                logger.info(f'로그 파일 정리: {log_file}')
            except Exception as e:
                logger.error(f'로그 파일 정리 오류: {log_file} - {e}')
    
    # Chrome 임시 파일 정리
    os.system('rm -rf /tmp/.com.google.Chrome* /tmp/chromedriver* /tmp/.org.chromium.Chromium* 2>/dev/null')
    os.system('rm -rf /tmp/junk* /tmp/scoped_dir* 2>/dev/null')
    os.system('rm -rf ~/.cache/chromium/* ~/.cache/google-chrome/* 2>/dev/null')
    logger.info('Chrome 임시 파일 정리 완료')
    
    # Snap 패키지 정리 - 디스크 사용량이 높을 때만 실행
    if disk_usage_percent > 80:
        try:
            logger.info('디스크 사용량이 높아 스냅 패키지 정리를 시도합니다')
            
            # 사용자가 실행 중인 경우 스냅 캐시만 정리 (sudo 없이도 가능한 작업)
            # 스냅 관련 임시 파일 정리
            os.system('rm -rf ~/.cache/snapd/* 2>/dev/null')
            
            # 스냅 정리 스크립트 생성
            snap_cleanup_script = os.path.join(current_dir, 'snap_cleanup.sh')
            with open(snap_cleanup_script, 'w') as f:
                f.write('#!/bin/bash\n')
                f.write('# 스냅 패키지 정리 스크립트\n')
                f.write('set -e\n\n')
                f.write('# 오래된 스냅 버전 정리\n')
                f.write('snap set system refresh.retain=2\n')
                f.write('rm -rf /var/lib/snapd/cache/*\n\n')
                f.write('# 불필요한 snap 관련 로그 정리\n')
                f.write('find /var/log/journal -type f -name "*.journal" -mtime +7 -delete 2>/dev/null\n')
                f.write('echo "스냅 정리 완료: $(date)"\n')
            
            # 스크립트 실행 권한 부여
            os.chmod(snap_cleanup_script, 0o755)
            
            logger.info(f'스냅 정리 스크립트가 생성되었습니다: {snap_cleanup_script}')
            logger.info('관리자 권한으로 다음 명령어를 실행하세요: sudo ./snap_cleanup.sh')
            
        except Exception as e:
            logger.error(f'스냅 패키지 정리 파일 생성 오류: {e}')
    else:
        logger.info('디스크 사용량이 정상 범위 내에 있어 스냅 정리를 건너뜁니다')
    
    # 최종 디스크 사용량 체크
    if sys.platform == 'linux':
        try:
            statvfs = os.statvfs(current_dir)
            free_space_mb = (statvfs.f_frsize * statvfs.f_bavail) / (1024 * 1024)
            used_percent = 100 - (statvfs.f_bavail / statvfs.f_blocks * 100)
            logger.info(f'정리 후 디스크 여유 공간: {free_space_mb:.2f}MB ({used_percent:.1f}% 사용 중)')
        except Exception as e:
            logger.error(f'디스크 공간 확인 오류: {e}')
    
    logger.info(f'시스템 정리 완료: {total_removed}개 파일 삭제됨')
    return total_removed

if __name__ == '__main__':
    logger.info('시스템 정리 스크립트 시작')
    
    # 즉시 한 번 실행
    cleanup_system()
    
    # 1시간마다 자동 실행 (선택적)
    schedule.every(1).hours.do(cleanup_system)
    logger.info('정기 정리 스케줄 설정: 1시간마다 실행')

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info('사용자에 의해 스크립트가 종료되었습니다.')
    except Exception as e:
        logger.error(f'스크립트 실행 중 오류 발생: {e}')
    
    logger.info('시스템 정리 스크립트 종료') 