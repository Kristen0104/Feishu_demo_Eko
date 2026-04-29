from __future__ import annotations

import io
import json
from typing import Any

import lark_oapi as lark
from lark_oapi.api.drive.v1 import (
    CreateImportTaskRequest,
    CreateFolderFileRequest,
    CreateFolderFileRequestBody,
    ImportTask,
    ImportTaskMountPoint,
    GetImportTaskRequest,
    UploadAllMediaRequest,
    UploadAllMediaRequestBody,
)
from lark_oapi.api.bitable.v1 import (
    CreateAppTableRecordRequest,
    AppTableRecord,
)

from app.config import settings
from app.modules.feishu.schemas import FeishuCardSchema


class FeishuImportTaskFailedError(Exception):
    """飞书导入任务失败"""


class FeishuPermissionError(Exception):
    """飞书应用权限不足或能力未开通"""


class FeishuClient:
    """飞书 API 客户端封装

    使用官方 lark-oapi SDK 实现:
    - 文档导入任务（将 Markdown 导入为飞书文档）
    - 多维表格记录创建
    - 其他飞书 API 能力
    """

    def __init__(self) -> None:
        # 自建应用初始化，云文档/通讯录接口专用
        self._client = lark.Client.builder() \
            .app_id(settings.FEISHU_APP_ID) \
            .app_secret(settings.FEISHU_APP_SECRET) \
            .log_level(lark.LogLevel.DEBUG) \
            .build()

    def get_card(self, card_id: str) -> FeishuCardSchema:
        return FeishuCardSchema(
            card_id=card_id,
            title="Stub Feishu Card",
            platform="feishu",
        )

    def create_import_task(
        self,
        markdown_content: str,
        file_name: str,
    ) -> str:
        """创建导入任务，将 Markdown 导入为飞书文档。

        当前飞书链路需要：
        1. 创建一个目录挂载点，作为导入后文档的落点
        2. 通过 media.upload_all 上传源文件，获取 file_token
        3. 通过 import_tasks 创建导入任务
        """
        md_bytes = markdown_content.encode("utf-8")
        folder_body = CreateFolderFileRequestBody.builder() \
            .name("Eko Imports") \
            .folder_token("") \
            .build()
        folder_request = CreateFolderFileRequest.builder() \
            .request_body(folder_body) \
            .build()
        folder_response = self._client.drive.v1.file.create_folder(folder_request)
        if not folder_response.success():
            raise Exception(
                f"Failed to create import folder: {folder_response.code}, {folder_response.msg}, {folder_response.request_id}"
            )

        upload_body = UploadAllMediaRequestBody.builder() \
            .file_name(f"{file_name}.md") \
            .parent_type("ccm_import_open") \
            .size(len(md_bytes)) \
            .extra(json.dumps({"obj_type": "docx", "file_extension": "md"})) \
            .file(io.BytesIO(md_bytes)) \
            .build()

        upload_request = UploadAllMediaRequest.builder() \
            .request_body(upload_body) \
            .build()

        upload_response = self._client.drive.v1.media.upload_all(upload_request)
        if not upload_response.success():
            if upload_response.code == 1061004:
                raise FeishuPermissionError(
                    "飞书应用缺少文件上传/云文档导入权限，无法上传导入源文件。"
                )
            raise Exception(
                f"Failed to upload source file: {upload_response.code}, {upload_response.msg}, {upload_response.request_id}"
            )

        mount_point = ImportTaskMountPoint.builder() \
            .mount_type(1) \
            .mount_key(folder_response.data.token) \
            .build()

        import_task = ImportTask.builder() \
            .file_extension("md") \
            .file_name(file_name) \
            .type("docx") \
            .file_token(upload_response.data.file_token) \
            .point(mount_point) \
            .build()

        request = CreateImportTaskRequest.builder() \
            .request_body(import_task) \
            .build()

        response = self._client.drive.v1.import_task.create(request)
        if not response.success():
            raise Exception(
                f"Failed to create import task: {response.code}, {response.msg}, {response.request_id}"
            )

        return response.data.ticket

    def get_import_task_result(self, ticket: str) -> dict[str, Any] | None:
        """查询导入任务结果

        Args:
            ticket: 导入任务 ticket

        Returns:
            成功返回包含 url 和 token 的字典，失败返回 None，进行中返回 None
        """
        request = GetImportTaskRequest.builder() \
            .ticket(ticket) \
            .build()

        response = self._client.drive.v1.import_task.get(request)

        if not response.success():
            raise Exception(
                f"Failed to get import task: {response.code}, {response.msg}, {response.request_id}"
            )

        result = response.data.result

        # 导入状态: 0-成功, 1-处理中, 2-导入中间态（当前实测会短暂出现）
        if result.job_status in (1, 2):
            return None
        if result.job_status != 0:
            raise FeishuImportTaskFailedError(
                getattr(result, "job_error_msg", None)
                or response.msg
                or "Import task failed"
            )

        return {
            "url": result.url,
            "token": result.token,
        }

    def get_import_task_status(self, ticket: str) -> dict[str, Any]:
        """查询导入任务状态，保留处理中/失败/成功三态"""
        request = GetImportTaskRequest.builder() \
            .ticket(ticket) \
            .build()

        response = self._client.drive.v1.import_task.get(request)

        if not response.success():
            raise Exception(
                f"Failed to get import task: {response.code}, {response.msg}, {response.request_id}"
            )

        result = response.data.result

        if result.job_status == 0:
            return {
                "ticket": ticket,
                "status": "success",
                "document_url": result.url,
            }
        if result.job_status in (1, 2):
            return {
                "ticket": ticket,
                "status": "processing",
                "document_url": None,
            }
        if result.job_status < 0:
            return {
                "ticket": ticket,
                "status": "failed",
                "document_url": None,
            }

        raise Exception(f"Unexpected import task status: {result.job_status}")

    def create_bitable_record(
        self,
        app_token: str,
        table_id: str,
        fields: dict[str, Any],
    ) -> str:
        """在多维表格中创建新记录

        Args:
            app_token: 多维表格应用 token
            table_id: 数据表 ID
            fields: 字段值字典，格式 {field_name: value}

        Returns:
            新记录 ID
        """
        # 新 SDK 用法
        record = AppTableRecord.builder() \
            .fields(fields) \
            .build()

        request = CreateAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .request_body(record) \
            .build()

        response = self._client.bitable.v1.app_table_record.create(request)

        if not response.success():
            raise Exception(
                f"Failed to create bitable record: {response.code}, {response.msg}, {response.request_id}"
            )

        return response.data.record.record_id
