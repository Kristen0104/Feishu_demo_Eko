from fastapi.routing import APIRoute

from app.core.security import get_auth_context
from app.modules.bitable.router import router


def test_all_bitable_routes_require_auth_context() -> None:
    routes = [route for route in router.routes if isinstance(route, APIRoute)]

    assert routes
    for route in routes:
        dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
        assert get_auth_context in dependency_calls, route.path
