# 🧪 Reagent-ology 실행 가이드

## 📦 설치 요구사항

### 1. Python 3.8 이상
- Python 3.12 권장
- https://www.python.org/downloads/ 에서 다운로드

### 2. 필수 패키지 설치
```powershell
pip install fastapi uvicorn pyserial python-multipart httpx
```

또는 requirements.txt 사용:
```powershell
cd reagent-ology
pip install -r requirements.txt
```

## 🚀 실행 방법

### 방법 1: 배치 파일 실행 (가장 간단)
1. `START_REAGENT_OLOGY.bat` 파일을 **더블클릭**
2. 자동으로 서버가 시작되고 브라우저가 열립니다
3. 종료하려면 터미널 창에서 `Ctrl+C` 누르기

### 방법 2: Python 스크립트 실행
```powershell
cd reagent-ology
python run_app.py
```

### 방법 3: 수동 실행 (고급)
```powershell
cd reagent-ology
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
그 다음 브라우저에서 `reagent_ology.html` 파일 열기

## 🔧 문제 해결

### 서버가 시작되지 않을 때
1. Python이 설치되어 있는지 확인:
   ```powershell
   python --version
   ```

2. 필수 패키지가 설치되어 있는지 확인:
   ```powershell
   pip list | findstr "fastapi uvicorn pyserial"
   ```

3. 포트 8000이 사용 중인지 확인:
   ```powershell
   netstat -ano | findstr :8000
   ```
   
   사용 중이면 해당 프로세스 종료:
   ```powershell
   taskkill /PID <PID번호> /F
   ```

### 저울이 인식되지 않을 때
1. 저울 USB 케이블이 연결되어 있는지 확인
2. 장치 관리자에서 COM 포트 확인
3. 웹 페이지의 "저울 포트 선택"에서 올바른 포트 선택

### 브라우저가 자동으로 열리지 않을 때
수동으로 브라우저를 열고 다음 파일을 엽니다:
```
C:\Users\ppofluxus\Documents\Regentology\reagent-ology\reagent_ology.html
```

## 📱 주요 기능

### 1. 저울 자동 측정 (3초 안정화)
- "Use with Scale" 버튼 클릭
- 저울에 시약 올리기
- 3초 동안 무게가 일정하게 유지되면 자동 측정

### 2. CSV 업로드
- "저울 CSV 업로드" 메뉴
- CSV 파일 선택하여 일괄 업데이트

### 3. 자동완성 DB 관리
- "자동완성 DB 관리" 메뉴
- 자주 사용하는 시약 정보 추가/삭제

## 🌐 접속 주소

- **백엔드 API**: http://127.0.0.1:8000
- **API 문서**: http://127.0.0.1:8000/docs
- **웹 페이지**: 로컬 파일 (reagent_ology.html)

## 📊 데이터 저장 위치

모든 데이터는 CSV 파일로 저장됩니다:
- `data/reagents.csv` - 시약 목록
- `data/usage_logs.csv` - 사용 기록
- `data/scale_measurements.csv` - 저울 측정값
- `data/local_autocomplete.csv` - 자동완성 DB

## 🛑 서버 종료

터미널 창에서 `Ctrl+C` 키를 누르면 서버가 안전하게 종료됩니다.

## 💡 팁

1. **자동 시작**: 배치 파일을 바탕화면에 바로가기로 만들어두면 편리합니다
2. **데이터 백업**: 정기적으로 `data/` 폴더를 백업하세요
3. **CSV 편집**: Excel이나 메모장으로 직접 CSV 파일을 편집할 수도 있습니다

## 📞 문의

문제가 발생하면 다음을 확인하세요:
1. 터미널에 출력된 오류 메시지
2. 브라우저 개발자 도구의 콘솔 (F12)
3. 서버 로그 메시지
