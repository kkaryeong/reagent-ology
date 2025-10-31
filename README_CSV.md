# Reagent-ology (완전 CSV 기반 버전)

**고등학생 1회성 프로젝트용 - SQL 없이 CSV만 사용!**

실험실 시약 관리 데모 애플리케이션입니다. CSV 파일만으로 간단하게 데이터를 관리하며, 별도의 데이터베이스 설치나 복잡한 설정이 필요 없습니다.

## ✨ 특징

- ✅ **SQL 불필요**: SQLite, SQLAlchemy 제거 → CSV 파일만 사용
- ✅ **간단한 구조**: Excel에서도 편집 가능한 CSV 파일
- ✅ **쉬운 백업**: 파일 복사만으로 백업 완료
- ✅ **배포 용이**: Python만 있으면 어디서든 실행 가능

## 📁 데이터 파일 구조

모든 데이터는 `data/` 폴더의 CSV 파일에 저장됩니다:

```
reagent-ology/
├── data/
│   ├── reagents.csv          # 시약 재고 정보
│   ├── usage_logs.csv        # 사용/폐기/측정 이력
│   └── autocomplete.csv      # 자동완성 DB
```

### reagents.csv 구조
```csv
id,slug,name,formula,cas,location,storage,expiry,hazard,ghs,disposal,density,volume_ml,nfc_tag_uid,scale_device,quantity,used,discarded,created_at,updated_at
1,sodium-chloride,Sodium Chloride,NaCl,7647-14-5,Shelf A,RT,,,Irritant,일반폐기물,2.165,,,1000,0,0,2025-01-15T10:00:00,2025-01-15T10:00:00
```

### usage_logs.csv 구조
```csv
id,reagent_id,prev_qty,new_qty,delta,source,note,created_at
1,1,1000,990,-10,use,Experiment A,2025-01-15T11:00:00
```

## 🚀 설치 및 실행

### 1) 의존성 설치
```bash
cd /Users/ppofluxus/Documents/Regentology/reagent-ology
pip install -r requirements.txt
```

**필요한 패키지 (SQL 제거됨):**
- fastapi
- uvicorn
- httpx
- pydantic

### 2) 백엔드 실행
```bash
# reagent-ology 폴더에서 실행
uvicorn backend.main:app --reload

# 또는
python -m uvicorn backend.main:app --reload
```

서버 주소: http://127.0.0.1:8000

### 3) 프런트엔드 실행
```bash
# 정적 파일 서버
python -m http.server 5510
```

브라우저에서 열기: http://127.0.0.1:5510/reagent_ology.html

## 📝 주요 기능

### 시약 관리
- ✅ 시약 등록/수정/삭제
- ✅ 이름 자동완성 (로컬 CSV + PubChem)
- ✅ Formula, CAS, Storage, GHS, Disposal, Density 자동 입력
- ✅ 수량 관리 (g 단위)
- ✅ 밀도 기반 부피(mL) 자동 계산

### 사용 이력 추적
- ✅ 사용량 기록
- ✅ 폐기량 기록
- ✅ 저울 측정 기록
- ✅ 시약별 상세 이력 조회

### 하드웨어 연동 준비
- ✅ NFC Tag UID 필드
- ✅ Scale Device 필드
- ✅ NFC 태그로 시약 자동 조회
- ✅ 저울 측정값 자동 반영

## 🔧 CSV 파일 직접 편집

### Excel/Numbers로 편집하기
1. `data/reagents.csv` 또는 `data/autocomplete.csv` 열기
2. 데이터 수정
3. UTF-8 인코딩으로 저장
4. 브라우저 새로고침 → 즉시 반영!

### 백업하기
```bash
# 전체 data 폴더 백업
cp -r data/ data_backup_$(date +%Y%m%d)/

# 특정 파일만 백업
cp data/reagents.csv data/reagents_backup_$(date +%Y%m%d).csv
```

## 🎯 사용 예시

### 1. 새 시약 등록
- 웹 UI: `#/add` 페이지에서 등록
- 이름 입력 시 자동완성으로 Formula, CAS, Density 등 자동 입력
- 저장 버튼 클릭 → `data/reagents.csv`에 즉시 저장

### 2. 시약 사용 기록
- `#/inventory`에서 시약 선택
- "Use -10" 버튼 클릭
- 수량 자동 감소 + 사용량 누적
- `data/usage_logs.csv`에 이력 자동 기록

### 3. 저울로 측정
- "Use with Scale" 버튼 클릭
- 측정한 무게(g) 입력
- 밀도가 설정되어 있으면 mL도 자동 계산
- NFC 태그가 등록되어 있으면 태그만으로 시약 인식 가능

### 4. 데이터 내보내기
- `#/inventory`에서 "CSV 내보내기" 버튼
- 전체 시약 정보를 Excel에서 열 수 있는 CSV로 저장

## 🛠️ API 엔드포인트

### 시약 관리
- `GET /api/reagents` - 전체 시약 목록
- `POST /api/reagents` - 새 시약 등록
- `GET /api/reagents/{id}` - 시약 상세 조회
- `PUT /api/reagents/{id}` - 시약 정보 수정
- `DELETE /api/reagents/{id}` - 시약 삭제

### 사용 기록
- `POST /api/reagents/{id}/use` - 사용량 기록
- `POST /api/reagents/{id}/discard` - 폐기량 기록
- `POST /api/reagents/{id}/measurement` - 저울 측정 기록
- `POST /api/measurements/weight` - NFC 태그로 측정 기록
- `GET /api/reagents/{id}/usage` - 사용 이력 조회

### 자동완성
- `GET /api/autocomplete?q=sodium` - 로컬 + PubChem 자동완성
- `GET /api/autocomplete/local?q=sodium` - 로컬만 자동완성
- `GET /api/autocomplete/local-db` - 자동완성 DB 전체 목록
- `POST /api/autocomplete/local-db` - 자동완성 항목 추가
- `DELETE /api/autocomplete/local-db/{name}` - 항목 삭제

## 📊 데이터 관리 팁

### CSV 파일이 없을 때
- 첫 실행 시 자동으로 생성됩니다
- 프런트에서 로그인 → 기본 샘플 데이터 자동 추가

### CSV 파일 손상 시
1. 백업에서 복원
2. 또는 파일 삭제 후 재시작 (빈 파일로 시작)

### 데이터 초기화
```bash
# 모든 데이터 삭제
rm data/reagents.csv data/usage_logs.csv

# 재시작하면 빈 파일로 시작
```

## 🔒 보안 주의사항

**현재 버전은 로컬 데모용입니다!**

- ⚠️ 로그인은 브라우저 localStorage 기반 (암호화 없음)
- ⚠️ 실제 운영 시 적절한 인증 시스템 필요
- ⚠️ 중요 데이터는 정기적으로 백업

## 🐛 문제 해결

### 포트 충돌
```bash
# 8000 포트가 사용 중이면
uvicorn backend.main:app --reload --port 8001

# 5510 포트가 사용 중이면
python -m http.server 5511
```

### CSV 파일 인코딩 오류
- Excel에서 저장 시 "CSV UTF-8 (쉼표로 구분)" 선택
- 또는 메모장에서 "UTF-8"로 저장

### 자동완성이 안 될 때
1. `data/autocomplete.csv` 파일 확인
2. 헤더가 올바른지 확인: `name,formula,synonyms,cas,storage,ghs,disposal,density`
3. 쌍따옴표로 감싼 필드에 세미콜론(;) 사용 확인

## 📚 추가 개발 아이디어

- [ ] CSV를 Google Sheets로 연동
- [ ] QR 코드 생성 및 스캔
- [ ] 만료일 임박 알림
- [ ] 사용 통계 그래프
- [ ] 모바일 앱 연동

## 📄 라이선스

고등학교 프로젝트용 데모 코드입니다. 자유롭게 수정 및 사용 가능합니다.

---

**💡 Tip**: CSV 파일을 Git으로 버전 관리하면 변경 이력을 추적할 수 있습니다!
