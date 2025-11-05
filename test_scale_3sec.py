"""
저울 API 테스트 - 3초 안정화 기능 포함
"""
import requests
import time

API_BASE = "http://127.0.0.1:8000/api"

def test_scale_ports():
    """사용 가능한 포트 확인"""
    print("=" * 60)
    print("1️⃣  포트 목록 조회")
    print("=" * 60)
    
    response = requests.get(f"{API_BASE}/scale/ports")
    
    if response.status_code == 200:
        data = response.json()
        ports = data.get("ports", [])
        print(f"✅ 발견된 포트: {len(ports)}개")
        for port in ports:
            print(f"   - {port['device']}: {port.get('description', 'N/A')}")
        return ports
    else:
        print(f"❌ 오류: {response.status_code}")
        print(response.text)
        return []

def test_scale_weight(port="COM3"):
    """저울에서 무게 읽기 (3초 안정화)"""
    print()
    print("=" * 60)
    print(f"2️⃣  저울 무게 읽기 (포트: {port})")
    print("=" * 60)
    print("⏳ 3초 안정화 대기 중...")
    print("   (저울에 물체를 올려놓고 3초간 가만히 두세요)")
    
    start_time = time.time()
    
    try:
        response = requests.get(
            f"{API_BASE}/scale/weight",
            params={"port": port, "baudrate": 9600},
            timeout=35  # 3초 안정화 + 여유시간
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ 측정 성공! (소요 시간: {elapsed:.1f}초)")
            print(f"   📊 무게: {data['weight_grams']:.2f} g")
            print(f"   🔌 포트: {data['port']}")
            print(f"   ⏰ 시각: {data['timestamp']}")
            return data
        else:
            print(f"\n❌ 오류 (HTTP {response.status_code})")
            print(f"   소요 시간: {elapsed:.1f}초")
            try:
                error_data = response.json()
                print(f"   메시지: {error_data.get('detail', response.text)}")
            except:
                print(f"   메시지: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"\n⏱️  타임아웃! (35초 초과)")
        print("   저울이 안정화되지 않았거나 연결 문제가 있을 수 있습니다.")
        return None
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        return None

def test_reagent_measurement(reagent_id=1, port="COM3"):
    """시약 무게 측정 및 업데이트"""
    print()
    print("=" * 60)
    print(f"3️⃣  시약 #{reagent_id} 무게 측정")
    print("=" * 60)
    print("⏳ 3초 안정화 대기 중...")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{API_BASE}/reagents/{reagent_id}/measure-weight",
            params={"port": port, "baudrate": 9600, "note": "테스트 측정"},
            timeout=35
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ 측정 및 업데이트 성공! (소요 시간: {elapsed:.1f}초)")
            print(f"   📊 측정 무게: {data['measured_weight']:.2f} g")
            print(f"   📈 변화량: {data['delta']:+.2f} g")
            print(f"   🧪 시약: {data['reagent']['name']}")
            print(f"   💧 현재 수량: {data['reagent']['quantity']:.2f} g")
            if data['reagent'].get('volume_ml'):
                print(f"   📏 부피: {data['reagent']['volume_ml']:.2f} mL")
            return data
        else:
            print(f"\n❌ 오류 (HTTP {response.status_code})")
            print(f"   소요 시간: {elapsed:.1f}초")
            try:
                error_data = response.json()
                print(f"   메시지: {error_data.get('detail', response.text)}")
            except:
                print(f"   메시지: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"\n⏱️  타임아웃! (35초 초과)")
        return None
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        return None

if __name__ == "__main__":
    print("\n🧪 Reagent-ology 저울 API 테스트")
    print("   3초 안정화 기능 포함\n")
    
    # 1. 포트 확인
    ports = test_scale_ports()
    
    if not ports:
        print("\n⚠️  사용 가능한 포트가 없습니다.")
        print("   저울이 연결되어 있는지 확인하세요.")
        exit(1)
    
    # 기본 포트 선택
    default_port = ports[0]['device']
    print(f"\n✅ 기본 포트로 {default_port} 사용\n")
    
    # 2. 무게 읽기 테스트
    weight_data = test_scale_weight(default_port)
    
    if weight_data:
        # 3. 시약 측정 테스트 (선택사항)
        print("\n" + "=" * 60)
        response = input("시약 측정 테스트를 진행하시겠습니까? (y/n): ")
        if response.lower() == 'y':
            reagent_id = input("시약 ID를 입력하세요 (기본값: 1): ").strip()
            if not reagent_id:
                reagent_id = 1
            else:
                reagent_id = int(reagent_id)
            
            test_reagent_measurement(reagent_id, default_port)
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료!")
    print("=" * 60)
