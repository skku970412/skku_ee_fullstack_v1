from __future__ import annotations

import asyncio
import base64
import mimetypes
from typing import Any

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import JSONResponse
from openai import OpenAI, OpenAIError

from ..config import get_settings


router = APIRouter(tags=["plates"])


def _recognize_url(full: str) -> str:
    return full


def _image_to_data_url(content: bytes, content_type: str | None) -> str:
    guessed = content_type or "image/jpeg"
    if not guessed or guessed == "application/octet-stream":
        guessed = "image/jpeg"
    mime_type, _ = mimetypes.guess_type(f"file.{guessed.split('/')[-1]}")
    mime = mime_type or guessed
    encoded = base64.b64encode(content).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


async def _recognize_with_openai(image: UploadFile, settings) -> JSONResponse:
    content = await image.read()
    if not content:
        raise HTTPException(status_code=400, detail="Image file is required.")
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured.")

    data_url = _image_to_data_url(content, image.content_type)
    prompt = settings.plate_openai_prompt

    def _call_openai() -> tuple[str, str]:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.create(
            model=settings.plate_openai_model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": data_url},
                    ],
                }
            ],
        )
        text_output = (response.output_text or "").strip()
        return text_output, response.output_text or ""

    try:
        plate_text, raw_output = await asyncio.to_thread(_call_openai)
    except OpenAIError as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI error: {exc}") from exc
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"OpenAI error: {exc}") from exc
    finally:
        await image.close()

    return JSONResponse({"plate": plate_text, "raw": raw_output})


async def _proxy_recognition(
    image: UploadFile,
    settings,
) -> Any:
    try:
        url = _recognize_url(settings.plate_service_endpoint)
        content = await image.read()
        if not content:
            raise HTTPException(status_code=400, detail="Image file is required.")

        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            files = {
                "image": (
                    image.filename or "upload.jpg",
                    content,
                    image.content_type or "image/jpeg",
                )
            }
            resp = await client.post(url, files=files)
            if resp.status_code >= 400:
                # Bubble up LP service errors as 502 to the frontend
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"LP service error: status {resp.status_code}",
                )
            upstream_media_type = resp.headers.get("content-type", "").lower()
            if "charset" not in upstream_media_type:
                media_type = "application/json; charset=utf-8"
            else:
                media_type = resp.headers.get("content-type")
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=media_type,
                headers={
                    key: value
                    for key, value in resp.headers.items()
                    if key.lower() in {"cache-control", "etag"}
                },
            )
    except HTTPException:
        raise
    except asyncio.TimeoutError as exc:  # pragma: no cover
        raise HTTPException(status_code=504, detail="LP service timeout") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"LP service unreachable: {exc.__class__.__name__}"
        ) from exc
    finally:
        await image.close()


@router.post(
    "/api/license-plates",
    summary="Proxy image to LP service and return recognition result",
)
async def recognize_plate_proxy(
    image: UploadFile = File(..., description="Plate image file"),
    settings=Depends(get_settings),
) -> Any:
    if settings.plate_service_mode == "gptapi":
        return await _recognize_with_openai(image=image, settings=settings)
    return await _proxy_recognition(image=image, settings=settings)


@router.post(
    "/api/plates/recognize",
    include_in_schema=False,
)
async def recognize_plate_legacy(
    image: UploadFile = File(..., description="Plate image file"),
    settings=Depends(get_settings),
) -> Any:
    if settings.plate_service_mode == "gptapi":
        return await _recognize_with_openai(image=image, settings=settings)
    return await _proxy_recognition(image=image, settings=settings)
