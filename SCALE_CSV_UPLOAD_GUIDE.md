# 저울 측정값 CSV 업로드 기능 가이드

## 📋 개요

저울에서 측정한 무게 데이터를 CSV 파일로 관리하고, 일괄적으로 시약 데이터베이스에 반영하는 기능입니다.

## 🔄 워크플로우

### 방법 1: 실시간 측정 → CSV 저장 → 일괄 업로드

```
1. 저울로 시약 무게 측정
   ↓
2. 웹 UI에서 "실시간 측정값 저장" 사용
   - NFC Tag UID 입력
   - 측정한 무게 입력
   - 메모 및 측정자 입력(선택)
   ↓
3. data/scale_measurements.csv 파일에 자동 저장
   ↓
4. 측정 완료 후 "CSV 업로드" 버튼으로 일괄 처리
   ↓
5. DB 업데이트 완료 및 결과 확인
```

### 방법 2: 외부 CSV 파일 직접 업로드

```
1. Excel이나 저울 소프트웨어에서 CSV 파일 생성
   ↓
2. 지정된 형식으로 데이터 입력
   ↓
3. 웹 UI에서 파일 선택 및 업로드
   ↓
4. 자동 처리 및 DB 업데이트
```

## 📄 CSV 파일 형식

### 필수 헤더
```csv
nfc_tag_uid,reagent_id,reagent_name,measured_weight,timestamp,note,operator
```

### 필드 설명

| 필드 | 필수/선택 | 설명 | 예시 |
|------|----------|------|------|
| nfc_tag_uid | 선택* | NFC 태그 UID | NFC-ACE-001 |
| reagent_id | 선택* | 시약 DB ID | 1 |
| reagent_name | 선택* | 시약 이름 | 아세톤 |
| measured_weight | **필수** | 측정 무게 (g) | 485.5 |
| timestamp | 선택 | 측정 시각 | 2025-11-05T14:30:00 |
| note | 선택 | 메모 | 정기측정 |
| operator | 선택 | 측정자 | 김철수 |

*nfc_tag_uid, reagent_id, reagent_name 중 **최소 하나**는 필수 (시약 식별용)

### 샘플 데이터

```csv
nfc_tag_uid,reagent_id,reagent_name,measured_weight,timestamp,note,operator
NFC-ACE-001,1,아세톤,485.5,2025-11-05T14:30:00,정기측정,김철수
NFC-ETH-001,2,Ethanol,920.3,2025-11-05T14:31:00,사용후측정,김철수
,3,Methanol,275.8,2025-11-05T14:32:00,,이영희
NFC-NACL-001,,,1050.0,,,박영수
```

## 🔌 API 엔드포인트

### 1. 측정값 CSV 파일에 저장

```http
POST /api/scale/save-measurement?nfc_tag_uid=NFC-ACE-001&measured_weight=485.5&note=정기측정&operator=김철수
```

**설명**: 측정값을 `data/scale_measurements.csv` 파일에 즉시 저장 (DB에는 반영하지 않음)

**응답**:
```json
{
  "success": true,
  "message": "측정값이 CSV 파일에 저장되었습니다",
  "file": "C:\\...\\data\\scale_measurements.csv",
  "data": {
    "nfc_tag_uid": "NFC-ACE-001",
    "measured_weight": 485.5,
    "timestamp": "2025-11-05T14:30:00",
    "note": "정기측정",
    "operator": "김철수"
  }
}
```

### 2. CSV 파일 업로드 및 DB 업데이트

```http
POST /api/scale/upload-measurements
Content-Type: multipart/form-data

file: scale_measurements.csv
```

**설명**: CSV 파일을 업로드하여 시약 수량을 일괄 업데이트하고 usage_logs에 기록

**응답**:
```json
{
  "message": "CSV 파일 처리 완료: 3건 성공, 0건 실패",
  "results": {
    "total": 3,
    "success": 3,
    "failed": 0,
    "errors": [],
    "updates": [
      {
        "row": 2,
        "identifier": "NFC:NFC-ACE-001",
        "reagent_name": "아세톤",
        "previous_quantity": 500.0,
        "new_quantity": 485.5,
        "delta": -14.5
      },
      {
        "row": 3,
        "identifier": "NFC:NFC-ETH-001",
        "reagent_name": "Ethanol",
        "previous_quantity": 1000.0,
        "new_quantity": 920.3,
        "delta": -79.7
      }
    ]
  },
  "timestamp": "2025-11-05T14:35:00"
}
```

## 💻 웹 UI 사용법

### 1. 저울 CSV 업로드 메뉴 접속

1. 웹 브라우저에서 `index.html` 열기
2. 상단 네비게이션에서 **"저울 CSV 업로드"** 클릭

### 2. 실시간 측정값 저장

1. "실시간 측정값 저장" 섹션에서:
   - NFC Tag UID 입력 (예: NFC-ACE-001)
   - 저울에서 측정한 무게 입력 (그램 단위)
   - 메모 및 측정자 입력 (선택)
2. **"CSV에 저장"** 버튼 클릭
3. 성공 메시지 확인

### 3. CSV 파일 일괄 업로드

1. "CSV 파일 업로드" 섹션에서:
   - **파일 선택** 버튼 클릭
   - CSV 파일 선택 (UTF-8 인코딩)
2. **"업로드 및 처리"** 버튼 클릭
3. 처리 결과 확인:
   - 성공/실패 건수
   - 업데이트된 시약 목록
   - 에러 목록 (있는 경우)

### 4. 샘플 CSV 다운로드

- **"샘플 CSV 다운로드"** 버튼 클릭
- 다운로드된 파일을 참고하여 CSV 파일 작성

## 🧪 테스트 방법

### Python 스크립트로 테스트

```bash
cd reagent-ology
python test_csv_upload.py
```

### 수동 테스트

1. 서버 실행:
```bash
start_server.bat
```

2. 샘플 CSV 파일 확인:
```
data/scale_measurements_sample.csv
```

3. Postman이나 curl로 API 테스트:
```bash
# 측정값 저장
curl -X POST "http://127.0.0.1:8000/api/scale/save-measurement?nfc_tag_uid=NFC-TEST-001&measured_weight=123.45&note=테스트&operator=테스터"

# CSV 업로드
curl -X POST -F "file=@data/scale_measurements_sample.csv" "http://127.0.0.1:8000/api/scale/upload-measurements"
```

## 📊 처리 로직 상세

### 시약 찾기 우선순위

1. **NFC Tag UID** 매칭 (가장 우선)
2. **Reagent ID** 매칭
3. **Reagent Name** 매칭 (정확히 일치)

### 데이터 업데이트

1. 기존 `quantity` 값 저장
2. 새로운 `measured_weight`로 업데이트
3. `delta` 계산 (new - previous)
4. `usage_logs.csv`에 기록:
   - source: "csv_upload"
   - note: "CSV 업로드: {원본 note} (측정자: {operator}) [시간: {timestamp}]"

### 에러 처리

- **파일 형식 오류**: CSV 파일이 아니면 거부
- **인코딩 오류**: UTF-8 인코딩 권장
- **시약 미발견**: identifier 정보로 시약을 찾을 수 없는 경우
- **무게 값 오류**: 음수이거나 숫자가 아닌 경우
- **부분 성공**: 일부 행만 처리되더라도 성공한 행은 DB에 반영됨

## 📁 파일 위치

- **측정값 저장 파일**: `data/scale_measurements.csv`
- **시약 데이터**: `data/reagents.csv`
- **사용 기록**: `data/usage_logs.csv`
- **샘플 파일**: `data/scale_measurements_sample.csv`

## 🔐 보안 고려사항

1. **파일 크기 제한**: 대용량 파일 업로드 방지 (FastAPI default: 1MB)
2. **파일 형식 검증**: .csv 확장자만 허용
3. **데이터 검증**: 모든 필드 타입 및 범위 검증
4. **트랜잭션**: 에러 발생 시에도 성공한 행은 커밋

## 💡 활용 예시

### 예시 1: 일일 정기 점검

```csv
nfc_tag_uid,reagent_id,reagent_name,measured_weight,timestamp,note,operator
NFC-ACE-001,,,450.2,2025-11-05T09:00:00,일일점검,김철수
NFC-ETH-001,,,980.5,2025-11-05T09:01:00,일일점검,김철수
NFC-MEOH-001,,,285.3,2025-11-05T09:02:00,일일점검,김철수
```

### 예시 2: 실험 후 측정

```csv
nfc_tag_uid,reagent_id,reagent_name,measured_weight,timestamp,note,operator
NFC-ACE-001,,,435.8,2025-11-05T14:30:00,실험A후측정,이영희
NFC-ETH-001,,,920.0,2025-11-05T14:31:00,실험A후측정,이영희
```

### 예시 3: ID 기반 업데이트

```csv
nfc_tag_uid,reagent_id,reagent_name,measured_weight,timestamp,note,operator
,1,,420.5,,,박영수
,2,,900.2,,,박영수
,3,,260.1,,,박영수
```

## ❓ FAQ

**Q: CSV 파일을 Excel에서 만들어도 되나요?**  
A: 네, Excel에서 작성 후 "CSV UTF-8 (쉼표로 분리)"로 저장하세요.

**Q: 여러 시약을 한 번에 업데이트할 수 있나요?**  
A: 네, CSV 파일에 여러 행을 작성하면 한 번에 처리됩니다.

**Q: 일부 행에서 에러가 나면 어떻게 되나요?**  
A: 에러가 난 행은 건너뛰고, 성공한 행만 DB에 반영됩니다. 처리 결과에서 에러 목록을 확인할 수 있습니다.

**Q: 저울에서 직접 CSV를 내보낼 수 있나요?**  
A: 저울 모델에 따라 다릅니다. CSV export 기능이 있다면 데이터를 변환하여 사용할 수 있습니다.

**Q: NFC 태그가 없는 시약은 어떻게 하나요?**  
A: reagent_id나 reagent_name으로 식별할 수 있습니다.

## 🚀 향후 개선 사항

1. ✅ CSV 템플릿 다운로드 기능
2. ⏳ Excel 파일 직접 업로드 지원
3. ⏳ 자동 저울 연동 (시리얼 포트 직접 읽기)
4. ⏳ 측정 이력 그래프 시각화
5. ⏳ 예약 측정 (특정 시간마다 자동 측정)

---

**문서 버전**: 1.0  
**작성일**: 2025년 11월 5일  
**최종 수정**: 2025년 11월 5일
