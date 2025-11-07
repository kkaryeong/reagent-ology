"""
Reagent-ology 통합 실행 스크립트
백엔드 서버 시작 + 브라우저 자동 오픈
"""
import os
import sys
import time
import webbrowser
import socket
import subprocess
import platform
from pathlib import Path
import urllib.request
import urllib.error

def main():
    # 현재 디렉토리를 스크립트 위치로 설정
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    print("=" * 60)
    print("🧪 Reagent-ology 시작")
    print("=" * 60)
    print()
    
    # HTML 파일 경로 확인
    html_file = script_dir / "index.html"
    if not html_file.exists():
        print(f"❌ 오류: {html_file} 파일을 찾을 수 없습니다.")
        input("Enter 키를 눌러 종료...")
        sys.exit(1)
    
    # 백엔드 모듈 확인
    backend_dir = script_dir / "backend"
    if not backend_dir.exists():
        print(f"❌ 오류: backend 폴더를 찾을 수 없습니다.")
        input("Enter 키를 눌러 종료...")
        sys.exit(1)
    
    print("✅ 파일 확인 완료")
    print()
    
    # 필요한 패키지 확인
    try:
        import uvicorn
        import fastapi
        import serial
    except ImportError as e:
        print(f"❌ 필요한 패키지가 설치되지 않았습니다: {e}")
        print()
        print("다음 명령어로 설치하세요:")
        print("  pip install fastapi uvicorn pyserial python-multipart httpx")
        input("Enter 키를 눌러 종료...")
        sys.exit(1)
    
    print("✅ 필요한 패키지 확인 완료")
    print()
    
    # 서버 URL (고정 포트: 8000)
    server_url = "http://127.0.0.1:8000"
    # UI는 이제 FastAPI가 정적 서빙하므로 HTTP 경로로 오픈
    html_http_url = f"{server_url}/index.html"

    # mDNS(.local) 안내용 호스트명 구성 (ASCII가 아닌 이름이면 실사용이 제한될 수 있음)
    hostname = socket.gethostname().strip()
    mdns_host = f"{hostname}.local"
    mdns_origin = f"http://{mdns_host}:8000"

    # 사용자가 STICKER_ORIGIN 환경변수로 스티커용 호스트를 명시적으로 지정할 수 있음
    sticker_origin = os.environ.get("STICKER_ORIGIN", mdns_origin)
    sticker_ui_url = f"{sticker_origin}/index.html"

    # LAN IP 탐지 (mDNS 대안으로 안내)
    def get_lan_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"
    lan_ip = get_lan_ip()
    lan_origin = f"http://{lan_ip}:8000"
    lan_ui_url = f"{lan_origin}/index.html"
    
    print("🚀 FastAPI 서버 시작 중...")
    print(f"   서버 주소: {server_url}")
    print(f"   웹페이지: {html_http_url}")
    print()
    print("📌 스마트폰에서 접속(같은 Wi‑Fi)")
    print("   1) mDNS(.local) 권장 주소:")
    print(f"      {sticker_ui_url}")
    print("   2) 대안 — LAN IP 주소:")
    print(f"      {lan_ui_url}")
    print("   * Windows에서 .local(mDNS) 인식이 안 되면 'Bonjour Print Services' 설치를 권장합니다.")
    print("   * 또는 공유기에서 PC 고정 IP 예약 후 http://<고정IP>:8000 사용")
    print("   * macOS/Linux도 동일 URL 사용 가능 (이 스크립트와 start_server.sh 제공)")
    print()
    print("=" * 60)
    print("⚠️  서버를 종료하려면 Ctrl+C 를 누르세요")
    print("=" * 60)
    print()
    
    # 포트 사용중 확인 및 정리
    def get_pids_on_port(port: int) -> list[int]:
        system = platform.system().lower()
        pids: set[int] = set()
        try:
            if 'windows' in system:
                # Windows netstat 결과 파싱
                out = subprocess.check_output(
                    f'netstat -ano | findstr :{port}',
                    shell=True,
                    text=True,
                    stderr=subprocess.STDOUT,
                    encoding='utf-8',
                    errors='ignore',
                )
                for line in out.splitlines():
                    if 'LISTENING' in line.upper():
                        parts = line.split()
                        if parts:
                            try:
                                pid = int(parts[-1])
                                pids.add(pid)
                            except ValueError:
                                pass
            else:
                # macOS/Linux: lsof 사용
                out = subprocess.check_output(
                    ["bash", "-lc", f"lsof -t -i :{port} -sTCP:LISTEN"],
                    text=True,
                    stderr=subprocess.STDOUT,
                )
                for line in out.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        pids.add(int(line))
                    except ValueError:
                        pass
        except subprocess.CalledProcessError:
            return []
        return list(pids)

    def kill_pids(pids: list[int]):
        system = platform.system().lower()
        for pid in pids:
            try:
                if 'windows' in system:
                    subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False, capture_output=True)
                else:
                    subprocess.run(["kill", "-9", str(pid)], check=False, capture_output=True)
            except Exception:
                pass

    def is_server_ready(url: str) -> bool:
        try:
            urllib.request.urlopen(url + "/api/health", timeout=1)
            return True
        except Exception:
            return False

    # 이미 떠있는 서버가 있으면 재사용, 아니면 포트 정리 후 기동
    if is_server_ready(server_url):
        print("✅ 서버가 이미 실행 중입니다. 브라우저만 엽니다.")
    else:
        pids = get_pids_on_port(8000)
        if pids:
            print(f"⚠️  포트 8000 사용 중 감지: {pids} → 정리 시도")
            kill_pids(pids)
            time.sleep(0.5)

    # 브라우저 자동 오픈 (서버 준비 대기)
    def open_browser():
        
        # 서버가 준비될 때까지 대기 (최대 30초)
        for i in range(60):
            try:
                urllib.request.urlopen(f"{server_url}/api/health", timeout=1)
                print(f"✅ 서버 준비 완료!")
                break
            except (urllib.error.URLError, Exception):
                time.sleep(0.5)
        else:
            print("⚠️  서버 시작 대기 시간 초과")
        
        time.sleep(1)
        print(f"🌐 브라우저 열기: {html_http_url}")
        webbrowser.open(html_http_url)

        # 스티커 안내 파일 생성
        try:
            info_path = script_dir / "NFC_STICKER_BASE.txt"
            info = [
                "Reagent-ology NFC 스티커 안내",
                "",
                "스마트폰 스캔 시 열 URL (권장: mDNS .local)",
                f"{sticker_ui_url}#/r/UID",
                "",
                "예시:",
                f"{sticker_ui_url}#/r/04:E4:12:34:56",
                "",
                "(대안) LAN IP 기반:",
                f"{lan_ui_url}#/r/UID",
                f"{lan_ui_url}#/r/04:E4:12:34:56",
                "",
                "주의:",
                "- PC와 스마트폰은 같은 Wi‑Fi에 연결되어야 합니다.",
                "- .local 인식이 안 되면 공유기에서 PC IP를 고정 예약하고 고정 IP로 URL을 생성하세요.",
                "",
                "환경변수:",
                "- STICKER_ORIGIN 을 설정하면 임의의 호스트로 스티커 URL을 강제할 수 있습니다.",
                "  예) STICKER_ORIGIN=http://lab-nt.local:8000",
            ]
            info_path.write_text("\n".join(info), encoding="utf-8")
            print(f"📝 NFC 스티커 가이드 파일 생성: {info_path}")
        except Exception:
            pass
    
    import threading
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # 환경변수 설정
    os.environ['PYTHONPATH'] = str(script_dir)
    
    # Uvicorn 서버 시작
    try:
        # 안정적인 실행을 위해 기본값은 reload 비활성화
        # 개발 중 자동 리로드가 필요하면 환경변수 RELOAD=1 을 설정하세요.
        reload_flag = os.environ.get("RELOAD", "0") == "1"
        # 서버가 이미 떠 있으면 여기서 기동하지 않고 대기(브라우저만 오픈)
        if is_server_ready(server_url):
            # 준비 대기 스레드가 브라우저를 열 수 있도록 충분히 유지
            while True:
                time.sleep(3600)
        else:
            uvicorn.run(
                "backend.main:app",
                host="0.0.0.0",
                port=8000,
                reload=reload_flag,
                log_level="info"
            )
    except KeyboardInterrupt:
        print()
        print("=" * 60)
        print("🛑 서버 종료됨")
        print("=" * 60)
    except Exception as e:
        print(f"❌ 서버 오류: {e}")
        input("Enter 키를 눌러 종료...")
        sys.exit(1)

if __name__ == "__main__":
    main()
