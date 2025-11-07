"""Test script for CSV upload functionality"""
import requests
import json

API_BASE = "http://127.0.0.1:8000/api"

def test_save_measurement():
    """테스트 1: 측정값을 CSV 파일에 저장"""
    print("\n" + "="*60)
    print("테스트 1: 측정값 CSV 저장")
    print("="*60)
    
    url = f"{API_BASE}/scale/save-measurement"
    params = {
        "nfc_tag_uid": "NFC-TEST-001",
        "measured_weight": 123.45,
        "note": "테스트 측정",
        "operator": "테스트 사용자"
    }
    
    print(f"POST {url}")
    print(f"Parameters: {params}")
    
    try:
        response = requests.post(url, params=params)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 성공!\n")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"❌ 실패: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 에러: {e}")
        return False


def test_upload_csv():
    """테스트 2: CSV 파일 업로드 및 DB 업데이트"""
    print("\n" + "="*60)
    print("테스트 2: CSV 파일 업로드")
    print("="*60)
    
    url = f"{API_BASE}/scale/upload-measurements"
    
    # 샘플 CSV 파일 경로
    csv_file_path = "data/scale_measurements_sample.csv"
    
    print(f"POST {url}")
    print(f"File: {csv_file_path}")
    
    try:
        with open(csv_file_path, 'rb') as f:
            files = {'file': ('scale_measurements_sample.csv', f, 'text/csv')}
            response = requests.post(url, files=files)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 성공!\n")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # 결과 요약
            results = data.get('results', {})
            print(f"\n📊 처리 결과:")
            print(f"   총: {results.get('total', 0)}건")
            print(f"   성공: {results.get('success', 0)}건")
            print(f"   실패: {results.get('failed', 0)}건")
            
            if results.get('updates'):
                print(f"\n✅ 업데이트된 시약:")
                for update in results['updates']:
                    print(f"   - {update['reagent_name']}: {update['previous_quantity']}g → {update['new_quantity']}g")
            
            if results.get('errors'):
                print(f"\n❌ 에러:")
                for error in results['errors']:
                    print(f"   - 행 {error['row']}: {error['error']}")
            
            return True
        else:
            print(f"❌ 실패: {response.text}")
            return False
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {csv_file_path}")
        return False
    except Exception as e:
        print(f"❌ 에러: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("저울 CSV 업로드 기능 테스트")
    print("="*60)
    print("\n⚠️  참고사항:")
    print("   - FastAPI 서버가 http://127.0.0.1:8000 에서 실행 중이어야 합니다.")
    print("   - data/scale_measurements_sample.csv 파일이 있어야 합니다.")
    
    # 테스트 1: CSV에 측정값 저장
    print("\n" + "─"*60)
    input("엔터를 눌러 테스트 1을 시작하세요...")
    result1 = test_save_measurement()
    
    # 테스트 2: CSV 파일 업로드
    if result1:
        print("\n" + "─"*60)
        input("엔터를 눌러 테스트 2를 시작하세요...")
        result2 = test_upload_csv()
    
    print("\n" + "="*60)
    print("테스트 완료!")
    print("="*60)
    
    if result1:
        print("\n✅ 측정값이 data/scale_measurements.csv 파일에 저장되었습니다.")
        print("   웹 UI에서 '저울 CSV 업로드' 메뉴를 통해 이 파일을 업로드할 수 있습니다.")
    
    print("\n💡 다음 단계:")
    print("   1. 웹 브라우저에서 index.html 열기")
    print("   2. '저울 CSV 업로드' 메뉴 클릭")
    print("   3. CSV 파일 선택 후 업로드")
    print("   4. 처리 결과 확인")


if __name__ == "__main__":
    main()
