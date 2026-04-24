"""
飞书 Webhook 回调 API 模块
接收飞书平台事件回调（HTTP 模式备用，长连接模式主要使用 feishu_ws.py）
"""
import httpx
from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from app.config import settings
from app.services.feishu_service import fetch_group_messages, parse_message_content, get_tenant_token
from app.services.intent_service import recognize_intent

router = APIRouter()


async def reply_message(chat_id: str, message_id: str, content: str) -> bool:
    """回复消息到群聊"""
    try:
        token = await get_tenant_token()
        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "msg_type": "text",
            "content": content,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            return resp.status_code == 200
    except Exception:
        return False


@router.post("/feishu")
async def feishu_webhook(request: Request) -> JSONResponse:
    """飞书事件回调入口"""
    try:
        event_data = await request.json()
    except Exception:
        return JSONResponse({"code": 1, "msg": "Invalid JSON"}, status_code=400)

    if "challenge" in event_data:
        return JSONResponse({"challenge": event_data["challenge"]})

    event_type = event_data.get("event", {}).get("type")
    if event_type == "im.message.receive_v1":
        return await handle_message_received(event_data)
    else:
        return JSONResponse({"code": 0, "msg": "event received"})


async def handle_message_received(event_data: dict) -> JSONResponse:
    """处理收到消息事件"""
    try:
        event = event_data["event"]
        message = event["message"]
        chat_id = message["chat_id"]
        message_id = message["message_id"]
        sender = event.get("sender", {})
        sender_id = sender.get("sender_id", {}).get("open_id", "")
        chat_type = message.get("chat_type", "group")

        text = parse_message_content(message)
        intent = recognize_intent(text)

        # 过滤掉@ mention，只保留实际消息内容
        clean_text = text
        if "@_user_" in text:
            # 去掉 @_user_X 部分
            import re
            clean_text = re.sub(r'@_user_\d+\s*', '', text).strip()
            if not clean_text:
                clean_text = text

        # 重新识别意图
        if clean_text != text:
            intent = recognize_intent(clean_text)

        # 回复意图识别结果
        intent_text = {
            "DOC": "我已识别您的意图为【文档生成】，正在准备为您生成 Word 文稿...",
            "PPT": "我已识别您的意图为【演示文稿生成】，正在准备为您生成 PPT...",
            "SUMMARY": "我已识别您的意图为【摘要生成】，正在为您总结...",
            "CHAT": "我已收到您的消息，正在思考回复..."
        }.get(intent, f"收到消息，意图识别为: {intent}")

        # 回复消息
        content_str = f'{{"text":"{intent_text}"}}'
        await reply_message(chat_id, message_id, content_str)

        # 如果是创作类意图，获取群聊天记录作为上下文
        chat_history = []
        if intent in ("DOC", "PPT", "SUMMARY"):
            messages = await fetch_group_messages(chat_id, page_size=50)
            chat_history = [
                {
                    "message_id": m["message_id"],
                    "sender_id": m.get("sender", {}).get("id"),
                    "content": parse_message_content(m),
                    "create_time": m.get("create_time"),
                }
                for m in messages.get("items", [])
            ]

        return JSONResponse({
            "code": 0,
            "msg": "ok",
            "data": {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "clean_text": clean_text,
                "sender": sender_id,
                "intent": intent,
                "chat_type": chat_type,
                "chat_history": chat_history,
            }
        })

    except KeyError as e:
        return JSONResponse({"code": 1, "msg": f"Missing field: {e}"})
    except Exception as e:
        return JSONResponse({"code": 1, "msg": str(e)})
