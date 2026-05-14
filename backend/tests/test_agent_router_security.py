from fastapi.routing import APIRoute

from app.core.security import AuthContext, get_auth_context
from app.modules.agent.router import _with_authenticated_sender, router
from app.modules.agent.schemas import AgentChatRequest


def test_agent_chat_routes_require_auth_context() -> None:
    routes = [
        route
        for route in router.routes
        if isinstance(route, APIRoute) and route.path in {"/chat", "/chat/stream"}
    ]

    assert {route.path for route in routes} == {"/chat", "/chat/stream"}
    for route in routes:
        dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
        assert get_auth_context in dependency_calls, route.path


def test_authenticated_sender_overrides_client_user_scope() -> None:
    request = AgentChatRequest(
        session_id="session_1",
        message="查一下项目排期",
        sender={"platform_user_id": "spoofed", "sender_open_id": "ou_spoofed", "workspace_id": "custom_workspace"},
    )

    next_request = _with_authenticated_sender(
        request,
        AuthContext(user_id="user_real", feishu_user_id="ou_real"),
    )

    assert next_request.sender is not None
    assert next_request.sender["platform_user_id"] == "user_real"
    assert next_request.sender["sender_open_id"] == "ou_real"
    assert next_request.sender["workspace_id"] == "custom_workspace"
