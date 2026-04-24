"""
飞书长连接 WebSocket 服务
使用 SDK 长连接接收飞书事件
参考官方样例：https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/server-side-sdk/python-sdk/event-subscription-overview
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import re
import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

from app.config import settings
from app.services.intent_service import recognize_intent


def log(msg):
    sys.stdout.write(str(msg) + '\n')
    sys.stdout.flush()


def do_p2_im_message_receive_v1(data: P2ImMessageReceiveV1) -> None:
    """处理收到消息事件"""
    try:
        log('[ Handler called ]')
        message = data.event.message
        if not message:
            log('[ No message ]')
            return

        chat_id = message.chat_id
        message_id = message.message_id
        chat_type = message.chat_type or 'group'
        content = message.content or '{}'

        # 解析文本消息
        if message.message_type == 'text':
            text = json.loads(content).get('text', '')
        else:
            text = ''

        # 过滤掉@ mention
        clean_text = re.sub(r'@_user_\d+\s*', '', text).strip()
        if not clean_text:
            clean_text = text

        # 识别意图
        intent = recognize_intent(clean_text)

        log(f'[ Intent ]: {intent}, [ Text ]: {clean_text}')
        log(f'[ ChatID ]: {chat_id}, [ MessageID ]: {message_id}, [ ChatType ]: {chat_type}')

    except Exception as e:
        import traceback
        log(f'[ Error ]: {e}')
        traceback.print_exc()


def main():
    # 创建 Client 用于 API 调用
    client = lark.Client.builder().app_id(settings.FEISHU_APP_ID).app_secret(settings.FEISHU_APP_SECRET).build()

    # 创建 WebSocket 长连接客户端
    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1)
        .build()
    )

    ws_client = lark.ws.Client(
        settings.FEISHU_APP_ID,
        settings.FEISHU_APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.DEBUG,
    )

    log(f'[ Starting Feishu WebSocket Client ] AppID: {settings.FEISHU_APP_ID}')
    ws_client.start()


if __name__ == "__main__":
    main()