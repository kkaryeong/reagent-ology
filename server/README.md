
# Reagent Server (FastAPI)

NFC 태그로 여는 시약 페이지 ↔ RS232 저울 측정값을 반영해 **현재 잔량과 사용기록을 관리**하는 API 서버입니다.  
단위는 **그램(g)** 기준으로만 사용합니다. (밀도 입력 시 프론트에서 ml 변환 표시 가능)

## 구성
- **/api/reagents/**: 시약 등록/조회
- **/api/measure**: 측정값(gross_g, g 단위) 반영 → 잔량 업데이트 + 로그 적재
- **/api/queue**: 폰에서 NFC 스캔 시 측정 작업을 큐에 추가
- **/api/queue/next**: PC 에이전트가 작업을 선점
- **/api/queue/{id}/done**: 작업 완료 처리
- **/api/sse/{tag_uid}**: 해당 시약의 실시간 갱신 알림(SSE)

## 설치 & 실행
```bash
# (권장) 가상환경 생성 후
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## CORS
`main.py` 상단의 `ALLOWED_ORIGINS` 에 Netlify 도메인 등을 추가하세요.

## 초기 데이터 입력(예시)
```bash
curl -X POST "http://127.0.0.1:8000/api/reagents/upsert" \
  -H "Content-Type: application/json" \
  -d '{"name":"Acetone","tag_uid":"04A224112233","density_g_per_ml":0.79,"tare_g":120,"unit":"ml","current_net_g":350}'
```

## 프런트 페이지에서 사용(예)
- `GET /api/reagents/by-tag/{tag_uid}`
- `GET /api/reagents/{id}/logs?limit=50`
- NFC 링크 예: `https://reagent-ology.netlify.app/r/<tag_uid>` 로 접속 시,
  페이지 로드시 `POST /api/queue` 호출 → PC 에이전트가 측정 후 `measure` 반영 → SSE로 실시간 갱신.
```

