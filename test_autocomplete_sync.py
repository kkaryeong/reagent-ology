"""Test autocomplete synchronization from reagents to autocomplete DB"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backend import csvdb, localdb

print("=== 자동완성 DB 동기화 테스트 ===\n")

# 1. 현재 autocomplete DB 확인
print("1. 현재 autocomplete DB 항목 수:")
before_count = len(localdb.list_all())
print(f"   {before_count}개\n")

# 2. 새 시약 추가
print("2. 새 시약 추가: 염화칼륨 (Potassium Chloride)")
new_reagent = csvdb.create_reagent({
    "slug": "test-kcl",
    "name": "Test Potassium Chloride",
    "formula": "KCl",
    "cas": "7447-40-7",
    "location": "Test Shelf",
    "storage": "RT",
    "ghs": ["Irritant"],
    "disposal": "일반폐기물",
    "density": 1.98,
    "quantity": 500.0,
})
print(f"   ✓ 시약 생성: {new_reagent['name']}\n")

# 3. autocomplete DB 확인
print("3. autocomplete DB 업데이트 확인:")
after_count = len(localdb.list_all())
print(f"   항목 수: {after_count}개 (이전: {before_count}개)")

# 4. 추가된 항목 검색
print("\n4. 'Test Potassium' 검색:")
results = localdb.search_local("Test Potassium", limit=5)
if results:
    for r in results:
        print(f"   ✓ {r['name']} ({r['formula']}) - CAS: {r['cas']}, Density: {r['density']}")
else:
    print("   ✗ 검색 결과 없음")

# 5. 시약 업데이트
print("\n5. 시약 업데이트: density 변경")
updated = csvdb.update_reagent("test-kcl", {
    "density": 2.00,
    "storage": "Cool storage"
})
print(f"   ✓ 업데이트됨: density={updated['density']}, storage={updated['storage']}\n")

# 6. autocomplete DB에도 반영되었는지 확인
print("6. autocomplete DB 업데이트 확인:")
results = localdb.search_local("Test Potassium", limit=1)
if results and results[0]['density'] == 2.00:
    print(f"   ✓ 자동완성 DB도 업데이트됨: density={results[0]['density']}")
else:
    print(f"   ✗ 자동완성 DB 업데이트 실패")

# 7. 테스트 시약 삭제
print("\n7. 테스트 시약 삭제")
csvdb.delete_reagent("test-kcl")
print("   ✓ 시약 삭제 완료 (autocomplete DB에는 유지됨)")

print("\n=== 테스트 완료 ===")
print(f"최종 autocomplete DB 항목 수: {len(localdb.list_all())}개")
