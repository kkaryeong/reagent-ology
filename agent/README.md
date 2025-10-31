
# Reagent Scale Agent

RS232 저울 → FastAPI 서버 자동 업로드 에이전트

## 실행 방법
```bash
pip install -r requirements.txt
python scale_agent.py
```

## 동작
1. 서버 `/api/queue/next` 로 새로운 측정 요청(tag_uid) 확인
2. 저울에서 안정값(2.5초 이상 유지) 판정
3. `/api/measure` 로 결과 업로드
4. `/api/queue/{id}/done` 호출로 완료 처리

## 설정
- `API_BASE`: 서버 주소
- `PORT`, `BAUD`: 저울 통신 설정
- `EPSILON`, `MIN_STABLE_SEC`: 안정 판정 기준
- `SIMULATE=True` 로 테스트 가능
