#!/bin/bash
# 스냅 패키지 정리 스크립트
set -e

echo "스냅 정리 시작: $(date)"

# 오래된 스냅 버전 정리
echo "스냅 버전 제한 설정 (최대 2개)..."
snap set system refresh.retain=2

echo "스냅 캐시 정리..."
rm -rf /var/lib/snapd/cache/*

echo "불필요한 스냅 로그 정리..."
find /var/log/journal -type f -name "*.journal" -mtime +7 -delete 2>/dev/null

# 스냅 리스트 확인
echo "현재 설치된 스냅 패키지:"
snap list

echo "스냅 정리 완료: $(date)"
echo "디스크 사용량:"
df -h
