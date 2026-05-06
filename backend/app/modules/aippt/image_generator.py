from __future__ import annotations

import base64
from pathlib import Path

import httpx

from app.config import Settings


class GPTImageGenerator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def enabled(self) -> bool:
        return self._settings.AIPPT_IMAGE_GENERATION_ENABLED and bool(self._settings.AIPPT_IMAGE_API_KEY)

    def generate_pending_images(self, resources: list[dict[str, str]], project_dir: Path, prompt_builder) -> list[dict[str, str]]:
        updated: list[dict[str, str]] = []
        for resource in resources:
            item = dict(resource)
            if item.get("status", "Pending") != "Pending":
                updated.append(item)
                continue

            try:
                prompt = prompt_builder(item)
                output_path = self._generate_one(prompt, project_dir / "images", item)
                item["filename"] = output_path.name
                item["status"] = "Generated"
                item["path"] = str(output_path)
                item.pop("error", None)
            except Exception as exc:
                item["status"] = "Needs-Manual"
                item["error"] = str(exc)
            updated.append(item)
        return updated

    def _generate_one(self, prompt: str, images_dir: Path, resource: dict[str, str]) -> Path:
        images_dir.mkdir(parents=True, exist_ok=True)
        filename = self._normalized_filename(resource.get("filename") or "image.png")
        output_path = images_dir / filename
        payload = {
            "model": self._settings.AIPPT_IMAGE_MODEL,
            "prompt": prompt,
            "size": self._settings.AIPPT_IMAGE_SIZE,
            "quality": self._settings.AIPPT_IMAGE_QUALITY,
            "output_format": self._settings.AIPPT_IMAGE_OUTPUT_FORMAT,
            "response_format": "b64_json",
            "n": 1,
        }
        headers = {
            "Authorization": f"Bearer {self._settings.AIPPT_IMAGE_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "*/*",
        }
        with httpx.Client(timeout=self._settings.AIPPT_IMAGE_TIMEOUT_SECONDS, trust_env=False) as client:
            response = client.post(
                f"{self._settings.AIPPT_IMAGE_API_BASE.rstrip('/')}/v1/images/generations",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json().get("data") or []
            if not data:
                raise RuntimeError("image API returned no data")
            first = data[0]
            if first.get("b64_json"):
                output_path.write_bytes(base64.b64decode(first["b64_json"]))
                return output_path
            if first.get("url"):
                image_response = client.get(first["url"])
                image_response.raise_for_status()
                output_path.write_bytes(image_response.content)
                return output_path
        raise RuntimeError("image API returned neither b64_json nor url")

    def _normalized_filename(self, filename: str) -> str:
        path = Path(filename)
        suffix = path.suffix.lower() or f".{self._settings.AIPPT_IMAGE_OUTPUT_FORMAT.lower()}"
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            suffix = f".{self._settings.AIPPT_IMAGE_OUTPUT_FORMAT.lower()}"
        safe_stem = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in path.stem).strip("._")
        return f"{safe_stem or 'image'}{suffix}"
