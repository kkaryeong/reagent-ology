"""Test script to verify scale API endpoints."""
import requests
import json

API_BASE = "http://127.0.0.1:8000/api"

def test_scale_ports():
    """테스트 1: 사용 가능한 포트 목록 조회"""
    print("\n" + "="*60)
    print("테스트 1: 저울 포트 목록 조회")
    print("="*60)
    
    url = f"{API_BASE}/scale/ports"
    print(f"GET {url}")
    
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 성공!\n")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data.get('ports', [])
        else:
            print(f"❌ 실패: {response.text}")
            return []
    except Exception as e:
        print(f"❌ 에러: {e}")
        return []

def test_read_weight(port="COM3", baudrate=9600):
    """테스트 2: 저울에서 무게 읽기"""
    print("\n" + "="*60)
    print("테스트 2: 저울 무게 읽기")
    print("="*60)
    
    url = f"{API_BASE}/scale/weight"
    params = {"port": port, "baudrate": baudrate}
    print(f"GET {url}")
    print(f"Parameters: {params}")
    
    try:
        response = requests.get(url, params=params)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 성공!\n")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        else:
            print(f"❌ 실패: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 에러: {e}")
        return None

def test_tare_scale(port="COM3", baudrate=9600):
    """테스트 3: 저울 영점 조정"""
    print("\n" + "="*60)
    print("테스트 3: 저울 영점 조정 (Tare)")
    print("="*60)
    
    url = f"{API_BASE}/scale/tare"
    params = {"port": port, "baudrate": baudrate}
    print(f"POST {url}")
    print(f"Parameters: {params}")
    
    try:
        response = requests.post(url, params=params)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 성공!\n")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            return data
        else:
            print(f"❌ 실패: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 에러: {e}")
        return None

def main():
    print("\n" + "="*60)
    print("저울 API 테스트")
    print("="*60)
    print("\n⚠️  참고사항:")
    print("   - 저울이 COM3 포트에 연결되어 있어야 합니다.")
    print("   - FastAPI 서버가 http://127.0.0.1:8000 에서 실행 중이어야 합니다.")
    print("   - 저울 위에 무게를 올려서 테스트해보세요!")
    
    # 테스트 1: 포트 목록
    ports = test_scale_ports()
    
    if not ports:
        print("\n❌ 포트를 찾을 수 없습니다. 테스트를 종료합니다.")
        return
    
    # 첫 번째 포트 사용
    port_device = ports[0]['device'] if ports else "COM3"
    
    # 테스트 2: 무게 읽기
    weight_data = test_read_weight(port=port_device)
    
    if weight_data:
        print(f"\n📊 현재 무게: {weight_data['weight_grams']} g")
    
    # 테스트 3: 영점 조정
    user_input = input("\n영점 조정(Tare)을 테스트하시겠습니까? (y/n): ")
    if user_input.lower() == 'y':
        tare_data = test_tare_scale(port=port_device)
        if tare_data:
            print("\n영점 조정 후 다시 무게를 읽어봅니다...")
            weight_data = test_read_weight(port=port_device)
            if weight_data:
                print(f"\n📊 영점 조정 후 무게: {weight_data['weight_grams']} g")
    
    print("\n" + "="*60)
    print("테스트 완료!")
    print("="*60)
    print("\n💡 다음 단계:")
    print("   1. 웹 브라우저에서 index.html 열기")
    print("   2. 시약 목록에서 'Use with Scale' 버튼 클릭")
    print("   3. 저울 위에 시약을 올리고 무게 측정")
    print("   4. 데이터베이스에 자동 저장 확인")

if __name__ == "__main__":
    main()
