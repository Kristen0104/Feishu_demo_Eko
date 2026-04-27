from __future__ import annotations

import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core import container
from app.modules.canvas.ai_service import HttpCanvasAiService
from app.modules.canvas.dependencies import get_canvas_service
from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.service import CanvasService
from app.modules.feishu.client import FeishuClient
from app.modules.feishu.dependencies import get_feishu_service
from app.modules.feishu.schemas import (
    FeishuBoardAdapterPayloadSchema,
)
from app.modules.feishu.service import FeishuService
from app.config import get_settings
from tests.modules.test_feishu_document_contract import DummyHttpClient


class StatefulStubFeishuService:
    def __init__(self) -> None:
        self._calls = 0
        self._client = FeishuClient(http_client=DummyHttpClient())
        self._service = FeishuService(client=self._client)

    def resolve_document_whiteboard_import_payload(
        self,
        *,
        share_url: str,
        session_id: str,
    ) -> FeishuBoardAdapterPayloadSchema:
        self._calls += 1
        payload = self._service.resolve_document_whiteboard_import_payload(
            share_url=share_url,
            session_id=session_id,
        )
        source_board = payload.source_board
        source_version = f"v{self._calls + 4}"
        first_node_text = "Start" if self._calls == 1 else "Source changed after refresh"
        nodes = [dict(node) for node in source_board.nodes]
        if nodes:
            nodes[0]["text"] = first_node_text
        metadata = dict(source_board.metadata)
        metadata["source_version"] = source_version
        return payload.model_copy(
            update={
                "source_board": source_board.model_copy(
                    update={
                        "nodes": nodes,
                        "metadata": metadata,
                    }
                )
            }
        )

    def export_board(
        self,
        payload: FeishuBoardAdapterPayloadSchema,
    ) -> FeishuBoardAdapterPayloadSchema:
        return self._service.export_board(payload)

    def publish_board(
        self,
        payload: FeishuBoardAdapterPayloadSchema,
    ):
        return self._service.publish_board(payload)


def create_stub_app() -> FastAPI:
    app = FastAPI(title="Canvas Stub Server")
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    container.register_routers(app)

    canvas_service = CanvasService(
        repository=CanvasRepository(storage_dir=BACKEND_ROOT / "runtime" / "canvas"),
        ai_service=HttpCanvasAiService(settings=settings),
    )
    feishu_service = StatefulStubFeishuService()
    app.dependency_overrides[get_canvas_service] = lambda: canvas_service
    app.dependency_overrides[get_feishu_service] = lambda: feishu_service
    return app


app = create_stub_app()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8012)
