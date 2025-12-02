# 프런트엔드 요약 (user-front, admin-front)

## 공통
- 스택: Vite + React 18 + TypeScript, TailwindCSS, framer-motion, lucide-react.
- API 베이스: `VITE_API_BASE` 없으면 `http(s)://<host>:8000`, 후행 `/` 제거.
- 빌드/실행: `npm install`, `npm run dev -- --host`, `npm run build`.
- 오류 처리: `extractError`로 FastAPI `detail`/배열/텍스트를 파싱해 사용자 친화 메시지 노출.

## 사용자 UI (user-front/src)
- 흐름: 허브 메뉴 ↔ 로그인 → 번호 입력·검증 → 시간·세션 선택 → 예약 생성 → 결과 → 내 예약 조회/취소.
- 번호 처리: 한국 번호판 정규식 검사, `/api/plates/verify`로 중복·겹침 확인, `/api/reservations/my?plate`로 히스토리 조회.
- 스케줄링: 4개 세션, 30분 슬롯; 날짜 ±3~10일 가용률 스트립(여러 날짜 `/api/reservations/by-session` 호출 후 점유 집계). 22시 이후 예약 차단, 종료시간 자동 계산.
- 예약 CRUD: `/api/reservations` 생성, `/api/reservations/my?email` 조회, `DELETE /api/reservations/{id}?email=...` 취소. 이메일은 소문자 정규화.
- 스캐너: `getUserMedia` 웹캠 캡처 → `/api/license-plates` 업로드 → plate 자동 입력. 스캔 다이얼로그 열림/닫힘 시 스트림 정리.
- 보조 UX: 허브 메뉴(예약/내 예약/요금표), 요금 견적(분당 100원), 날씨 위젯(open-meteo API), Stepper/애니메이션.

## 관리자 UI (admin-front/src)
- 인증: `/api/admin/login`(고정 크레덴셜·토큰). 이후 Authorization `Bearer {token}`.
- 조회: `/api/admin/reservations/by-session?date=YYYY-MM-DD`; 15초 자동 새로고침 토글, 날짜 입력 지원.
- KPI: 총 예약, 진행 중, 단순 점유율(예약당 1.7슬롯 가중).
- 세션 카드: 혼잡도 배지, 진행·다음 예약, 예약 테이블(이메일/상태/진행도/ID) + 삭제 버튼(`DELETE /api/admin/reservations/{id}`).
- 레이아웃: 2열 카드/1열 리스트 토글, framer-motion으로 전환 애니메이션.
