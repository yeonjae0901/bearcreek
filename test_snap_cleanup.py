#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import sys

# 로그 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_snap_cleanup_script():
    """스냅 정리 스크립트 생성"""
    logger.info('스냅 정리 스크립트 생성 시작')
    
    # 현재 디렉토리
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # 스냅 정리 스크립트 생성
        snap_cleanup_script = os.path.join(current_dir, 'snap_cleanup.sh')
        with open(snap_cleanup_script, 'w') as f:
            f.write('#!/bin/bash\n')
            f.write('# 스냅 패키지 정리 스크립트\n')
            f.write('set -e\n\n')
            f.write('echo "스냅 정리 시작: $(date)"\n\n')
            f.write('# 오래된 스냅 버전 정리\n')
            f.write('echo "스냅 버전 제한 설정 (최대 2개)..."\n')
            f.write('snap set system refresh.retain=2\n\n')
            f.write('echo "스냅 캐시 정리..."\n')
            f.write('rm -rf /var/lib/snapd/cache/*\n\n')
            f.write('echo "불필요한 스냅 로그 정리..."\n')
            f.write('find /var/log/journal -type f -name "*.journal" -mtime +7 -delete 2>/dev/null\n\n')
            f.write('# 스냅 리스트 확인\n')
            f.write('echo "현재 설치된 스냅 패키지:"\n')
            f.write('snap list\n\n')
            f.write('echo "스냅 정리 완료: $(date)"\n')
            f.write('echo "디스크 사용량:"\n')
            f.write('df -h\n')
        
        # 스크립트 실행 권한 부여
        os.chmod(snap_cleanup_script, 0o755)
        
        logger.info(f'스냅 정리 스크립트가 생성되었습니다: {snap_cleanup_script}')
        logger.info('관리자 권한으로 다음 명령어를 실행하세요: sudo ./snap_cleanup.sh')
        
        return True
    except Exception as e:
        logger.error(f'스냅 정리 스크립트 생성 오류: {e}')
        return False

if __name__ == '__main__':
    if create_snap_cleanup_script():
        logger.info('스크립트 생성 성공!')
    else:
        logger.error('스크립트 생성 실패') 