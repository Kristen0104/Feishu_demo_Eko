type Emit = (sessionId: string, raw: unknown) => void;

/**
 * Deterministic demo sequence compatible with backend-style envelopes (same keys as WS payload).
 */
export function runProtocolMockSequence(sessionId: string, emit: Emit): () => void {
  const timers: number[] = [];

  const schedule = (ms: number, fn: () => void) => {
    const id = window.setTimeout(fn, ms);
    timers.push(id);
  };

  schedule(400, () => {
    emit(sessionId, {
      type: "INTENT_RECOGNIZED",
      session_id: sessionId,
      payload: { intent: "DOC" },
    });
  });

  schedule(1200, () => {
    emit(sessionId, {
      type: "AGENT_PLANNING",
      session_id: sessionId,
      payload: {
        steps: [
          { id: "1", title: "意图解析", status: "completed" },
          { id: "2", title: "检索上下文", status: "running" },
          { id: "3", title: "结构化生成", status: "pending" },
          { id: "4", title: "同步飞书", status: "pending" },
        ],
      },
    });
  });

  schedule(2200, () => {
    emit(sessionId, {
      type: "AGENT_PLANNING",
      session_id: sessionId,
      payload: {
        steps: [
          { id: "1", title: "意图解析", status: "completed" },
          { id: "2", title: "检索上下文", status: "completed" },
          { id: "3", title: "结构化生成", status: "running" },
          { id: "4", title: "同步飞书", status: "pending" },
        ],
      },
    });
  });

  const mdChunks = [
    "## 实时草稿\n\n",
    "以下为 **协议兼容 mock** 推送的 Markdown 片段，联调真实 WS / SSE 后将替换为服务端内容。\n\n",
    "### 要点\n\n",
    "- WebSocket 可用时由服务端推送 `DOC_STREAM`\n",
    "- 不可用时使用本演示序列保持 UI 可验收\n\n",
    "---\n\n",
    "> 与「Word 预览」共用同一 `docMarkdownStream` 数据源。\n",
  ];

  let t = 3200;
  for (const chunk of mdChunks) {
    schedule(t, () => {
      emit(sessionId, {
        type: "DOC_STREAM",
        session_id: sessionId,
        payload: { chunk },
      });
    });
    t += 280;
  }

  schedule(t + 400, () => {
    emit(sessionId, {
      type: "AGENT_PLANNING",
      session_id: sessionId,
      payload: {
        steps: [
          { id: "1", title: "意图解析", status: "completed" },
          { id: "2", title: "检索上下文", status: "completed" },
          { id: "3", title: "结构化生成", status: "completed" },
          { id: "4", title: "同步飞书", status: "running" },
        ],
      },
    });
  });

  schedule(t + 1400, () => {
    emit(sessionId, { type: "TASK_COMPLETED", session_id: sessionId, payload: {} });
  });

  return () => {
    for (const id of timers) window.clearTimeout(id);
  };
}
