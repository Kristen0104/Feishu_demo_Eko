"""
意图识别服务模块
根据用户消息关键词识别意图类型：
- DOC: 需要创建 Word/文档
- PPT: 需要创建 PPT/演示文稿
- SUMMARY: 需要生成摘要
- CHAT: 普通闲聊/问答
"""

import re


INTENT_KEYWORDS = {
    "DOC": [
        "文档", "文稿", "方案", "报告", "撰写", "写一个", "生成文档",
        "word", "生成word", "整理成文档", "输出文档", "形成文档"
    ],
    "PPT": [
        "ppt", "演示", "汇报", "展示", "幻灯片", "生成ppt", "做ppt",
        "演示文稿", "做成ppt", "输出ppt"
    ],
    "SUMMARY": [
        "总结", "摘要", "概括", "提炼", "汇总", "归纳", "整理要点",
        "核心观点", "主要结论", "归纳一下"
    ],
}


def recognize_intent(message: str) -> str:
    """
    根据消息内容识别意图

    Returns:
        DOC: 需要创建 Word/文档
        PPT: 需要创建 PPT/演示
        SUMMARY: 需要生成摘要
        CHAT: 闲聊/普通问答
    """
    msg_lower = message.lower()

    # 先检查关键词匹配
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in msg_lower:
                return intent

    # 检查是否要求基于前文创建
    if any(phrase in message for phrase in ["根据", "基于", "按照", "依据"]):
        if any(word in message for word in ["上文", "前文", "刚才", "讨论", "内容"]):
            # 有基于前文的指示，检查是要生成什么
            for intent, keywords in INTENT_KEYWORDS.items():
                for kw in keywords:
                    if kw.lower() in msg_lower:
                        return intent

    return "CHAT"


def extract_intent_keywords(message: str) -> dict:
    """提取匹配到的意图关键词"""
    msg_lower = message.lower()
    matched = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        hits = [kw for kw in keywords if kw.lower() in msg_lower]
        if hits:
            matched[intent] = hits
    return matched
