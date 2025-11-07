# Reagent-ology 프로젝트 현황 보고서

## 📋 프로젝트 개요
**화학약품 관리 데이터베이스 시스템**
- NFC 태그 기반 화학약품 식별 및 관리
- USB 저울 연동을 통한 자동 무게 측정 및 재고 관리
- CSV 기반 간단한 데이터베이스 구조

---

## 🏗️ 프로젝트 구조

```
reagent-ology/
├── backend/                    # 백엔드 서버
│   ├── main.py                # FastAPI 메인 애플리케이션
│   ├── schemas.py             # Pydantic 데이터 모델
│   ├── csvdb.py               # CSV 데이터베이스 관리
│   ├── localdb.py             # 로컬 자동완성 DB
│   ├── scale_reader.py        # 🆕 USB 저울 통신 모듈
│   └── utils.py               # 유틸리티 함수
│
├── data/                       # 데이터 저장소 (CSV)
│   ├── reagents.csv           # 시약 정보 (8개 등록됨)
│   ├── usage_logs.csv         # 사용 기록
│   └── autocomplete.csv       # 자동완성 데이터
│
├── index.html                 # 프론트엔드 UI (renamed from reagent_ology.html)
├── requirements.txt           # Python 의존성 (pyserial 포함)
├── start_server.bat           # 🆕 서버 시작 스크립트
├── test_scale_connection.py   # 🆕 저울 연결 테스트
└── test_scale_api.py          # 🆕 저울 API 테스트

```

---

## ✅ 구현 완료된 기능

### 1. **데이터베이스 (CSV 기반)** ✅
- ✅ 시약 정보 저장: `reagents.csv`
  - 8개의 시약 등록됨 (아세톤, 에탄올, 메탄올, 염화나트륨 등)
  - 필드: id, slug, name, formula, cas, location, storage, expiry, hazard, ghs, disposal, density, volume_ml, nfc_tag_uid, scale_device, quantity, used, discarded
- ✅ 사용 기록: `usage_logs.csv`
  - 시약 사용/폐기 이력 추적
- ✅ 자동완성 DB: `autocomplete.csv`

### 2. **프론트엔드 (HTML)** ✅
- ✅ 시약 목록 조회 및 검색
- ✅ 시약 추가/수정/삭제
- ✅ GHS 필터링 및 정렬 기능
- ✅ 시약 상세 정보 보기
- ✅ 사용/폐기 기록 관리
- ✅ CSV 내보내기
- ✅ NFC Tag UID 입력 필드 제공
- ✅ Scale Device 필드 제공
- ✅ "Use with Scale" 버튼 (저울로 무게 측정)

### 3. **백엔드 API (FastAPI)** ✅
#### 기본 CRUD API
- ✅ `GET /api/reagents` - 시약 목록 조회
- ✅ `POST /api/reagents` - 새 시약 등록
- ✅ `GET /api/reagents/{slug}` - 시약 상세 조회
- ✅ `PUT /api/reagents/{slug}` - 시약 정보 수정
- ✅ `DELETE /api/reagents/{slug}` - 시약 삭제
- ✅ `POST /api/reagents/{slug}/use` - 시약 사용 기록
- ✅ `POST /api/reagents/{slug}/discard` - 시약 폐기 기록
- ✅ `POST /api/reagents/{slug}/measurement` - 수동 무게 측정

#### 🆕 저울 연동 API (신규 추가)
- ✅ `GET /api/scale/ports` - 연결된 저울 포트 목록
- ✅ `GET /api/scale/weight` - 저울에서 현재 무게 읽기
- ✅ `POST /api/scale/tare` - 저울 영점 조정
- ✅ `POST /api/reagents/{id}/measure-weight` - 저울로 시약 무게 측정 및 DB 저장

### 4. **USB 저울 연동** 🆕 ✅
- ✅ `backend/scale_reader.py` 모듈 구현
  - 시리얼 포트 자동 감지
  - 다양한 저울 프로토콜 지원
  - 안정된 무게 읽기 (stability check)
  - Tare(영점 조정) 기능
  - 에러 처리 및 타임아웃 관리
- ✅ COM3 포트 저울 연결 확인 완료
- ✅ 무게 읽기 테스트 성공 (0.0g)

### 5. **NFC 태그 연동** ✅
- ✅ 각 시약에 `nfc_tag_uid` 필드 제공
- ✅ UI에서 NFC 태그 입력 가능
- ✅ 데이터베이스에 저장됨
- ✅ NFC 스캔 페이지 라우팅 (`#/r/<tag_uid>`)

---

## 🔄 현재 데이터 흐름

### 시나리오 1: NFC 태그로 시약 조회 후 저울로 무게 측정
```
1. 사용자가 NFC 태그를 스캔
   ↓
2. URL: #/r/{nfc_tag_uid} 접근
   ↓
3. 프론트엔드: nfc_tag_uid로 시약 검색
   ↓
4. API: GET /api/reagents?nfc_tag_uid={uid}
   ↓
5. 시약 정보 표시
   ↓
6. 사용자가 "저울로 측정" 버튼 클릭
   ↓
7. API: POST /api/reagents/{id}/measure-weight?port=COM3
   ↓
8. 백엔드: ScaleReader로 COM3에서 무게 읽기
   ↓
9. 백엔드: reagents.csv 업데이트 (quantity)
   ↓
10. 백엔드: usage_logs.csv에 측정 기록
   ↓
11. 프론트엔드: 업데이트된 정보 표시
```

### 시나리오 2: 수동으로 시약 선택 후 무게 측정
```
1. 사용자가 시약 목록에서 시약 선택
   ↓
2. "Use with Scale" 버튼 클릭
   ↓
3. JavaScript: useWithScale(reagent) 함수 호출
   ↓
4. (현재) 프롬프트로 무게 입력 요청
   ↓
5. API: POST /api/reagents/{slug}/measurement
   ↓
6. 데이터베이스 업데이트
```

---

## 🚧 개선이 필요한 부분

### 1. **NFC 태그 자동 스캔 연동** ⚠️
**현재 상태:**
- NFC UID를 수동으로 입력하는 필드만 있음
- URL 라우팅(`#/r/{tag_uid}`)은 구현되어 있으나 실제 NFC 리더 연동 없음

**개선 방안:**
```javascript
// NFC Web API 사용 (Chrome/Android에서 지원)
async function scanNFC() {
    if ('NDEFReader' in window) {
        const reader = new NDEFReader();
        await reader.scan();
        reader.onreading = event => {
            const uid = event.serialNumber;
            location.hash = `#/r/${uid}`;
        };
    } else {
        alert('이 브라우저는 NFC를 지원하지 않습니다.');
    }
}
```

### 2. **저울 자동 측정 UI** ⚠️
**현재 상태:**
- `useWithScale()` 함수가 프롬프트로 무게를 입력받음
- 실제로는 API를 호출하여 저울에서 자동으로 읽어야 함

**개선 방안:**
```javascript
async function useWithScale(reagent) {
    try {
        // 저울에서 자동으로 무게 읽기
        const response = await fetch(
            `${API_BASE}/reagents/${reagent.id}/measure-weight?port=COM3`,
            { method: 'POST' }
        );
        const data = await response.json();
        
        alert(`측정 완료!\n무게: ${data.measured_weight}g\n이전: ${data.previous_quantity}g`);
        
        // 목록 새로고침
        await refreshReagents();
        renderList();
    } catch (err) {
        alert('저울 측정 실패: ' + err.message);
    }
}
```

### 3. **NFC UID로 시약 조회 API** ⚠️
**현재 상태:**
- NFC UID로 직접 조회하는 API 엔드포인트가 명시적으로 없음

**추가 필요:**
```python
# backend/main.py에 추가
@app.get("/api/reagents/by-nfc/{nfc_tag_uid}")
def get_reagent_by_nfc(nfc_tag_uid: str):
    """NFC 태그 UID로 시약 조회"""
    all_reagents = csvdb.list_all_reagents()
    for r in all_reagents:
        if r.get("nfc_tag_uid") == nfc_tag_uid:
            return schemas.ReagentOut(**r)
    raise HTTPException(status_code=404, detail="해당 NFC 태그의 시약을 찾을 수 없습니다")
```

### 4. **저울 포트 자동 감지 UI** 💡
**개선 방안:**
- 프론트엔드에서 `/api/scale/ports`를 호출하여 사용 가능한 포트 목록 표시
- 사용자가 포트를 선택하거나 자동으로 첫 번째 포트 사용

### 5. **실시간 무게 모니터링** 💡
**추가 기능 아이디어:**
- WebSocket을 사용하여 저울의 무게를 실시간으로 표시
- "안정화 대기 중..." 상태 표시
- 무게가 안정되면 자동으로 저장

---

## 📊 현재 데이터베이스 상태

### reagents.csv (8개 시약 등록)
1. 아세톤 (67-64-1) - 500g, NFC-ACE-001, RS232-1
2. Ethanol (ethanol-64-17-5) - 1000g, NFC-ETH-001, RS232-1
3. Methanol (methanol-67-56-1) - 300g, NFC-MEOH-001, RS232-2
4. Sodium Chloride (sodium-chloride-7647-14-5) - 1000g, NFC-NACL-001, RS232-3
5. Sulfuric Acid (sulfuric-acid-7664-93-9) - 100g
6. Sodium Sulfate (sodium-sulfate-7757-82-6) - 121g
7. Sodium Chloride (sodium-chloride-7647-14-5-1) - 1000g
8. 황산칼륨 (7647-01-0) - 1000g

### usage_logs.csv (2개 기록)
- 아세톤 사용 기록 2건

---

## 🔧 기술 스택

### 백엔드
- **FastAPI** 0.110.0 - 고성능 Python 웹 프레임워크
- **Pydantic** 2.7.4 - 데이터 검증
- **PySerial** 3.5 - USB 저울 시리얼 통신
- **Uvicorn** 0.29.0 - ASGI 서버

### 프론트엔드
- **HTML5** - 단일 페이지 애플리케이션
- **JavaScript (ES6+)** - API 호출 및 UI 로직
- **CSS3** - 스타일링

### 데이터베이스
- **CSV 파일** - 간단하고 이식성 좋은 데이터 저장

---

## 🚀 실행 방법

### 1. 의존성 설치
```bash
cd reagent-ology
pip install -r requirements.txt
```

### 2. 서버 실행
**방법 A: 배치 파일 사용 (권장)**
```bash
start_server.bat
```

**방법 B: 수동 실행**
```bash
set PYTHONPATH=%cd%
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 프론트엔드 열기
- 웹 브라우저에서 `index.html` 열기
- 또는 `http://127.0.0.1:8000` 접속 (정적 파일 서빙 설정 시)

### 4. 저울 연결 테스트
```bash
python test_scale_connection.py
python test_scale_api.py
```

---

## 🧪 테스트 시나리오

### 저울 연동 테스트
1. ✅ 저울을 COM3에 연결
2. ✅ `test_scale_connection.py` 실행 → 저울 감지 확인
3. ✅ 서버 실행
4. ⏳ `test_scale_api.py` 실행 → API 테스트
5. ⏳ 브라우저에서 "Use with Scale" 버튼 테스트

### NFC 태그 테스트 (수동)
1. ⏳ 시약에 NFC 태그 UID 입력 (예: NFC-TEST-001)
2. ⏳ URL에 `#/r/NFC-TEST-001` 입력
3. ⏳ 해당 시약 정보 표시 확인

---

## 📝 다음 단계 추천 사항

### 우선순위 높음 🔴
1. **NFC 자동 스캔 구현**
   - Web NFC API 또는 별도 NFC 리더 프로그램 연동
   
2. **저울 자동 측정 UI 완성**
   - `useWithScale()` 함수 수정
   - API 호출로 자동 측정
   
3. **NFC UID 조회 API 추가**
   - `/api/reagents/by-nfc/{uid}` 엔드포인트

### 우선순위 중간 🟡
4. **저울 포트 선택 UI**
   - 사용 가능한 포트 목록 표시
   - 포트 설정 저장
   
5. **에러 처리 개선**
   - 저울 연결 실패 시 사용자 친화적 메시지
   - 재시도 로직
   
6. **사용 로그 필터링**
   - 날짜별, 시약별 필터
   - 통계 대시보드

### 우선순위 낮음 🟢
7. **WebSocket 실시간 업데이트**
   - 무게 실시간 모니터링
   
8. **데이터 백업 기능**
   - CSV 자동 백업
   - 복원 기능
   
9. **사용자 권한 관리**
   - 관리자/사용자 역할
   - 수정 권한 제어

---

## 💾 백업 및 배포

### CSV 파일 백업
```bash
# data/ 폴더를 정기적으로 백업
xcopy data\*.csv backup\%date%\ /Y
```

### Netlify 배포 설정
- `netlify.toml` 파일 있음
- `netlify-build.sh` 빌드 스크립트 있음
- 정적 HTML만 배포 가능 (백엔드는 별도 호스팅 필요)

---

## 🎯 프로젝트 목표 달성도

| 기능 | 상태 | 완성도 |
|------|------|--------|
| 1. 프론트엔드 HTML | ✅ 완료 | 100% |
| 2. CSV 데이터베이스 | ✅ 완료 | 100% |
| 3. NFC 스티커 연동 | ⚠️ 부분 완료 | 70% |
| 4. 저울 연동 | ⚠️ 부분 완료 | 80% |
| 4.1 저울 통신 모듈 | ✅ 완료 | 100% |
| 4.2 저울 API | ✅ 완료 | 100% |
| 4.3 UI 자동 측정 | ⏳ 미완성 | 40% |
| **전체** | **⚠️ 진행 중** | **85%** |

---

## 📞 문제 해결

### 저울이 연결되지 않을 때
1. Device Manager에서 COM 포트 확인
2. 저울 전원 및 USB 케이블 확인
3. `test_scale_connection.py`로 포트 감지 테스트

### 서버가 시작되지 않을 때
1. `PYTHONPATH` 환경 변수 확인
2. 의존성 재설치: `pip install -r requirements.txt`
3. 포트 8000이 사용 중인지 확인

### NFC 태그가 인식되지 않을 때
1. 브라우저가 NFC Web API를 지원하는지 확인 (Chrome/Android)
2. HTTPS 환경에서만 작동 (localhost는 HTTP 허용)
3. NFC 리더 하드웨어 연결 확인

---

## 📄 라이선스 및 기여

- 프로젝트: Reagent-ology
- 용도: 고등학교 화학 실험실 시약 관리
- 기여자: [GitHub 저장소](https://github.com/kkaryeong/reagent-ology)

---

**작성일**: 2025년 11월 5일  
**버전**: 1.1.0 (저울 연동 추가)
