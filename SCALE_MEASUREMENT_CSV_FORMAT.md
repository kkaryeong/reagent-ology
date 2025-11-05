# 저울 측정값 CSV 파일 형식 정의

## 1. 단일 측정 CSV 형식 (scale_measurements.csv)

### 형식 A: NFC 태그 기반
```csv
nfc_tag_uid,measured_weight,timestamp,note
NFC-ACE-001,485.5,2025-11-05T14:30:00,정기측정
NFC-ETH-001,920.3,2025-11-05T14:31:00,사용후측정
NFC-MEOH-001,275.8,2025-11-05T14:32:00,
```

### 형식 B: 시약 이름 기반
```csv
reagent_name,measured_weight,timestamp,note
아세톤,485.5,2025-11-05T14:30:00,정기측정
Ethanol,920.3,2025-11-05T14:31:00,사용후측정
Methanol,275.8,2025-11-05T14:32:00,
```

### 형식 C: 시약 ID 기반
```csv
reagent_id,measured_weight,timestamp,note
1,485.5,2025-11-05T14:30:00,정기측정
2,920.3,2025-11-05T14:31:00,사용후측정
3,275.8,2025-11-05T14:32:00,
```

## 2. 배치 측정 CSV 형식 (권장)

모든 식별 방법을 지원하는 통합 형식:
```csv
nfc_tag_uid,reagent_id,reagent_name,measured_weight,timestamp,note,operator
NFC-ACE-001,1,아세톤,485.5,2025-11-05T14:30:00,정기측정,김철수
NFC-ETH-001,2,Ethanol,920.3,2025-11-05T14:31:00,사용후측정,김철수
,3,Methanol,275.8,2025-11-05T14:32:00,,김철수
```

## 3. 자동 저울 연동 CSV 형식

저울이 자동으로 생성하는 형식 (변환 필요):
```csv
Date,Time,Weight(g),Unit,Status
2025-11-05,14:30:00,485.5,g,Stable
2025-11-05,14:31:00,920.3,g,Stable
2025-11-05,14:32:00,275.8,g,Stable
```

## 필드 설명

| 필드 | 필수 | 설명 |
|------|------|------|
| nfc_tag_uid | 선택* | NFC 태그 UID (예: NFC-ACE-001) |
| reagent_id | 선택* | 시약 DB의 ID |
| reagent_name | 선택* | 시약 이름 |
| measured_weight | 필수 | 측정된 무게 (그램) |
| timestamp | 선택 | 측정 시각 (ISO 8601 형식) |
| note | 선택 | 메모 |
| operator | 선택 | 측정자 |

*nfc_tag_uid, reagent_id, reagent_name 중 최소 1개는 필수

## 처리 로직

1. CSV 파일 읽기
2. 각 행에 대해:
   - nfc_tag_uid, reagent_id, reagent_name 중 하나로 시약 찾기
   - 기존 quantity와 measured_weight 비교
   - quantity 업데이트
   - usage_logs에 기록 추가
3. 처리 결과 반환 (성공/실패 건수, 에러 목록)
