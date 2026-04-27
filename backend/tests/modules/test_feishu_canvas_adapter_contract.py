from __future__ import annotations

from pathlib import Path

from app.modules.canvas.repository import CanvasRepository
from app.modules.canvas.service import CanvasService
from app.modules.feishu.client import FeishuClient
from app.modules.feishu.publisher import build_publish_nodes
from app.modules.feishu.schemas import (
    FeishuBoardAdapterPayloadSchema,
    FeishuBoardElementMappingSchema,
    FeishuBoardSourceSchema,
)
from app.modules.feishu.service import FeishuService


def test_feishu_import_generates_working_copy_and_export_round_trips_payload() -> None:
    service = FeishuService(client=FeishuClient())
    payload = FeishuBoardAdapterPayloadSchema(
        session_id="canvas-feishu-001",
        source_board=FeishuBoardSourceSchema(
            board_id="source-board-001",
            title="产品路线图",
            nodes=[
                {"id": "node-1", "text": "需求收集"},
                {"id": "node-2", "text": "方案设计"},
            ],
            edges=[
                {"id": "edge-1", "from": "node-1", "to": "node-2", "type": "next"}
            ],
        ),
        element_mappings=[
            FeishuBoardElementMappingSchema(
                source_element_id="node-1",
                working_element_id="node-1",
                element_type="node",
            ),
            FeishuBoardElementMappingSchema(
                source_element_id="edge-1",
                working_element_id="edge-1",
                element_type="edge",
            ),
        ],
    )

    imported = service.import_board(payload)

    assert imported.working_board is not None
    assert imported.working_board.session_id == "canvas-feishu-001"
    assert imported.working_board.latest_snapshot["nodes"][0]["text"] == "需求收集"
    assert imported.working_board.latest_snapshot["edges"][0]["from"] == "node-1"

    exported = service.export_board(imported)

    assert exported.source_board.board_id == "source-board-001"
    assert exported.source_board.nodes[1]["text"] == "方案设计"
    assert exported.source_board.edges[0]["to"] == "node-2"
    assert exported.element_mappings[0].working_element_id == "node-1"


def test_feishu_publish_nodes_use_canvas_style_template_fields() -> None:
    payload = FeishuBoardAdapterPayloadSchema(
        session_id="canvas-feishu-publish-style",
        source_board=FeishuBoardSourceSchema(
            board_id="source-board-publish-style",
            title="Styled board",
            nodes=[
                {
                    "id": "decision",
                    "type": "note",
                    "text": "是否继续?",
                    "x": 120,
                    "y": 120,
                    "width": 240,
                    "height": 180,
                    "shape_kind": "flow_chart_diamond",
                    "style": {
                        "fill_color": "#fff7ed",
                        "border_color": "#f59e0b",
                        "border_style": "solid",
                        "border_width": "medium",
                    },
                    "font_weight": "bold",
                },
                {
                    "id": "end",
                    "type": "topic",
                    "text": "结束",
                    "x": 480,
                    "y": 120,
                    "style": {"fill_color": "#eef2ff", "border_color": "#4f46e5"},
                },
            ],
            edges=[
                {
                    "id": "edge-1",
                    "from": "decision",
                    "to": "end",
                    "label": "是",
                    "shape": "right_angled_polyline",
                    "arrow_style": "triangle_arrow",
                    "style": {"border_color": "#9ca3af", "border_width": "narrow"},
                }
            ],
        ),
    )

    nodes = build_publish_nodes(payload)

    decision = nodes[0]
    connector = nodes[2]["connector"]
    assert decision["type"] == "composite_shape"
    assert decision["composite_shape"]["type"] == "flow_chart_diamond"
    assert decision["style"]["border_color"] == "#f59e0b"
    assert decision["text"]["font_weight"] == "bold"
    assert connector["shape"] == "right_angled_polyline"
    assert connector["end"]["arrow_style"] == "triangle_arrow"
    assert connector["style"]["border_color"] == "#9ca3af"


def test_feishu_publish_strips_preview_theme_style_strings() -> None:
    payload = FeishuBoardAdapterPayloadSchema(
        session_id="canvas-feishu-publish-preview-style",
        source_board=FeishuBoardSourceSchema(
            board_id="source-board-publish-preview-style",
            title="Preview style board",
            nodes=[
                {
                    "id": "node-1",
                    "type": "topic",
                    "text": "预览节点",
                    "style": {
                        "fill_color": "#dbeafe",
                        "border_color": "#2563eb",
                        "theme_fill_color_code": "gray1",
                        "theme_border_color_code": "blue",
                        "fill_opacity": 100,
                        "border_opacity": 100,
                    },
                },
                {
                    "id": "node-2",
                    "type": "topic",
                    "text": "目标节点",
                    "style": {
                        "theme_fill_color_code": 3,
                        "theme_border_color_code": 5,
                    },
                },
            ],
            edges=[
                {
                    "id": "edge-1",
                    "from": "node-1",
                    "to": "node-2",
                    "style": {
                        "border_color": "#64748b",
                        "theme_border_color_code": "blue",
                        "border_opacity": 100,
                    },
                }
            ],
        ),
    )

    nodes = build_publish_nodes(payload)

    source_style = nodes[0]["style"]
    target_style = nodes[1]["style"]
    connector_style = nodes[2]["connector"]["style"]
    assert source_style["fill_color"] == "#dbeafe"
    assert source_style["border_color"] == "#2563eb"
    assert "theme_fill_color_code" not in source_style
    assert "theme_border_color_code" not in source_style
    assert target_style["theme_fill_color_code"] == 3
    assert target_style["theme_border_color_code"] == 5
    assert "theme_border_color_code" not in connector_style


def test_feishu_publish_start_and_end_nodes_keep_visible_text() -> None:
    payload = FeishuBoardAdapterPayloadSchema(
        session_id="canvas-feishu-publish-terminals",
        source_board=FeishuBoardSourceSchema(
            board_id="source-board-publish-terminals",
            title="Terminal board",
            nodes=[
                {
                    "id": "start",
                    "type": "topic",
                    "text": "开始",
                    "x": 100,
                    "y": 100,
                    "width": 180,
                    "height": 80,
                    "visual_role": "start",
                    "shape_kind": "state_start",
                },
                {
                    "id": "end",
                    "type": "topic",
                    "text": "结束",
                    "x": 420,
                    "y": 100,
                    "width": 180,
                    "height": 80,
                    "visual_role": "end",
                    "shape_kind": "state_end",
                },
            ],
            edges=[{"id": "edge-1", "from": "start", "to": "end"}],
        ),
    )

    nodes = build_publish_nodes(payload)

    start = nodes[0]
    end = nodes[1]
    assert start["composite_shape"]["type"] == "flow_chart_round_rect"
    assert start["text"]["text"] == "开始"
    assert end["composite_shape"]["type"] == "flow_chart_round_rect"
    assert end["text"]["text"] == "结束"


def test_feishu_publish_does_not_infer_huge_turning_points_for_branches() -> None:
    payload = FeishuBoardAdapterPayloadSchema(
        session_id="canvas-feishu-publish-branches",
        source_board=FeishuBoardSourceSchema(
            board_id="source-board-publish-branches",
            title="Branch board",
            nodes=[
                {
                    "id": "decision",
                    "type": "note",
                    "text": "是否继续?",
                    "x": 300,
                    "y": 180,
                    "width": 180,
                    "height": 140,
                    "shape_kind": "flow_chart_diamond",
                },
                {
                    "id": "yes",
                    "type": "note",
                    "text": "继续",
                    "x": 620,
                    "y": 180,
                    "width": 180,
                    "height": 90,
                },
                {
                    "id": "no",
                    "type": "note",
                    "text": "返回补充",
                    "x": 620,
                    "y": 400,
                    "width": 180,
                    "height": 90,
                },
            ],
            edges=[
                {"id": "edge-yes", "from": "decision", "to": "yes", "label": "是"},
                {"id": "edge-no", "from": "decision", "to": "no", "label": "否"},
            ],
        ),
    )

    nodes = build_publish_nodes(payload)
    connectors = {node["id"]: node["connector"] for node in nodes if node["type"] == "connector"}

    assert "turning_points" not in connectors["edge-yes"]
    assert "turning_points" not in connectors["edge-no"]
    assert connectors["edge-yes"]["start"]["attached_object"]["snap_to"] == "right"
    assert connectors["edge-no"]["start"]["attached_object"]["snap_to"] == "bottom"
    assert connectors["edge-no"]["end"]["attached_object"]["snap_to"] == "top"
    assert connectors["edge-no"]["start"]["attached_object"]["position"] == {"x": 0.5, "y": 1.0}


def test_feishu_publish_does_not_force_no_branch_down_when_target_is_above() -> None:
    payload = FeishuBoardAdapterPayloadSchema(
        session_id="canvas-feishu-publish-no-above",
        source_board=FeishuBoardSourceSchema(
            board_id="source-board-publish-no-above",
            title="No branch above board",
            nodes=[
                {
                    "id": "decision",
                    "type": "note",
                    "text": "是否在家吃?",
                    "x": 300,
                    "y": 300,
                    "width": 180,
                    "height": 140,
                    "shape_kind": "flow_chart_diamond",
                },
                {
                    "id": "no",
                    "type": "note",
                    "text": "手机查找想吃的餐厅",
                    "x": 560,
                    "y": 180,
                    "width": 240,
                    "height": 90,
                },
            ],
            edges=[{"id": "edge-no", "from": "decision", "to": "no", "label": "否"}],
        ),
    )

    nodes = build_publish_nodes(payload)
    connector = next(node["connector"] for node in nodes if node["id"] == "edge-no")

    assert "turning_points" not in connector
    assert connector["start"]["attached_object"]["snap_to"] == "right"
    assert connector["end"]["attached_object"]["snap_to"] == "left"


def test_feishu_publish_routes_same_row_return_edges_as_curves() -> None:
    payload = FeishuBoardAdapterPayloadSchema(
        session_id="canvas-feishu-publish-return-edge",
        source_board=FeishuBoardSourceSchema(
            board_id="source-board-publish-return-edge",
            title="Return edge board",
            nodes=[
                {
                    "id": "previous",
                    "type": "topic",
                    "text": "系好安全带，启动车辆",
                    "x": 1268,
                    "y": 196,
                    "width": 352,
                    "height": 88,
                },
                {
                    "id": "decision",
                    "type": "note",
                    "text": "车辆是否有故障告警",
                    "x": 1716,
                    "y": 150,
                    "width": 240,
                    "height": 180,
                    "shape_kind": "flow_chart_diamond",
                },
                {
                    "id": "fix",
                    "type": "topic",
                    "text": "排查故障或呼叫救援",
                    "x": 2052,
                    "y": 196,
                    "width": 324,
                    "height": 88,
                },
            ],
            edges=[
                {
                    "id": "edge-return",
                    "from": "fix",
                    "to": "previous",
                    "label": "故障排除后",
                    "shape": "right_angled_polyline",
                }
            ],
        ),
    )

    nodes = build_publish_nodes(payload)
    connector = next(node["connector"] for node in nodes if node["id"] == "edge-return")

    assert connector["shape"] == "curve"
    assert connector["caption_position"] == 0.25
    assert connector["start"]["attached_object"]["snap_to"] == "bottom"
    assert connector["end"]["attached_object"]["snap_to"] == "bottom"


def test_feishu_publish_vertical_connector_aligns_attachment_positions() -> None:
    payload = FeishuBoardAdapterPayloadSchema(
        session_id="canvas-feishu-publish-vertical",
        source_board=FeishuBoardSourceSchema(
            board_id="source-board-publish-vertical",
            title="Vertical board",
            nodes=[
                {
                    "id": "top",
                    "type": "note",
                    "text": "扫码点单等待上菜",
                    "x": 100,
                    "y": 100,
                    "width": 320,
                    "height": 90,
                },
                {
                    "id": "bottom",
                    "type": "note",
                    "text": "用餐完成后结账",
                    "x": 180,
                    "y": 520,
                    "width": 280,
                    "height": 90,
                },
            ],
            edges=[{"id": "edge-vertical", "from": "top", "to": "bottom"}],
        ),
    )

    nodes = build_publish_nodes(payload)
    connector = next(node["connector"] for node in nodes if node["id"] == "edge-vertical")

    assert connector["start"]["attached_object"]["snap_to"] == "bottom"
    assert connector["end"]["attached_object"]["snap_to"] == "top"
    assert connector["start"]["attached_object"]["position"] == {"x": 0.59375, "y": 1.0}
    assert connector["end"]["attached_object"]["position"] == {"x": 0.392857, "y": 0.0}


def test_canvas_can_ingest_feishu_adapter_result_into_detail_and_working_board(
    tmp_path: Path,
) -> None:
    service = FeishuService(client=FeishuClient())
    canvas_repository = CanvasRepository(storage_dir=tmp_path / "canvas")
    canvas_service = CanvasService(repository=canvas_repository)
    imported = service.import_board(
        FeishuBoardAdapterPayloadSchema(
            session_id="canvas-feishu-002",
            source_board=FeishuBoardSourceSchema(
                board_id="source-board-002",
                title="协作看板",
                nodes=[{"id": "node-1", "text": "同步需求"}],
                edges=[],
            ),
        )
    )

    canvas_service.ingest_feishu_board("canvas-feishu-002", imported)
    detail = canvas_service.get_session_detail("canvas-feishu-002")

    assert detail.source_board.raw_payload["source_board"]["board_id"] == "source-board-002"
    assert detail.working_board.latest_snapshot["nodes"][0]["text"] == "同步需求"
    assert detail.recent_changes[0].change_type == "source_import"


def test_document_whiteboard_nodes_can_be_translated_into_adapter_payload() -> None:
    from tests.modules.test_feishu_document_contract import DummyHttpClient

    service = FeishuService(
        client=FeishuClient(
            http_client=DummyHttpClient(),
            access_token_provider=lambda: "tenant-token-001",
        )
    )

    adapted = service.resolve_document_whiteboard_import_payload(
        share_url="https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg",
        session_id="canvas-feishu-003",
    )

    assert adapted.session_id == "canvas-feishu-003"
    assert adapted.source_board.board_id == "wb-first"
    assert adapted.source_board.title == "产品路线图"
    assert adapted.source_board.nodes[0]["id"] == "node-1"
    assert adapted.source_board.nodes[0]["text"] == "Start"
    assert adapted.source_board.nodes[0]["node_id"] == "node-1"
    assert adapted.source_board.nodes[0]["type"] == "text_shape"
    assert adapted.source_board.nodes[0]["width"] == 240
    assert adapted.source_board.nodes[1]["id"] == "node-2"
    assert adapted.source_board.nodes[1]["height"] == 64
    assert adapted.source_board.metadata["source_type"] == "feishu_document_whiteboard"
    assert (
        adapted.source_board.metadata["share_url"]
        == "https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg"
    )
    assert (
        adapted.source_board.metadata["document_id"] == "QFQVd8EEnoD58zxNwLNcmJRJnAg"
    )
    assert adapted.source_board.metadata["document_token"] == "QFQVd8EEnoD58zxNwLNcmJRJnAg"
    assert adapted.source_board.metadata["whiteboard_id"] == "wb-first"
    assert adapted.source_board.metadata["block_id"] == "block-2"
    assert (
        adapted.source_board.metadata["source_version"]
        == "feishu-doc-blocks:QFQVd8EEnoD58zxNwLNcmJRJnAg:block-2:wb-first"
    )
    assert adapted.source_board.metadata["raw_document"]["document_id"] == (
        "QFQVd8EEnoD58zxNwLNcmJRJnAg"
    )
    assert adapted.source_board.metadata["raw_whiteboard"]["whiteboard_id"] == "wb-first"
    assert adapted.working_board is not None
    assert adapted.working_board.latest_snapshot["nodes"][0]["id"] == "node-1"
    assert adapted.working_board.latest_snapshot["nodes"][0]["type"] == "text_shape"
    assert adapted.element_mappings[0].source_element_id == "node-1"
    assert adapted.element_mappings[0].origin_type == "source_import"
    assert adapted.element_mappings[0].mapping_status == "active"
    assert adapted.element_mappings[0].metadata == {
        "source_type": "feishu_document_whiteboard",
        "document_id": "QFQVd8EEnoD58zxNwLNcmJRJnAg",
        "whiteboard_id": "wb-first",
        "block_id": "block-2",
    }


def test_translated_document_whiteboard_payload_can_be_ingested_by_canvas(
    tmp_path: Path,
) -> None:
    from tests.modules.test_feishu_document_contract import DummyHttpClient

    feishu_service = FeishuService(
        client=FeishuClient(
            http_client=DummyHttpClient(),
            access_token_provider=lambda: "tenant-token-001",
        )
    )
    canvas_service = CanvasService(repository=CanvasRepository(storage_dir=tmp_path / "canvas"))

    adapted = feishu_service.resolve_document_whiteboard_import_payload(
        share_url="https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg",
        session_id="canvas-feishu-004",
    )
    detail = canvas_service.ingest_feishu_board("canvas-feishu-004", adapted)

    assert detail.source_board.source_board_id == "wb-first"
    assert detail.source_board.source_version == (
        "feishu-doc-blocks:QFQVd8EEnoD58zxNwLNcmJRJnAg:block-2:wb-first"
    )
    assert detail.source_board.raw_payload["source_metadata"]["document_id"] == (
        "QFQVd8EEnoD58zxNwLNcmJRJnAg"
    )
    assert detail.source_board.raw_payload["source_metadata"]["block_id"] == "block-2"
    assert detail.working_board.latest_snapshot["nodes"][1]["text"] == "Discuss"
    assert detail.element_mappings[0].source_element_id == "node-1"
    assert detail.element_mappings[0].working_element_id == "node-1"
    assert detail.element_mappings[0].origin_type == "source_import"
    assert detail.recent_changes[0].payload["source_board"]["board_id"] == "wb-first"
    assert detail.recent_changes[0].actor_type == "feishu"
    assert detail.recent_changes[0].actor_id == "wb-first"
    assert detail.recent_changes[0].target_scope == "board:wb-first"
    assert (
        detail.recent_changes[0].payload["source_board"]["metadata"]["whiteboard_id"]
        == "wb-first"
    )
    assert detail.recent_changes[0].payload["element_mappings"][0]["origin_type"] == (
        "source_import"
    )
