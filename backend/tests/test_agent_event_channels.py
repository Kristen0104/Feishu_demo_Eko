from app.modules.agent.events import AgentEventProtocol


def test_result_created_chat_response_uses_chat_channel():
    event = AgentEventProtocol.result(
        {"session_id": "s1", "intent": "chat", "status": "completed", "message": "ok"},
        "ok",
    )

    assert event["event"] == "result.created"
    assert event["channel"] == "chat"
    assert event["visibility"] == "user"


def test_result_created_docx_artifact_uses_artifact_channel():
    event = AgentEventProtocol.result(
        {
            "session_id": "s1",
            "intent": "docx",
            "status": "completed",
            "message": "文档完成",
            "artifact": {"kind": "docx", "content": "# title"},
        },
        "文档完成",
    )

    assert event["event"] == "result.created"
    assert event["channel"] == "artifact"
    assert event["visibility"] == "user"


def test_result_created_ppt_artifact_uses_artifact_channel():
    event = AgentEventProtocol.result(
        {
            "session_id": "s1",
            "intent": "ppt",
            "status": "completed",
            "artifact": {"kind": "ppt", "job_id": "job1"},
        },
        "PPT 已创建",
    )

    assert event["event"] == "result.created"
    assert event["channel"] == "artifact"
    assert event["visibility"] == "user"


def test_result_created_board_artifact_uses_artifact_channel():
    event = AgentEventProtocol.result(
        {
            "session_id": "s1",
            "intent": "board",
            "status": "completed",
            "artifact": {"kind": "board", "task_id": "task1"},
        },
        "画板完成",
    )

    assert event["event"] == "result.created"
    assert event["channel"] == "artifact"
    assert event["visibility"] == "user"


def test_result_created_failed_response_uses_error_channel():
    event = AgentEventProtocol.result(
        {
            "session_id": "s1",
            "intent": "docx",
            "status": "failed",
            "error": "boom",
        },
        "失败",
    )

    assert event["event"] == "result.created"
    assert event["channel"] == "error"
    assert event["visibility"] == "user"


def test_result_created_unknown_response_falls_back_to_chat_channel():
    event = AgentEventProtocol.result({"foo": "bar"}, "ok")

    assert event["event"] == "result.created"
    assert event["channel"] == "chat"
    assert event["visibility"] == "user"


def test_turn_failed_keeps_error_channel():
    event = AgentEventProtocol.failed(
        {"session_id": "s1", "intent": "docx", "status": "failed"},
        "失败",
        "boom",
    )

    assert event["event"] == "turn.failed"
    assert event["channel"] == "error"
    assert event["visibility"] == "user"
