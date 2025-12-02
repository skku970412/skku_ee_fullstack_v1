#!/usr/bin/env bash
set -euo pipefail

# Resolve repository root even when invoked via symlink.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

log() {
  printf '[setup] %s\n' "$*"
}

warn() {
  printf '[setup][warn] %s\n' "$*" >&2
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

PYTHON_BIN="$(ensure_python || true)"
if [[ -n "${PYTHON_BIN:-}" ]]; then
  if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating virtual environment at $VENV_DIR using $PYTHON_BIN"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  else
    log "Virtual environment already exists at $VENV_DIR"
  fi

  # shellcheck disable=SC1091
  if [[ -f "$VENV_DIR/bin/activate" ]]; then
    source "$VENV_DIR/bin/activate"
  elif [[ -f "$VENV_DIR/Scripts/activate" ]]; then
    source "$VENV_DIR/Scripts/activate"
  fi

  if [[ -f "$ROOT_DIR/backend/requirements.txt" ]]; then
    log "Installing backend Python dependencies"
    python -m pip install --upgrade pip >/dev/null
    python -m pip install -r "$ROOT_DIR/backend/requirements.txt"
  fi
else
  warn "Could not find python3 or python on PATH; skipping virtualenv creation"
fi

if ! command -v npm >/dev/null 2>&1; then
  warn "npm is not available on PATH; skipping frontend dependency installation"
  exit 0
fi

for project in "admin-front" "user-front"; do
  project_dir="$ROOT_DIR/$project"
  if [[ ! -f "$project_dir/package.json" ]]; then
    warn "Skipping $project_dir (package.json not found)"
    continue
  fi

  if [[ -d "$project_dir/node_modules" ]]; then
    log "$project dependencies already installed"
    continue
  fi

  log "Installing npm dependencies for $project"
  (cd "$project_dir" && npm install)
done

log "Setup complete"
