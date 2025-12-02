#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

log() {
  printf '[run] %s\n' "$*"
}

warn() {
  printf '[run][warn] %s\n' "$*" >&2
}

ensure_python() {
  local candidates=("python3" "python")
  for bin in "${candidates[@]}"; do
    if command -v "$bin" >/dev/null 2>&1; then
      echo "$bin"
      return 0
    fi
  done
  return 1
}

ensure_venv_and_backend_deps() {
  PYTHON_BIN="$(ensure_python || true)"
  if [[ -z "${PYTHON_BIN:-}" ]]; then
    warn "Python interpreter를 찾을 수 없습니다. 백엔드를 시작할 수 없습니다."
    BACKEND_PYTHON=""
    return
  fi

  if [[ ! -d "$VENV_DIR" ]]; then
    log "가상환경(.venv)을 생성합니다."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  if [[ -x "$VENV_DIR/bin/python" ]]; then
    BACKEND_PYTHON="$VENV_DIR/bin/python"
  elif [[ -x "$VENV_DIR/Scripts/python.exe" ]]; then
    BACKEND_PYTHON="$VENV_DIR/Scripts/python.exe"
  else
    warn ".venv 내에서 Python 실행 파일을 찾을 수 없습니다."
    BACKEND_PYTHON=""
    return
  fi

  if [[ -f "$ROOT_DIR/backend/requirements.txt" ]]; then
    log "백엔드 Python 의존성을 설치/업데이트합니다."
    "$BACKEND_PYTHON" -m pip install --upgrade pip >/dev/null
    "$BACKEND_PYTHON" -m pip install -r "$ROOT_DIR/backend/requirements.txt"
  fi
}

ensure_frontend_deps() {
  if ! command -v npm >/dev/null 2>&1; then
    warn "npm을 찾을 수 없어 프론트엔드 의존성 설치를 건너뜁니다."
    return
  fi

  for project in "admin-front" "user-front"; do
    local dir="$ROOT_DIR/$project"
    if [[ ! -f "$dir/package.json" ]]; then
      warn "$project: package.json을 찾을 수 없어 건너뜁니다."
      continue
    fi

    if [[ -d "$dir/node_modules" ]]; then
      continue
    fi

    log "$project 의존성을 설치합니다."
    (cd "$dir" && npm install)
  done
}

declare -a PIDS=()
BACKEND_PYTHON=""

ensure_venv_and_backend_deps
ensure_frontend_deps

export AUTO_SEED_SESSIONS="${AUTO_SEED_SESSIONS:-1}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:5173,http://localhost:5174,http://localhost:5175,http://192.168.45.9:5173,http://192.168.45.9:5174,http://172.17.16.1:5173,http://172.17.16.1:5174,http://172.27.64.1:5173,http://172.27.64.1:5174}"
export VITE_API_BASE="${VITE_API_BASE:-http://localhost:8000}"
export PLATE_SERVICE_URL="${PLATE_SERVICE_URL:-http://localhost:8000/api/license-plates}"

cleanup() {
  if [[ "${#PIDS[@]}" -eq 0 ]]; then
    return
  fi

  log "실행 중인 프로세스를 종료합니다."
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done

  wait "${PIDS[@]}" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

start_dev() {
  local name="$1"
  local dir="$2"

  if [[ ! -f "$dir/package.json" ]]; then
    warn "$name: package.json이 없어 실행을 건너뜁니다."
    return
  fi

  log "$name 개발 서버를 시작합니다."
  (
    cd "$dir" || exit 1
    VITE_API_BASE="$VITE_API_BASE" npm run dev -- --host
  ) &
  PIDS+=("$!")
}

start_backend() {
  if [[ -z "$BACKEND_PYTHON" ]]; then
    warn "백엔드 Python 실행 파일이 없어 API 서버를 시작하지 않습니다."
    return
  fi

  if [[ ! -f "$ROOT_DIR/backend/requirements.txt" ]]; then
    warn "backend/requirements.txt가 없어 API 서버를 시작하지 않습니다."
    return
  fi

  log "FastAPI 백엔드 서버를 시작합니다."
  (
    cd "$ROOT_DIR" || exit 1
    "$BACKEND_PYTHON" -m uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
  ) &
  PIDS+=("$!")
}

start_backend
start_dev "admin-front" "$ROOT_DIR/admin-front"
start_dev "user-front" "$ROOT_DIR/user-front"

if [[ "${#PIDS[@]}" -eq 0 ]]; then
  warn "실행된 프로세스가 없습니다."
  exit 1
fi

wait -n "${PIDS[@]}"
