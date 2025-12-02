# 정리 · 커밋 절차 가이드

## 1) 불필요 산출물 정리
- `git status`로 확인 후 아래 항목은 삭제하거나 `.gitignore`에 추가:
  - Node: `node_modules/`, `**/dist/`, `.vite/`, `*.tsbuildinfo`
  - Python: `.venv/`, `__pycache__/`, `*.py[cod]`, `.pytest_cache/`
  - IDE/OS: `.DS_Store`, `Thumbs.db`, `.idea/`, `.vscode/`(필요 설정만 선택 커밋)
  - 런타임 출력: `captured/`, `camera-capture/reports/`, `*.log`
  - 데이터/비밀: `data/ev_charging.db`, `openai-key.txt`, 기타 키/토큰

## 2) .gitignore 업데이트
- 위 항목을 `.gitignore`에 반영 후 `git add .gitignore`.

## 3) 의존성 확정 (Python)
- 새 venv에서:
  - `pip install -r backend/requirements.txt`
  - 필요한 추가 패키지 설치 후 `pip freeze > backend/requirements.txt`
  - 불필요 패키지는 수동으로 제거해 최소화

## 4) 의존성 확정 (Node)
- `npm install` (user-front, admin-front 각각)
- `package-lock.json` 변화 여부 확인 후 필요 시 커밋

## 5) README 갱신
- 깨진 텍스트 복구
- 최근 변경사항(예: 배치 예약 기능 등) 간단히 추가

## 6) 빌드·테스트
- 프런트: 각 프로젝트에서 `npm run build`
- 백엔드: uvicorn TestClient로 기본 API 호출 등 최소 단위 테스트
- 필요 시 추가 스모크 테스트 실행

## 7) 커밋
- 변경사항을 확인하고 적절한 메시지로 커밋
- 민감 파일(DB, 키 파일 등)은 커밋하지 않도록 최종 점검
