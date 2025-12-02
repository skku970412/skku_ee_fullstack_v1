# Plate Recognition Service Integration

The project relies on an external AI service that accepts license-plate images and returns OCR results.
During development the service is assumed to run on the same host as the backend.

## Direct Access

- URL: `http://127.0.0.1:8001/v1/recognize`
- Method: `POST`
- Payload: `multipart/form-data` with a single field named `image` that contains the file data.

Example:

```bash
curl -X POST -F "image=@example.jpg" http://127.0.0.1:8001/v1/recognize
```

## Backend Proxy

The FastAPI backend exposes a proxy so that frontends (and external callers) do not need direct access to the AI service.

- URL: `http://127.0.0.1:8000/api/license-plates`
- Method: `POST`
- Payload: same as the direct endpoint (`multipart/form-data` with an `image` field).

The backend forwards the file to the service configured via the `PLATE_SERVICE_URL` environment variable
and returns the JSON response unchanged. For backwards compatibility the legacy endpoint
`POST /api/plates/recognize` is still available.

## Configuration

- `PLATE_SERVICE_URL` (default: `http://localhost:8001/v1/recognize`) controls which upstream endpoint the proxy targets.
- The convenience scripts (`run.sh` / `run.ps1`) set a sensible default when the variable is not provided.
