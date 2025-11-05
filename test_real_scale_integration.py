"""실제 저울로 시약 무게 측정하고 DB 업데이트"""
import requests
import json

API_BASE = "http://127.0.0.1:8000/api"

def test_measure_reagent_with_scale():
    """테스트: 저울로 시약 무게 측정하고 DB 업데이트"""
    print("\n" + "="*60)
    print("실제 저울로 시약 무게 측정 및 DB 업데이트 테스트")
    print("="*60)
    
    # 시약 ID 1번 (아세톤) 측정
    reagent_id = 1
    port = "COM3"
    note = "실제 저울 테스트"
    
    url = f"{API_BASE}/reagents/{reagent_id}/measure-weight"
    params = {
        "port": port,
        "baudrate": 9600,
        "note": note
    }
    
    print(f"\n📊 시약 ID {reagent_id}번의 무게를 저울로 측정합니다...")
    print(f"POST {url}")
    print(f"Parameters: {params}")
    print("\n⚠️  저울 위에 시약(또는 테스트 물체)를 올려주세요!")
    input("준비되면 엔터를 누르세요...")
    
    try:
        response = requests.post(url, params=params)
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 측정 성공!\n")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            print(f"\n📊 결과 요약:")
            print(f"   측정 무게: {data['measured_weight']} g")
            print(f"   이전 수량: {data['previous_quantity']} g")
            print(f"   변화량: {data['delta']:+.2f} g")
            print(f"   시약 이름: {data['reagent']['name']}")
            
            return True
        else:
            print(f"❌ 실패: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 에러: {e}")
        return False


def test_read_scale_only():
    """테스트: 저울에서 무게만 읽기 (DB 업데이트 안함)"""
    print("\n" + "="*60)
    print("저울 무게 읽기 테스트 (DB 업데이트 없음)")
    print("="*60)
    
    url = f"{API_BASE}/scale/weight"
    params = {"port": "COM3", "baudrate": 9600}
    
    print(f"GET {url}")
    print(f"Parameters: {params}")
    
    try:
        response = requests.get(url, params=params)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 성공!\n")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print(f"\n📊 현재 저울 무게: {data['weight_grams']} g")
            return data['weight_grams']
        else:
            print(f"❌ 실패: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 에러: {e}")
        return None


def main():
    print("\n" + "="*60)
    print("실전 저울 연동 테스트")
    print("="*60)
    print("\n⚠️  참고사항:")
    print("   - 저울이 COM3 포트에 연결되어 있어야 합니다.")
    print("   - FastAPI 서버가 http://127.0.0.1:8000 에서 실행 중이어야 합니다.")
    
    # 테스트 1: 무게만 읽기
    print("\n" + "─"*60)
    print("테스트 1: 저울 무게 읽기")
    print("─"*60)
    input("엔터를 눌러 계속...")
    
    weight = test_read_scale_only()
    
    if weight is None:
        print("\n❌ 저울 읽기에 실패했습니다. 서버와 저울 연결을 확인하세요.")
        return
    
    # 테스트 2: 시약 무게 측정 및 DB 업데이트
    print("\n" + "─"*60)
    print("테스트 2: 시약 무게 측정 및 DB 업데이트")
    print("─"*60)
    input("엔터를 눌러 계속...")
    
    result = test_measure_reagent_with_scale()
    
    if result:
        print("\n" + "="*60)
        print("✅ 모든 테스트 성공!")
        print("="*60)
        print("\n💡 다음 단계:")
        print("   1. 웹 브라우저에서 '연구실 보유 물질' 메뉴 확인")
        print("   2. 시약 목록에서 업데이트된 무게 확인")
        print("   3. 시약 상세 페이지에서 사용 기록 확인")
    else:
        print("\n" + "="*60)
        print("❌ 테스트 실패")
        print("="*60)


if __name__ == "__main__":
    main()
