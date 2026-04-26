from app.shared.schemas.common import ActorSchema


def get_request_actor() -> ActorSchema:
    return ActorSchema(user_id="anonymous", display_name="Anonymous")
