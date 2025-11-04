#!/usr/bin/env bash
set -e

# 1️⃣ Rust 설치
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# 2️⃣ PATH 설정 (Rust를 찾을 수 있게)
export PATH="$HOME/.cargo/bin:$PATH"

# 3️⃣ 기본 툴체인 설정 (안정 버전)
rustup default stable

# 4️⃣ Python 패키지 설치 준비
python -m pip install --upgrade pip setuptools wheel

# 5️⃣ requirements.txt 설치
pip install -r requirements.txt

# 6️⃣ 프로젝트 빌드 명령 (여기 부분만 프로젝트마다 다름)
# FastAPI나 Flask면 예: uvicorn main:app
# Streamlit이면 예: streamlit run app.py
# 정적 사이트면 npm run build 대신 python 명령어 넣으면 됨
