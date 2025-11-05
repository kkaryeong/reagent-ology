"""Test script to detect and connect to USB scale."""
import sys
sys.path.insert(0, '.')

from backend.scale_reader import ScaleReader, detect_scales

def main():
    print("=" * 60)
    print("저울 연결 테스트")
    print("=" * 60)
    
    # 1. 사용 가능한 시리얼 포트 검색
    print("\n1. 사용 가능한 시리얼 포트 검색 중...")
    ports = detect_scales()
    
    if not ports:
        print("❌ 연결된 시리얼 포트를 찾을 수 없습니다.")
        print("   - USB 저울이 연결되어 있는지 확인해주세요.")
        print("   - USB 케이블이 제대로 연결되어 있는지 확인해주세요.")
        return
    
    print(f"✅ {len(ports)}개의 시리얼 포트를 발견했습니다:\n")
    for i, port in enumerate(ports, 1):
        print(f"   [{i}] 포트: {port['device']}")
        print(f"       설명: {port['description']}")
        print(f"       HWID: {port['hwid']}")
        print()
    
    # 2. 각 포트에 연결 시도
    print("\n2. 각 포트에 저울 연결 시도...\n")
    
    successful_connections = []
    
    for port_info in ports:
        port = port_info['device']
        print(f"   📡 {port} 연결 시도 중...")
        
        # 일반적인 저울 통신 속도들을 시도
        baudrates = [9600, 19200, 4800, 2400, 115200]
        
        for baudrate in baudrates:
            try:
                scale = ScaleReader(port=port, baudrate=baudrate, timeout=1.0)
                if scale.connect():
                    print(f"      ✅ {port} 연결 성공! (baudrate: {baudrate})")
                    
                    # 무게 읽기 시도
                    print(f"      📊 무게 읽기 시도 중...")
                    weight = scale.read_weight()
                    
                    if weight is not None:
                        print(f"      ✅ 무게 읽기 성공: {weight} g")
                        successful_connections.append({
                            'port': port,
                            'baudrate': baudrate,
                            'weight': weight,
                            'description': port_info['description']
                        })
                    else:
                        print(f"      ⚠️  연결은 되었으나 무게를 읽을 수 없습니다.")
                        print(f"         (저울이 켜져있고 안정화되었는지 확인해주세요)")
                        successful_connections.append({
                            'port': port,
                            'baudrate': baudrate,
                            'weight': None,
                            'description': port_info['description']
                        })
                    
                    scale.disconnect()
                    break  # 성공하면 다음 baudrate 시도 안 함
                    
            except Exception as e:
                print(f"      ❌ {port} 연결 실패 (baudrate: {baudrate}): {e}")
        
        print()
    
    # 3. 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    if successful_connections:
        print(f"\n✅ {len(successful_connections)}개의 저울이 정상적으로 연결되었습니다:\n")
        for conn in successful_connections:
            print(f"   포트: {conn['port']}")
            print(f"   설명: {conn['description']}")
            print(f"   통신 속도: {conn['baudrate']} baud")
            if conn['weight'] is not None:
                print(f"   현재 무게: {conn['weight']} g")
            else:
                print(f"   현재 무게: (읽기 실패)")
            print()
        
        print("\n💡 다음 단계:")
        print(f"   1. FastAPI 서버 실행: uvicorn backend.main:app --reload")
        print(f"   2. API 테스트: GET http://127.0.0.1:8000/api/scale/ports")
        print(f"   3. 무게 읽기: GET http://127.0.0.1:8000/api/scale/weight?port={successful_connections[0]['port']}&baudrate={successful_connections[0]['baudrate']}")
    else:
        print("\n❌ 저울 연결에 실패했습니다.")
        print("\n문제 해결 방법:")
        print("   1. 저울의 전원이 켜져 있는지 확인")
        print("   2. USB 케이블이 제대로 연결되어 있는지 확인")
        print("   3. 저울 드라이버가 설치되어 있는지 확인")
        print("   4. 장치 관리자에서 COM 포트가 인식되는지 확인")
        print("   5. 다른 프로그램에서 포트를 사용 중이 아닌지 확인")

if __name__ == "__main__":
    main()
