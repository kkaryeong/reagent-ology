
import re, time, itertools, requests

# ====== 설정 ======
API_BASE = "http://127.0.0.1:8000"   # FastAPI 서버 주소
AGENT_NAME = "labpc-1"               # 에이전트 식별 이름

PORT = "COM3"        # 저울 연결 포트
BAUD = 9600
TIMEOUT = 1.0

# 안정 판정 파라미터
EPSILON = 0.002       # 허용 오차 (g)
ZERO_THRESHOLD = 0.002
MIN_STABLE_SEC = 2.5  # 안정 시간 (초)

# 시뮬레이터 (테스트용)
SIMULATE = False
SIM_LINES = ["12.000 g","12.001 g","12.000 g","12.000 g","12.000 g"]
SIM_INTERVAL_SEC = 0.2

LINE_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")

# ====== 함수 ======

def parse_weight(line: str):
    m = LINE_RE.search(line)
    return float(m.group(0)) if m else None

def serial_lines_stream():
    if SIMULATE:
        for line in itertools.cycle(SIM_LINES):
            yield line
            time.sleep(SIM_INTERVAL_SEC)
    else:
        import serial
        while True:
            try:
                with serial.Serial(PORT, BAUD, timeout=TIMEOUT) as ser:
                    print(f"[INFO] Serial opened: {PORT}@{BAUD}")
                    while True:
                        raw = ser.readline()
                        if not raw:
                            continue
                        yield raw.decode(errors="ignore").strip()
            except Exception as e:
                print(f"[WARN] Serial error: {e}. 3초 후 재시도")
                time.sleep(3)

def claim_next():
    r = requests.post(f"{API_BASE}/api/queue/next", params={"agent": AGENT_NAME}, timeout=10)
    r.raise_for_status()
    j = r.json().get("job")
    return (j["id"], j["tag_uid"]) if j else (None, None)

def post_measure(tag_uid, gross_g):
    r = requests.post(f"{API_BASE}/api/measure", json={"tag_uid": tag_uid, "gross_weight_g": gross_g}, timeout=10)
    r.raise_for_status()
    return r.json()

def finish_job(job_id):
    r = requests.post(f"{API_BASE}/api/queue/{job_id}/done", timeout=10)
    r.raise_for_status()

def measure_once():
    candidate=None; t0=None
    for line in serial_lines_stream():
        w = parse_weight(line)
        if w is None: continue
        gross_g = w
        if abs(gross_g) <= ZERO_THRESHOLD:
            candidate=None; t0=None; continue
        now=time.time()
        if candidate is None or abs(gross_g - candidate) > EPSILON:
            candidate=gross_g; t0=now; continue
        if now - t0 >= MIN_STABLE_SEC:
            return gross_g

def main():
    print("=== RS232 → Server Agent ===")
    while True:
        job_id, tag_uid = claim_next()
        if not job_id:
            time.sleep(1)
            continue
        print(f"[JOB {job_id}] tag={tag_uid} 측정 시작")
        gross = measure_once()
        print(f"[JOB {job_id}] 안정값 {gross:.3f} g → 서버 전송 중...")
        res = post_measure(tag_uid, gross)
        finish_job(job_id)
        print(f"[JOB {job_id}] 완료 ✓  ({res['reagent']['current_net_g']:.3f} g 남음)")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] 종료")
