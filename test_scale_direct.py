"""간단한 저울 테스트 스크립트 - 서버 없이 직접 저울 연결"""
import sys
sys.path.insert(0, 'C:\\Users\\ppofluxus\\Documents\\Regentology\\reagent-ology')

from backend.scale_reader import ScaleReader

def main():
    print("\n" + "="*60)
    print("저울 직접 연결 테스트")
    print("="*60)
    
    # 저울 연결
    scale = ScaleReader(port="COM3", baudrate=9600)
    
    print("\n1. 저울 연결 중...")
    if not scale.connect():
        print("❌ 저울 연결 실패!")
        return
    
    print(f"✅ 저울 연결 성공! (포트: {scale.port})")
    
    try:
        # 무게 읽기
        print("\n2. 무게 읽기 중...")
        weight = scale.get_stable_weight(max_attempts=5, tolerance=0.1)
        
        if weight is not None:
            print(f"✅ 측정 완료: {weight} g")
            
            # 저울 위에 물건을 올려달라고 요청
            input("\n📦 저울 위에 물건을 올려주세요. 준비되면 엔터를 누르세요...")
            
            print("\n3. 다시 무게 읽기 중...")
            weight2 = scale.get_stable_weight(max_attempts=5, tolerance=0.1)
            
            if weight2 is not None:
                print(f"✅ 측정 완료: {weight2} g")
                print(f"📊 무게 변화: {weight2 - weight:+.2f} g")
        else:
            print("❌ 무게 읽기 실패!")
            
    finally:
        scale.disconnect()
        print("\n저울 연결 해제 완료")
    
    print("\n" + "="*60)
    print("테스트 완료!")
    print("="*60)

if __name__ == "__main__":
    main()
