from __future__ import annotations

import io
import json
from typing import Any

try:
    import lark_oapi as lark
    from lark_oapi.api.bitable.v1 import AppTableRecord, CreateAppTableRecordRequest
    from lark_oapi.api.drive.v1 import (
        CreateFolderFileRequest,
        CreateFolderFileRequestBody,
        CreateImportTaskRequest,
        GetImportTaskRequest,
        ImportTask,
        ImportTaskMountPoint,
        UploadAllMediaRequest,
        UploadAllMediaRequestBody,
    )
except ImportError:  # pragma: no cover - optional dependency in local/dev environments
    lark = None
    AppTableRecord = None
    CreateAppTableRecordRequest = None
    CreateFolderFileRequest = None
    CreateFolderFileRequestBody = None
    CreateImportTaskRequest = None
    GetImportTaskRequest = None
    ImportTask = None
    ImportTaskMountPoint = None
    UploadAllMediaRequest = None
    UploadAllMediaRequestBody = None

from app.config import settings
from app.modules.feishu.board_client import FeishuBoardClient
from app.modules.feishu.schemas import (
    FeishuBoardCreateNotesRequest,
    FeishuBoardCreateNotesSchema,
    FeishuBoardDeleteRequest,
    FeishuBoardDeleteSchema,
    FeishuBoardImageSchema,
    FeishuBoardImportRequest,
    FeishuBoardImportSchema,
    FeishuBoardNodesSchema,
    FeishuBoardUpdateRequest,
    FeishuBoardUpdateSchema,
    FeishuCardSchema,
)


class FeishuImportTaskFailedError(Exception):
    """飞书导入任务失败"""


class FeishuPermissionError(Exception):
    """飞书应用权限不足或能力未开通"""


class FeishuClient:
    def __init__(self, board_client: FeishuBoardClient | None = None) -> None:
        self._board_client = board_client or FeishuBoardClient()
        self._client = self._build_sdk_client()

    def _build_sdk_client(self):
        if lark is None or not settings.FEISHU_APP_ID or not settings.FEISHU_APP_SECRET:
            return None
        return (
            lark.Client.builder()
            .app_id(settings.FEISHU_APP_ID)
            .app_secret(settings.FEISHU_APP_SECRET)
            .log_level(lark.LogLevel.DEBUG)
            .build()
        )

    def _require_sdk_client(self):
        if self._client is None:
            raise RuntimeError(
                "Feishu document sync requires the optional lark_oapi dependency and FEISHU_APP_ID/FEISHU_APP_SECRET."
            )
        return self._client

    def get_card(self, card_id: str) -> FeishuCardSchema:
        return FeishuCardSchema(
            card_id=card_id,
            title="Stub Feishu Card",
            platform="feishu",
        )

    def import_diagram(self, payload: FeishuBoardImportRequest) -> FeishuBoardImportSchema:
        result = self._board_client.import_diagram(
            payload.whiteboard_id,
            source=payload.source,
            source_type=payload.source_type,
            syntax=payload.syntax,
            diagram_type=payload.diagram_type,
            style=payload.style,
            user_access_token=payload.user_access_token,
        )
        return FeishuBoardImportSchema(**result)

    def create_notes(self, payload: FeishuBoardCreateNotesRequest) -> FeishuBoardCreateNotesSchema:
        result = self._board_client.create_notes(
            payload.whiteboard_id,
            nodes_json_or_nodes=payload.nodes if payload.nodes is not None else (payload.nodes_json or "[]"),
            source_type=payload.source_type,
            client_token=payload.client_token,
            user_id_type=payload.user_id_type,
            user_access_token=payload.user_access_token,
        )
        return FeishuBoardCreateNotesSchema(**result)

    def get_board_nodes(self, whiteboard_id: str, user_access_token: str | None = None) -> FeishuBoardNodesSchema:
        result = self._board_client.get_board_nodes(whiteboard_id, user_access_token=user_access_token)
        return FeishuBoardNodesSchema(nodes=result["data"]["nodes"])

    def get_board_image(self, whiteboard_id: str, user_access_token: str | None = None) -> FeishuBoardImageSchema:
        result = self._board_client.get_board_image(whiteboard_id, user_access_token=user_access_token)
        return FeishuBoardImageSchema(**result)

    def update_board(self, payload: FeishuBoardUpdateRequest) -> FeishuBoardUpdateSchema:
        result = self._board_client.update_board(
            payload.whiteboard_id,
            nodes_json_or_nodes=payload.nodes if payload.nodes is not None else (payload.nodes_json or "[]"),
            source_type=payload.source_type,
            overwrite=payload.overwrite,
            dry_run=payload.dry_run,
            user_access_token=payload.user_access_token,
        )
        return FeishuBoardUpdateSchema(**result)

    def delete_board(self, payload: FeishuBoardDeleteRequest) -> FeishuBoardDeleteSchema:
        node_ids = payload.node_ids
        if payload.all:
            node_ids = self._board_client.extract_board_node_ids(
                payload.whiteboard_id,
                user_access_token=payload.user_access_token,
            )
        result = self._board_client.delete_board_nodes(
            payload.whiteboard_id,
            node_ids,
            user_access_token=payload.user_access_token,
        )
        return FeishuBoardDeleteSchema(**result)

    def create_import_task(self, markdown_content: str, file_name: str) -> str:
        client = self._require_sdk_client()
        md_bytes = markdown_content.encode("utf-8")

        folder_body = CreateFolderFileRequestBody.builder().name("Eko Imports").folder_token("").build()
        folder_request = CreateFolderFileRequest.builder().request_body(folder_body).build()
        folder_response = client.drive.v1.file.create_folder(folder_request)
        if not folder_response.success():
            raise Exception(
                f"Failed to create import folder: {folder_response.code}, {folder_response.msg}, {folder_response.request_id}"
            )

        upload_body = (
            UploadAllMediaRequestBody.builder()
            .file_name(f"{file_name}.md")
            .parent_type("ccm_import_open")
            .size(len(md_bytes))
            .extra(json.dumps({"obj_type": "docx", "file_extension": "md"}))
            .file(io.BytesIO(md_bytes))
            .build()
        )
        upload_request = UploadAllMediaRequest.builder().request_body(upload_body).build()
        upload_response = client.drive.v1.media.upload_all(upload_request)
        if not upload_response.success():
            if upload_response.code == 1061004:
                raise FeishuPermissionError(
                    "飞书应用缺少文件上传/云文档导入权限，无法上传导入源文件。"
                )
            raise Exception(
                f"Failed to upload source file: {upload_response.code}, {upload_response.msg}, {upload_response.request_id}"
            )

        mount_point = ImportTaskMountPoint.builder().mount_type(1).mount_key(folder_response.data.token).build()
        import_task = (
            ImportTask.builder()
            .file_extension("md")
            .file_name(file_name)
            .type("docx")
            .file_token(upload_response.data.file_token)
            .point(mount_point)
            .build()
        )
        request = CreateImportTaskRequest.builder().request_body(import_task).build()
        response = client.drive.v1.import_task.create(request)
        if not response.success():
            raise Exception(
                f"Failed to create import task: {response.code}, {response.msg}, {response.request_id}"
            )
        return response.data.ticket

    def get_import_task_result(self, ticket: str) -> dict[str, Any] | None:
        client = self._require_sdk_client()
        request = GetImportTaskRequest.builder().ticket(ticket).build()
        response = client.drive.v1.import_task.get(request)
        if not response.success():
            raise Exception(
                f"Failed to get import task: {response.code}, {response.msg}, {response.request_id}"
            )

        result = response.data.result
        if result.job_status in (1, 2):
            return None
        if result.job_status != 0:
            raise FeishuImportTaskFailedError(
                getattr(result, "job_error_msg", None) or response.msg or "Import task failed"
            )
        return {"url": result.url, "token": result.token}

    def get_import_task_status(self, ticket: str) -> dict[str, Any]:
        client = self._require_sdk_client()
        request = GetImportTaskRequest.builder().ticket(ticket).build()
        response = client.drive.v1.import_task.get(request)
        if not response.success():
            raise Exception(
                f"Failed to get import task: {response.code}, {response.msg}, {response.request_id}"
            )

        result = response.data.result
        if result.job_status == 0:
            return {"ticket": ticket, "status": "success", "document_url": result.url}
        if result.job_status in (1, 2):
            return {"ticket": ticket, "status": "processing", "document_url": None}
        if result.job_status < 0:
            return {"ticket": ticket, "status": "failed", "document_url": None}
        raise Exception(f"Unexpected import task status: {result.job_status}")

    def create_bitable_record(self, app_token: str, table_id: str, fields: dict[str, Any]) -> str:
        client = self._require_sdk_client()
        record = AppTableRecord.builder().fields(fields).build()
        request = (
            CreateAppTableRecordRequest.builder()
            .app_token(app_token)
            .table_id(table_id)
            .request_body(record)
            .build()
        )
        response = client.bitable.v1.app_table_record.create(request)
        if not response.success():
            raise Exception(
                f"Failed to create bitable record: {response.code}, {response.msg}, {response.request_id}"
            )
        return response.data.record.record_id
