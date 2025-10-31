#!/usr/bin/env python3
"""CSV DB 기능 테스트 스크립트"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend import csvdb

print("=" * 60)
print("CSV Database Test")
print("=" * 60)

# 1. 시약 추가 테스트
print("\n[1] 시약 추가 테스트...")
test_reagent = {
    "slug": "test-chemical",
    "name": "Test Chemical",
    "formula": "H2O",
    "location": "Test Shelf",
    "quantity": 100.0,
    "cas": "7732-18-5",
    "storage": "RT",
    "density": 1.0,
}

reagent = csvdb.create_reagent(test_reagent)
print(f"✓ 시약 추가 성공: ID {reagent['id']}, Name: {reagent['name']}")

# 2. 시약 목록 조회
print("\n[2] 시약 목록 조회...")
all_reagents = csvdb.list_all_reagents()
print(f"✓ 총 {len(all_reagents)}개의 시약 등록됨")

# 3. 특정 시약 조회
print("\n[3] 특정 시약 조회...")
found = csvdb.get_reagent(str(reagent['id']))
if found:
    print(f"✓ ID로 조회 성공: {found['name']}")
else:
    print("✗ 조회 실패")

# 4. 시약 수정
print("\n[4] 시약 수정...")
update_data = {"quantity": 50.0, "storage": "냉장"}
updated = csvdb.update_reagent(str(reagent['id']), update_data)
if updated and updated['quantity'] == 50.0:
    print(f"✓ 수정 성공: Quantity = {updated['quantity']}, Storage = {updated['storage']}")
else:
    print("✗ 수정 실패")

# 5. 사용 기록 추가
print("\n[5] 사용 기록 추가...")
log = csvdb.add_usage_log(
    reagent_id=reagent['id'],
    prev_qty=50.0,
    new_qty=40.0,
    delta=-10.0,
    source="test",
    note="Test usage"
)
print(f"✓ 사용 기록 추가 성공: Log ID {log['id']}")

# 6. 사용 기록 조회
print("\n[6] 사용 기록 조회...")
logs = csvdb.get_usage_logs(reagent['id'])
print(f"✓ {len(logs)}개의 사용 기록 발견")

# 7. 시약 삭제
print("\n[7] 시약 삭제...")
success = csvdb.delete_reagent(str(reagent['id']))
if success:
    print("✓ 삭제 성공")
else:
    print("✗ 삭제 실패")

# 8. CSV 파일 확인
print("\n[8] CSV 파일 확인...")
data_dir = project_root / "data"
reagents_csv = data_dir / "reagents.csv"
usage_csv = data_dir / "usage_logs.csv"

if reagents_csv.exists():
    print(f"✓ reagents.csv 존재: {reagents_csv}")
else:
    print(f"✗ reagents.csv 없음")

if usage_csv.exists():
    print(f"✓ usage_logs.csv 존재: {usage_csv}")
else:
    print(f"✗ usage_logs.csv 없음")

print("\n" + "=" * 60)
print("테스트 완료!")
print("=" * 60)
