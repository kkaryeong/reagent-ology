# 저울 연동 웹 UI 테스트 가이드

## 🚀 서버 시작 방법

### 방법 1: 새 PowerShell 창에서 실행 (권장)

1. **새 PowerShell 창을 엽니다**
2. 다음 명령을 실행:

```powershell
cd C:\Users\ppofluxus\Documents\Regentology\reagent-ology
$env:PYTHONPATH = (Get-Location).Path
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

3. 서버가 시작되면 다음 메시지가 표시됩니다:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 방법 2: 배치 파일 사용

프로젝트 폴더에서 `start_server.bat` 파일을 더블클릭

---

## 🌐 웹 브라우저에서 테스트

서버가 실행되면:

1. **웹 브라우저 열기**
   - Chrome, Edge, Firefox 등
   
2. **HTML 파일 열기**
   ```
   파일 열기: C:\Users\ppofluxus\Documents\Regentology\reagent-ology\reagent_ology.html
   ```
   
   또는 파일 탐색기에서 `reagent_ology.html`을 더블클릭

---

## 🎯 저울 연동 테스트 단계

### Step 1: 로그인

- Username: `admin` (또는 원하는 이름)
- Password: `password` (또는 원하는 비밀번호)
- 처음이면 "Sign Up" 버튼으로 계정 생성

### Step 2: 저울 포트 확인

1. 상단 메뉴에서 **"연구실 보유 물질"** 클릭
2. 시약 목록에서 아무 시약이나 선택
3. **"Use with Scale"** 버튼 클릭
4. 모달 창이 나타남
5. **"포트 새로고침"** 버튼 클릭
6. 드롭다운에서 **"COM3 - USB Serial Port"** 확인

### Step 3: 무게 측정 테스트

#### 방법 A: 자동 측정
1. 저울 위에 물체를 올림 (현재 측정값: 15.16g)
2. 포트에서 **COM3** 선택
3. 메모 입력 (선택사항): "테스트 측정"
4. **"저울에서 읽기"** 버튼 클릭
5. 결과 확인:
   - 측정된 무게 표시
   - "측정 완료!" 메시지
   - 자동으로 DB 업데이트
6. 모달이 자동으로 닫힘
7. 시약 목록에서 업데이트된 무게 확인

#### 방법 B: 수동 입력
1. **"수동 입력"** 버튼 클릭
2. 무게 입력: `15.16`
3. 확인
4. DB 업데이트 확인

### Step 4: 결과 확인

1. **시약 목록 확인**
   - "연구실 보유 물질" 메뉴
   - 업데이트된 Qty 확인
   
2. **사용 기록 확인**
   - 시약 이름 클릭 (상세 페이지)
   - 하단 "사용 기록" 섹션
   - 측정 시각, 변화량, source 확인

---

## 📊 CSV 업로드 테스트

### Step 1: 측정값 CSV에 저장

1. 상단 메뉴에서 **"저울 CSV 업로드"** 클릭
2. **"실시간 측정값 저장"** 섹션:
   - NFC Tag UID: `NFC-ACE-001`
   - 무게 (g): `15.16`
   - 메모: `웹 UI 테스트`
   - 측정자: `본인 이름`
3. **"CSV에 저장"** 버튼 클릭
4. 성공 메시지 확인

### Step 2: CSV 파일 확인

파일 탐색기에서 확인:
```
C:\Users\ppofluxus\Documents\Regentology\reagent-ology\data\scale_measurements.csv
```

Excel이나 메모장으로 열어서 데이터 확인

### Step 3: CSV 파일 업로드

1. 같은 페이지에서 **"CSV 파일 업로드"** 섹션
2. **"파일 선택"** 버튼 클릭
3. 방금 생성된 `scale_measurements.csv` 파일 선택
4. **"업로드 및 처리"** 버튼 클릭
5. 처리 결과 확인:
   - 성공/실패 건수
   - 업데이트된 시약 목록
   - 에러 목록 (있는 경우)

---

## 🔧 문제 해결

### 서버가 시작되지 않을 때

**증상**: "대상 컴퓨터에서 연결을 거부했으므로..."

**해결**:
1. PowerShell 창에서 서버가 실행 중인지 확인
2. 포트 8000이 다른 프로그램에서 사용 중인지 확인:
   ```powershell
   netstat -ano | findstr :8000
   ```
3. 실행 중인 프로세스 종료 후 재시도

### 저울 연결 실패

**증상**: "Failed to connect to scale"

**해결**:
1. Device Manager에서 COM3 포트 확인
2. 저울 전원 및 USB 케이블 확인
3. 다른 프로그램이 포트를 사용 중인지 확인
4. 저울 재연결

### 포트 목록이 비어있음

**증상**: "사용 가능한 포트 없음"

**해결**:
1. pyserial 설치 확인:
   ```powershell
   pip install pyserial
   ```
2. 저울 USB 케이블 확인
3. 드라이버 설치 확인

---

## ✅ 성공 확인 체크리스트

- [ ] 서버 정상 시작 (http://127.0.0.1:8000)
- [ ] 웹 페이지 로그인 성공
- [ ] 저울 포트 목록에 COM3 표시
- [ ] "저울에서 읽기" 버튼으로 무게 측정 성공
- [ ] DB에 무게 업데이트 확인
- [ ] 사용 기록에 측정 이력 표시
- [ ] CSV 저장 기능 작동
- [ ] CSV 업로드 기능 작동

---

## 📞 추가 도움

문제가 계속되면 다음을 확인하세요:

1. **Python 버전**: 3.8 이상
2. **의존성 설치**: `pip install -r requirements.txt`
3. **저울 연결**: `python test_scale_connection.py`
4. **서버 로그**: PowerShell 창에서 에러 메시지 확인

---

**작성일**: 2025년 11월 5일  
**버전**: 1.0
