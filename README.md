Reagent-ology

실험실 시약 관리 데모 애플리케이션입니다. 로컬 FastAPI 백엔드와 정적 HTML 프런트로 동작하며, 이름 자동완성은 로컬 CSV DB를 우선 사용하고 필요 시 PubChem 제안으로 보강합니다.

## 요구사항
- macOS, zsh 기준 안내 (다른 OS도 Python 3.9+면 동일하게 동작)
- Python 3.9+ (권장: 가상환경 사용)

## 설치
```zsh
# 1) 프로젝트 루트로 이동
cd /Users/USERNAME/Documents/Regentology/reagent-ology

# 2) (선택) 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 3) 의존성 설치
pip install -r requirements.txt
```

## 실행
### 1) 백엔드(FastAPI)
아래 중 편한 방법을 선택하세요.

```zsh
# 방법 A: 현재 디렉토리(reagent-ology)에서 실행
uvicorn backend.main:app --reload

# 방법 B: python -m 형태로 실행(가상환경 사용 시)
python -m uvicorn backend.main:app --reload
```
- 서버: http://127.0.0.1:8000
- 헬스 체크: http://127.0.0.1:8000/api/health

### 2) 프런트엔드(정적 서버)
```zsh
# 배경 이미지 등 정적 파일 포함, 현재 디렉토리를 그대로 서빙
python -m http.server 5500 --directory .
```
- 접속 URL: http://127.0.0.1:5500/reagent_ology.html
  - 각 페이지에 고유 URL을 부여하는 해시 라우팅 사용 예: `#/add`, `#/inventory`, `#/auto-db`
  - 예: http://127.0.0.1:5500/reagent_ology.html#/add

## 기본 기능
- 시약 등록/수정/삭제, 수량 사용/폐기/저울 측정 기록
- 시약별 밀도(g/mL), NFC Tag UID, 저울/시리얼 포트 정보를 저장해 하드웨어 연동 준비
- 상세 페이지에서 사용 이력 확인
- 이름 자동완성: 로컬 CSV → 부족 시 PubChem으로 보강

## 밀도 및 저울 연동
- `Density (g/mL)` 입력 시, 저울에서 측정한 무게(g)를 자동으로 mL로 환산해 DB에 저장합니다.
- `NFC Tag UID`와 `Scale Device / Port` 필드로 각 시약을 하드웨어와 매핑할 수 있습니다.
- 저울 측정은 두 가지 방식으로 기록할 수 있습니다.
  1. 프런트엔드 `Use with Scale` 버튼 → `/api/reagents/{slug}/measurement`에 `measured_mass` 전달
  2. 하드웨어 연동 시 `/api/measurements/weight`에 `{ "nfc_tag_uid": "...", "measured_mass": 123.4 }` 형태로 호출
     - 백엔드가 NFC 태그에 해당하는 시약을 찾아 무게/부피를 갱신하고 사용 로그를 남깁니다.
  - 밀도가 지정되지 않은 경우 mL 환산 없이 무게만 갱신되며, 프런트 UI에서 경고합니다.

## 자동완성 DB 관리(CSV)
- 경로: `data/autocomplete.csv`
- 스키마: `name,formula,synonyms`
  - 예: `Sodium Chloride,NaCl,"Salt;Table Salt"`
- CSV를 수정하면 별도 재시작 없이도 즉시 반영됩니다(요청 시마다 CSV를 읽어옵니다).

### 관리자 UI로 관리
- 이동: http://127.0.0.1:5500/reagent%20ology.html#/auto-db
- 가능: 목록 조회, 항목 추가(Name/Formula 필수, Synonyms는 `;`로 구분), 삭제

### API로 관리
```zsh
# 전체 목록
curl -sS "http://127.0.0.1:8000/api/autocomplete/local-db"

# 추가
curl -sS -X POST "http://127.0.0.1:8000/api/autocomplete/local-db" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Calcium Carbonate","formula":"CaCO3","synonyms":["Calcite","Limestone"]}'

# 수정(이름 변경 포함)
curl -sS -X PUT "http://127.0.0.1:8000/api/autocomplete/local-db/Calcium%20Carbonate" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Calcium Carbonate","formula":"CaCO3","synonyms":["Chalk"]}'

# 삭제
curl -sS -X DELETE "http://127.0.0.1:8000/api/autocomplete/local-db/Calcium%20Carbonate" -i
```

## 프런트 동작 개요
- 저장/수정/사용/폐기/측정/삭제는 모두 백엔드 DB(SQLite)에 즉시 반영됩니다.
- 자동완성은 `/api/autocomplete/local`로 로컬 CSV 제안을 우선 가져오고, 부족할 때 `/api/autocomplete`로 PubChem 제안을 병합합니다.
- “Sodium” 입력 → Sodium 계열 추천, “Sodium Chloride” 선택 시 Formula가 자동으로 `NaCl`로 채워짐.

## 문제 해결
- 5500/8000 포트 충돌: 다른 프로세스 종료 후 재실행하거나 포트를 변경하세요.
- CORS 문제: 기본적으로 FastAPI에서 모든 오리진 허용(CORSMiddleware)으로 설정되어 있습니다.
- 네트워크 제한 환경: 로컬 CSV 자동완성만으로도 동작합니다(외부 호출 실패 시 무시).

## 디렉토리 구조(요약)
```
reagent-ology/
├── backend/
│   ├── main.py              # FastAPI 엔드포인트
│   ├── localdb.py           # CSV 기반 자동완성 DB + CRUD + 검색
│   ├── models.py, schemas.py, utils.py, database.py
├── data/
│   └── autocomplete.csv     # 자동완성 DB CSV
├── requirements.txt
├── reagent_ology.html       # 프런트엔드(정적, 배포용)
└── reagent_ology_edit.html  # 편집 검토용(동일 내용 미러)
```

## 라이선스
- 데모 목적의 코드로 제공됩니다. 실제 운영 시 보안/인증/권한/로그 정책을 반영하세요.
# reagent-ology
