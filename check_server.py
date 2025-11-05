"""간단한 서버 상태 체크 및 재시도 스크립트"""
import requests
import time
import sys

API_BASE = "http://127.0.0.1:8000"

print("FastAPI 서버 연결 대기 중...")
print("서버 주소:", API_BASE)

for i in range(30):  # 30초 동안 시도
    try:
        response = requests.get(f"{API_BASE}/api/reagents", timeout=2)
        if response.status_code in [200, 404, 422]:
            print(f"\n✅ 서버 연결 성공! (시도 {i+1})")
            print(f"서버가 {API_BASE} 에서 실행 중입니다.")
            sys.exit(0)
    except:
        print(f".", end="", flush=True)
        time.sleep(1)

print("\n\n❌ 서버에 연결할 수 없습니다.")
print("\n다음 명령으로 서버를 시작하세요:")
print("  cd reagent-ology")
print("  $env:PYTHONPATH=(Get-Location).Path")
print("  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
sys.exit(1)
