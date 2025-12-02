#!/usr/bin/env python3
"""Camera worker that watches Firebase and captures photos for AI recognition."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import firebase_admin
from firebase_admin import credentials, db, storage as fb_storage
import requests


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value not in (None, "") else default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value not in (None, "") else default


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return default if value in (None, "") else value


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE lines into os.environ (ignores comments/blank lines)."""
    try:
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, _, val = stripped.partition("=")
            if key and val:
                os.environ.setdefault(key.strip(), val.strip())
    except Exception:
        # Fail silent; this file is optional.
        pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture a photo when Firebase signals that a car entered the lot."
    )
    parser.add_argument(
        "--pipeline-mode",
        choices=("gpt", "storage", "both"),
        default=_env_str("PIPELINE_MODE", "gpt").lower(),
        help="Pipeline behavior: gpt=recognition/match only, storage=upload only, both=do both.",
    )
    parser.add_argument(
        "--credentials",
        default=os.getenv("FIREBASE_CREDENTIALS"),
        help="Path to the Firebase service-account JSON (default: FIREBASE_CREDENTIALS).",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("FIREBASE_DATABASE_URL"),
        help="Firebase Realtime Database URL (default: FIREBASE_DATABASE_URL).",
    )
    parser.add_argument(
        "--storage-bucket",
        default=os.getenv("FIREBASE_STORAGE_BUCKET"),
        help="Firebase Storage bucket name (e.g., plate-detection-xxxx.firebasestorage.app).",
    )
    parser.add_argument(
        "--storage-prefix",
        default=os.getenv("FIREBASE_STORAGE_PREFIX", "uploads"),
        help="Prefix path inside the bucket for uploads (default: uploads).",
    )
    parser.add_argument(
        "--signal-path",
        default=os.getenv("FIREBASE_SIGNAL_PATH", "/signals/car_on_parkinglot"),
        help="Realtime Database path that toggles when a car arrives.",
    )
    parser.add_argument(
        "--timestamp-path",
        default=os.getenv("FIREBASE_TIMESTAMP_PATH", "/signals/timestamp"),
        help="Realtime Database path that stores the detection timestamp.",
    )
    parser.add_argument(
        "--match-path",
        default=os.getenv("FIREBASE_CAR_MATCH_PATH", "/signals/car_plate_same"),
        help="Realtime Database path updated with plate match results.",
    )
    parser.add_argument(
        "--rtdb-plate-path",
        default=os.getenv("DETECTED_RTDB_PATH"),
        help="Optional RTDB path containing detected plate data (used as a secondary candidate).",
    )
    parser.add_argument(
        "--rtdb-timestamp-field",
        default=os.getenv("DETECTED_RTDB_TIMESTAMP_FIELD", "timestamp"),
        help="Timestamp field name when picking the latest RTDB plate entry (default: timestamp).",
    )
    parser.add_argument(
        "--expected-signal-value",
        default=os.getenv("EXPECTED_SIGNAL_VALUE", "ok"),
        help="Value that indicates the car-entry event has fired.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=_env_float("SIGNAL_POLL_INTERVAL", 2.0),
        help="Seconds between signal checks.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=_env_float("SIGNAL_TIMEOUT", 60.0),
        help="Max seconds to wait for the signal (0 or negative disables timeout).",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=_env_int("CAMERA_INDEX", 0),
        help="OpenCV camera index.",
    )
    parser.add_argument(
        "--camera-name",
        default=os.getenv("CAMERA_NAME_HINT", "C270"),
        help="Substring of the DirectShow device name used to auto-detect the camera.",
    )
    parser.add_argument(
        "--output-path",
        default=os.getenv("CAPTURE_OUTPUT_PATH", "captured/car_entry.jpg"),
        help="Where to save the captured photo.",
    )
    parser.add_argument(
        "--warmup-seconds",
        type=float,
        default=_env_float("CAMERA_WARMUP_SECONDS", 1.5),
        help="Seconds to wait after opening the camera before grabbing a frame.",
    )
    parser.add_argument(
        "--recognition-url",
        default=os.getenv("PLATE_SERVICE_URL", "http://localhost:8000/api/license-plates"),
        help="License-plate recognition HTTP endpoint (default: PLATE_SERVICE_URL).",
    )
    parser.add_argument(
        "--secondary-recognition-url",
        default=os.getenv("SECONDARY_RECOGNITION_URL"),
        help="Optional second recognition endpoint when pipeline-mode=both. If provided, its plate wins.",
    )
    parser.add_argument(
        "--recognition-timeout",
        type=float,
        default=_env_float("RECOGNITION_TIMEOUT", 15.0),
        help="HTTP timeout when calling the AI service.",
    )
    parser.add_argument(
        "--report-dir",
        default=os.getenv("CAPTURE_REPORT_DIR", "camera-capture/reports"),
        help="Directory where JSON reports for each attempt are stored.",
    )
    parser.add_argument(
        "--match-url",
        default=os.getenv("PLATE_MATCH_URL", "http://localhost:8000/api/plates/match"),
        help="Backend endpoint used to confirm whether the plate matches an active reservation.",
    )
    parser.add_argument(
        "--match-timeout",
        type=float,
        default=_env_float("PLATE_MATCH_TIMEOUT", 10.0),
        help="HTTP timeout when calling the backend plate match endpoint.",
    )
    parser.add_argument(
        "--serial-port",
        default=os.getenv("PLATE_MATCH_SERIAL_PORT"),
        help="Optional serial port (e.g., COM5) to ping when a reservation match is found.",
    )
    parser.add_argument(
        "--serial-baudrate",
        type=int,
        default=_env_int("PLATE_MATCH_SERIAL_BAUDRATE", 9600),
        help="Baud rate when opening the serial port.",
    )
    parser.add_argument(
        "--serial-message",
        default=os.getenv("PLATE_MATCH_SERIAL_MESSAGE", "START"),
        help="Payload text sent to the serial device upon a successful match.",
    )
    parser.add_argument(
        "--serial-timeout",
        type=float,
        default=_env_float("PLATE_MATCH_SERIAL_TIMEOUT", 2.0),
        help="Seconds to wait for the serial port to open/write.",
    )
    parser.add_argument(
        "--serial-wait",
        type=float,
        default=_env_float("PLATE_MATCH_SERIAL_WAIT_SECONDS", 0.15),
        help="Delay (seconds) after opening the serial port before writing.",
    )
    parser.add_argument(
        "--serial-no-newline",
        action="store_true",
        help="Do not append a newline when sending the serial payload.",
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuously; otherwise exit after a single capture attempt.",
    )
    parser.add_argument(
        "--cycle-interval",
        type=float,
        default=_env_float("CYCLE_INTERVAL_SECONDS", 2.0),
        help="Seconds to sleep between cycles in --continuous mode.",
    )
    parser.add_argument(
        "--skip-firebase",
        action="store_true",
        help="Skip Firebase wait logic (useful for local testing).",
    )
    parser.add_argument(
        "--upload-to-storage",
        action="store_true",
        default=_env_bool("AUTO_UPLOAD_TO_STORAGE", False),
        help="Also upload captured photos to Firebase Storage (requires --storage-bucket and credentials). "
        "Set AUTO_UPLOAD_TO_STORAGE=1 to enable by default.",
    )
    parser.add_argument(
        "--mock-signal-value",
        default=os.getenv("MOCK_SIGNAL_VALUE", "done"),
        help="Printed signal value when --skip-firebase is enabled.",
    )
    parser.add_argument(
        "--auth-mode",
        choices=("admin", "rest"),
        default=os.getenv("FIREBASE_AUTH_MODE", "admin"),
        help="Firebase connection strategy (admin uses service account, rest uses HTTP).",
    )
    parser.add_argument(
        "--rest-auth-token",
        default=os.getenv("FIREBASE_REST_AUTH_TOKEN"),
        help="Optional auth token appended to REST mode requests.",
    )
    parser.add_argument(
        "--list-cameras",
        action="store_true",
        help="Print available DirectShow devices and exit.",
    )
    return parser


def init_firebase(credentials_path: Path, database_url: str | None, storage_bucket: str | None) -> firebase_admin.App:
    if not credentials_path.exists():
        raise FileNotFoundError(f"Service-account file not found: {credentials_path}")
    if firebase_admin._apps:  # type: ignore[attr-defined]
        return firebase_admin.get_app()
    cred = credentials.Certificate(credentials_path)
    options: dict[str, str] = {}
    if database_url:
        options["databaseURL"] = database_url
    if storage_bucket:
        options["storageBucket"] = storage_bucket
    return firebase_admin.initialize_app(cred, options or None)


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    return str(value).strip().lower()


def wait_for_signal_admin(
    *,
    signal_path: str,
    expected_value: str,
    poll_interval: float,
    timeout: Optional[float],
) -> Any:
    reference = db.reference(signal_path)
    target = _normalize_value(expected_value)
    deadline = time.time() + timeout if timeout and timeout > 0 else None
    while True:
        value = reference.get()
        normalized = _normalize_value(value)
        print(f"[Firebase] current value: {value} (path: {signal_path})")
        if normalized == target:
            print("[Firebase] expected signal received.")
            return value
        if deadline and time.time() >= deadline:
            raise TimeoutError(
                f"Signal {signal_path} did not become '{expected_value}' within timeout."
            )
        time.sleep(max(0.1, poll_interval))


def _signal_url(database_url: str, signal_path: str) -> str:
    base = database_url.rstrip("/")
    path = signal_path if signal_path.startswith("/") else f"/{signal_path}"
    return f"{base}{path}.json"


def wait_for_signal_rest(
    *,
    database_url: str,
    signal_path: str,
    expected_value: str,
    poll_interval: float,
    timeout: Optional[float],
    auth_token: Optional[str],
) -> Any:
    target = _normalize_value(expected_value)
    deadline = time.time() + timeout if timeout and timeout > 0 else None
    url = _signal_url(database_url, signal_path)
    params = {"auth": auth_token} if auth_token else None
    while True:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        value = response.json()
        normalized = _normalize_value(value)
        print(f"[Firebase REST] current value: {value} (path: {signal_path})")
        if normalized == target:
            print("[Firebase REST] expected signal received.")
            return value
        if deadline and time.time() >= deadline:
            raise TimeoutError(
                f"Signal {signal_path} did not become '{expected_value}' within timeout."
            )
        time.sleep(max(0.1, poll_interval))


def parse_timestamp_value(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        divisor = 1000.0 if abs(value) > 1_000_000_000_000 else 1.0
        return datetime.fromtimestamp(value / divisor, tz=timezone.utc)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.isdigit():
            return parse_timestamp_value(int(stripped))
        normalized = stripped[:-1] + "+00:00" if stripped.endswith("Z") else stripped
        try:
            dt = datetime.fromisoformat(normalized)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def fetch_timestamp_admin(path_value: str) -> Any:
    reference = db.reference(path_value)
    return reference.get()


def fetch_timestamp_rest(database_url: str, path_value: str, auth_token: Optional[str]) -> Any:
    url = _signal_url(database_url, path_value)
    params = {"auth": auth_token} if auth_token else None
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_latest_rtdb_plate(path_value: str, *, timestamp_field: str = "timestamp") -> Tuple[Optional[str], Any]:
    """
    Fetch plate data from RTDB path. If the path contains multiple children, pick the one
    with the greatest timestamp_field value. Returns (plate, raw_payload).
    """
    try:
        reference = db.reference(path_value)
        data = reference.get()
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[RTDB] Failed to read {path_value}: {exc}")
        return None, None

    if not data:
        return None, data

    def _extract(obj: Any) -> Optional[str]:
        if isinstance(obj, dict):
            plate_val = obj.get("plate")
            if isinstance(plate_val, str) and plate_val.strip():
                return plate_val.strip()
        if isinstance(obj, str) and obj.strip():
            return obj.strip()
        return None

    if isinstance(data, dict) and "plate" in data:
        return _extract(data), data

    if isinstance(data, dict):
        # Select child with max timestamp_field if available.
        best_plate = None
        best_payload = None
        best_ts = None
        for value in data.values():
            plate_val = _extract(value)
            if plate_val:
                ts_val = None
                if isinstance(value, dict) and timestamp_field in value:
                    try:
                        ts_val = float(value[timestamp_field])
                    except Exception:
                        ts_val = None
                if best_ts is None or (ts_val is not None and ts_val >= (best_ts or float("-inf"))):
                    best_plate = plate_val
                    best_payload = value
                    best_ts = ts_val if ts_val is not None else best_ts
        return best_plate, data if best_payload is None else best_payload

    # Fallback: if simple value
    return _extract(data), data


def update_match_signal_admin(path_value: str, value: str) -> None:
    reference = db.reference(path_value)
    reference.set(value)


def update_match_signal_rest(
    database_url: str,
    path_value: str,
    value: str,
    auth_token: Optional[str],
) -> None:
    url = _signal_url(database_url, path_value)
    params = {"auth": auth_token} if auth_token else None
    requests.put(url, params=params, json=value, timeout=10)


def _load_camera_devices() -> List[str]:
    try:
        from pygrabber.dshow_graph import FilterGraph
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pygrabber is required to enumerate camera devices.") from exc
    graph = FilterGraph()
    return graph.get_input_devices()


def find_camera_index_by_name(name_hint: str) -> Optional[int]:
    if not name_hint:
        return None
    try:
        devices = _load_camera_devices()
    except RuntimeError as exc:
        print(f"[Camera] unable to list devices: {exc}")
        return None
    for idx, device_name in enumerate(devices):
        if name_hint.lower() in device_name.lower():
            return idx
    return None


def print_camera_devices() -> None:
    try:
        devices = _load_camera_devices()
    except RuntimeError as exc:
        print(f"[Camera] failed to list devices: {exc}")
        return
    if not devices:
        print("[Camera] no DirectShow devices available.")
        return
    print("[Camera] available DirectShow devices:")
    for idx, device_name in enumerate(devices):
        print(f"  [{idx}] {device_name}")


def capture_photo(camera_index: int, output_path: Path, warmup_seconds: float) -> Path:
    backend = cv2.CAP_DSHOW if os.name == "nt" else 0
    capture = cv2.VideoCapture(camera_index, backend)
    if not capture.isOpened():
        raise RuntimeError(f"Camera index {camera_index} could not be opened.")
    try:
        time.sleep(max(0.0, warmup_seconds))
        ok, frame = capture.read()
        if not ok or frame is None:
            raise RuntimeError("Failed to read frame from camera.")
    finally:
        capture.release()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    success, buffer = cv2.imencode(".jpg", frame)
    if not success:
        raise RuntimeError("Failed to encode frame as JPEG.")
    output_path.write_bytes(buffer.tobytes())
    return output_path


def upload_file_to_storage(*, bucket_name: str, local_path: Path, dest_path: str) -> str:
    """
    Upload a local file to Firebase Storage. Returns the public URL (if readable by rules).
    """
    if not bucket_name:
        raise ValueError("storage bucket name is required for upload.")
    bucket = fb_storage.bucket(bucket_name)
    blob = bucket.blob(dest_path)
    blob.upload_from_filename(local_path, content_type="image/jpeg")
    return blob.public_url


def _read_image_bytes(image_path: Path) -> bytes:
    return image_path.read_bytes()


def recognize_plate_http(
    *,
    image_path: Path,
    url: str,
    timeout: float,
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    if not url:
        return False, None, "Recognition URL is empty."
    files = {
        "image": (
            image_path.name,
            _read_image_bytes(image_path),
            "image/jpeg",
        )
    }
    try:
        response = requests.post(url, files=files, timeout=max(1.0, timeout))
        response.raise_for_status()
        data = response.json()
        return True, data, None
    except requests.RequestException as exc:
        return False, None, f"HTTP error: {exc}"
    except ValueError as exc:
        return False, None, f"Invalid JSON response: {exc}"


def match_plate_http(
    *,
    url: str,
    plate: str,
    timestamp: datetime,
    timeout: float,
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    if not url:
        return False, None, "Match URL is empty."
    payload = {"plate": plate, "timestamp": timestamp.isoformat()}
    try:
        response = requests.post(url, json=payload, timeout=max(1.0, timeout))
        response.raise_for_status()
        data = response.json()
        return True, data, None
    except requests.RequestException as exc:
        return False, None, f"HTTP error: {exc}"
    except ValueError as exc:
        return False, None, f"Invalid JSON response: {exc}"


def write_report(report_dir: Path, payload: Dict[str, Any]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    report_path = report_dir / f"report-{stamp}.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def trigger_serial_device(
    *,
    port: str,
    baudrate: int,
    message: str,
    append_newline: bool,
    wait_seconds: float,
    timeout: float,
) -> Tuple[bool, Optional[str]]:
    try:
        # Import lazily to keep pyserial optional until needed.
        import serial  # type: ignore  # pylint: disable=import-error
    except ImportError as exc:  # pragma: no cover - handled at runtime
        return False, f"pyserial is not installed: {exc}"

    payload = message or ""
    if append_newline and not payload.endswith("\n"):
        payload += "\n"
    encoded = payload.encode("utf-8")

    try:
        with serial.Serial(
            port=port,
            baudrate=max(1200, baudrate),
            timeout=max(0.1, timeout),
        ) as conn:
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            conn.write(encoded)
            conn.flush()
        return True, None
    except Exception as exc:  # pylint: disable=broad-except
        return False, str(exc)


def process_cycle(
    *,
    args: argparse.Namespace,
    camera_index: int,
    auto_resolved: bool,
) -> None:
    timestamp_raw: Any = None
    detected_timestamp = datetime.now(timezone.utc)

    if not args.skip_firebase:
        if args.auth_mode == "admin":
            wait_for_signal_admin(
                signal_path=args.signal_path,
                expected_value=args.expected_signal_value,
                poll_interval=args.poll_interval,
                timeout=None if args.timeout <= 0 else args.timeout,
            )
            try:
                timestamp_raw = fetch_timestamp_admin(args.timestamp_path)
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[Firebase] Failed to fetch timestamp: {exc}")
        else:
            wait_for_signal_rest(
                database_url=args.database_url,
                signal_path=args.signal_path,
                expected_value=args.expected_signal_value,
                poll_interval=args.poll_interval,
                timeout=None if args.timeout <= 0 else args.timeout,
                auth_token=args.rest_auth_token,
            )
            try:
                timestamp_raw = fetch_timestamp_rest(
                    args.database_url, args.timestamp_path, args.rest_auth_token
                )
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[Firebase REST] Failed to fetch timestamp: {exc}")
    else:
        print(f"[Firebase] skipped (--skip-firebase). mock value: {args.mock_signal_value}")

    parsed_timestamp = parse_timestamp_value(timestamp_raw)
    if parsed_timestamp:
        detected_timestamp = parsed_timestamp
    elif timestamp_raw is not None:
        print(f"[Worker] Unable to parse timestamp '{timestamp_raw}', using current UTC value.")

    output_path = capture_photo(
        camera_index=camera_index,
        output_path=Path(args.output_path),
        warmup_seconds=args.warmup_seconds,
    )

    storage_url: str | None = None
    storage_path: str | None = None
    if args.upload_to_storage and args.pipeline_mode in {"both", "storage"}:
        if not args.storage_bucket:
            print("[Storage] upload skipped: --storage-bucket is not set.")
        else:
            try:
                prefix = args.storage_prefix.rstrip("/\\")
                filename = Path(output_path).name
                storage_path = f"{prefix}/{filename}" if prefix else filename
                storage_url = upload_file_to_storage(
                    bucket_name=args.storage_bucket,
                    local_path=output_path,
                    dest_path=storage_path,
                )
                print(f"[Storage] uploaded to {storage_path}")
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[Storage] upload failed: {exc}")
    elif args.upload_to_storage and args.pipeline_mode == "gpt":
        print("[Storage] upload disabled because pipeline-mode=gpt.")

    suffix = " (auto-detected)" if auto_resolved else ""
    print(f"[Camera] captured photo at {output_path}{suffix}")

    primary_success = False
    primary_data: Optional[Dict[str, Any]] = None
    primary_error: Optional[str] = None

    secondary_success = False
    secondary_data: Optional[Dict[str, Any]] = None
    secondary_error: Optional[str] = None

    rtdb_plate: Optional[str] = None
    rtdb_payload: Any = None

    if args.pipeline_mode in {"gpt", "both"}:
        primary_success, primary_data, primary_error = recognize_plate_http(
            image_path=output_path,
            url=args.recognition_url,
            timeout=args.recognition_timeout,
        )
        if primary_success:
            plate = primary_data.get("plate") if isinstance(primary_data, dict) else None
            print(f"[AI-primary] recognition succeeded: {plate or 'no plate field'}")
        else:
            print(f"[AI-primary] recognition failed: {primary_error or 'unknown error'}")

    if args.pipeline_mode == "both" and args.secondary_recognition_url:
        secondary_success, secondary_data, secondary_error = recognize_plate_http(
            image_path=output_path,
            url=args.secondary_recognition_url,
            timeout=args.recognition_timeout,
        )
        if secondary_success:
            plate = secondary_data.get("plate") if isinstance(secondary_data, dict) else None
            print(f"[AI-secondary] recognition succeeded: {plate or 'no plate field'}")
        else:
            print(f"[AI-secondary] recognition failed: {secondary_error or 'unknown error'}")

    if args.rtdb_plate_path and args.pipeline_mode in {"gpt", "both"}:
        if firebase_admin._apps:  # type: ignore[attr-defined]
            rtdb_plate, rtdb_payload = fetch_latest_rtdb_plate(
                args.rtdb_plate_path, timestamp_field=args.rtdb_timestamp_field
            )
            print(f"[RTDB] plate candidate: {rtdb_plate or 'none'}")
        else:
            print("[RTDB] skipped: firebase not initialized.")

    def _extract_plate(payload: Optional[Dict[str, Any]]) -> Optional[str]:
        if not payload:
            return None
        plate_val = payload.get("plate")
        if isinstance(plate_val, str) and plate_val.strip():
            return plate_val.strip()
        return None

    recognized_plate = None
    secondary_plate = _extract_plate(secondary_data)
    primary_plate = _extract_plate(primary_data)
    rtdb_candidate = rtdb_plate if isinstance(rtdb_plate, str) and rtdb_plate.strip() else None

    if secondary_plate:
        recognized_plate = secondary_plate
    elif primary_plate:
        recognized_plate = primary_plate
    elif rtdb_candidate:
        recognized_plate = rtdb_candidate

    match_success = False
    match_response: Optional[Dict[str, Any]] = None
    match_error: Optional[str] = None
    match_result: Optional[bool] = None

    serial_trigger_sent: Optional[bool] = None
    serial_trigger_error: Optional[str] = None

    if recognized_plate and args.pipeline_mode in {"gpt", "both"}:
        match_success, match_response, match_error = match_plate_http(
            url=args.match_url,
            plate=recognized_plate,
            timestamp=detected_timestamp,
            timeout=args.match_timeout,
        )
        if match_success and isinstance(match_response, dict):
            match_result = bool(match_response.get("match"))
            print(f"[Backend] Plate match result: {'ok' if match_result else 'no'}")
            if match_result and args.serial_port:
                serial_trigger_sent, serial_trigger_error = trigger_serial_device(
                    port=args.serial_port,
                    baudrate=args.serial_baudrate,
                    message=args.serial_message,
                    append_newline=not args.serial_no_newline,
                    wait_seconds=args.serial_wait,
                    timeout=args.serial_timeout,
                )
                if serial_trigger_sent:
                    print(f"[Serial] Trigger sent to {args.serial_port}.")
                else:
                    print(f"[Serial] Failed to send trigger: {serial_trigger_error}")
        else:
            print(f"[Backend] Plate match failed: {match_error or 'unknown error'}")
    else:
        match_error = "Plate not recognized."

    car_match_written: Optional[str] = None
    if not args.skip_firebase and args.pipeline_mode in {"gpt", "both"}:
        desired_value = "ok" if match_result else "no"
        try:
            if args.auth_mode == "admin":
                update_match_signal_admin(args.match_path, desired_value)
            else:
                update_match_signal_rest(
                    args.database_url, args.match_path, desired_value, args.rest_auth_token
                )
            car_match_written = desired_value
            print(f"[Firebase] Updated {args.match_path} to {desired_value}.")
        except Exception as exc:  # pylint: disable=broad-except
            match_error = f"{match_error or ''} | Firebase update failed: {exc}".strip()
            print(f"[Firebase] Failed to update {args.match_path}: {exc}")

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "image_path": str(output_path),
        "storage_bucket": args.storage_bucket,
        "storage_upload_path": storage_path,
        "storage_upload_url": storage_url,
        "recognition_url": args.recognition_url,
        "secondary_recognition_url": args.secondary_recognition_url,
        "pipeline_mode": args.pipeline_mode,
        "success": primary_success or secondary_success,
        "plate": recognized_plate,
        "response": primary_data,
        "response_secondary": secondary_data,
        "rtdb_plate": rtdb_plate,
        "rtdb_payload": rtdb_payload,
        "error": primary_error,
        "error_secondary": secondary_error,
        "detected_timestamp": detected_timestamp.isoformat(),
        "match_url": args.match_url,
        "match_success": match_success,
        "match_response": match_response,
        "match_error": match_error,
        "car_plate_same": car_match_written,
        "serial_port": args.serial_port,
        "serial_trigger_sent": serial_trigger_sent,
        "serial_trigger_error": serial_trigger_error,
    }
    report_path = write_report(Path(args.report_dir), payload)
    print(f"[Report] wrote {report_path}")


def main() -> None:
    # Best-effort load of camera-capture/storage.env so bucket/prefix defaults are available.
    _load_env_file(Path(__file__).resolve().parent / "storage.env")

    parser = build_parser()
    args = parser.parse_args()

    if args.list_cameras:
        print_camera_devices()
        return

    resolved_camera_index = None
    auto_resolved = False
    if args.camera_name:
        idx = find_camera_index_by_name(args.camera_name)
        if idx is not None:
            resolved_camera_index = idx
            auto_resolved = True
            print(f"[Camera] auto-selected device index {idx} by name hint '{args.camera_name}'")
        else:
            print(
                f"[Camera] could not find a device containing '{args.camera_name}'. "
                "Falling back to --camera-index."
            )
    if resolved_camera_index is None:
        resolved_camera_index = args.camera_index

    if not args.skip_firebase:
        if args.auth_mode == "admin":
            if not args.credentials:
                parser.error("admin mode requires --credentials.")
            init_firebase(Path(args.credentials).expanduser(), args.database_url, args.storage_bucket)
        else:
            if not args.database_url:
                parser.error("rest mode requires --database-url.")
    if args.upload_to_storage and not firebase_admin._apps:  # type: ignore[attr-defined]
        # Storage access needs admin credentials even if realtime DB is skipped.
        if not args.credentials:
            parser.error("--upload-to-storage requires --credentials for Firebase admin access.")
        init_firebase(Path(args.credentials).expanduser(), args.database_url, args.storage_bucket)

    keep_running = True
    while keep_running:
        try:
            process_cycle(
                args=args,
                camera_index=resolved_camera_index,
                auto_resolved=auto_resolved,
            )
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[Worker] cycle failed: {exc}", file=sys.stderr)

        keep_running = args.continuous
        if keep_running:
            time.sleep(max(0.2, args.cycle_interval))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[Fatal] {exc}", file=sys.stderr)
        sys.exit(1)
