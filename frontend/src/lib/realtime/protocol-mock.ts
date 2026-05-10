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
      event: "intent.recognized",
      status: "completed",
      message: "我判断这次要走 docx 能力。",
      payload: { intent: "docx", session_id: sessionId },
    });
  });

  schedule(1200, () => {
    emit(sessionId, {
      event: "plan.created",
      status: "completed",
      message: "规划完成。下面按这些子任务执行。",
      payload: {
        plan: {
          goal: "生成文档",
          intent: "docx",
          task_complexity: "medium",
          missing_info: [],
          need_clarification: false,
          questions: [],
          assumptions: [],
          summary: "我会先理解需求，再检索上下文，最后生成并同步文档。",
          steps: [
            { id: "1", title: "意图解析", status: "completed" },
            { id: "2", title: "检索上下文", status: "running" },
            { id: "3", title: "结构化生成", status: "pending" },
            { id: "4", title: "同步飞书", status: "pending" },
          ],
        },
      },
    });
  });

  schedule(2200, () => {
    emit(sessionId, {
      event: "plan.created",
      status: "completed",
      message: "上下文检索完成，进入内容生成。",
      payload: {
        plan: {
          goal: "生成文档",
          intent: "docx",
          task_complexity: "medium",
          missing_info: [],
          need_clarification: false,
          questions: [],
          assumptions: [],
          summary: "我会先理解需求，再检索上下文，最后生成并同步文档。",
          steps: [
            { id: "1", title: "意图解析", status: "completed" },
            { id: "2", title: "检索上下文", status: "completed" },
            { id: "3", title: "结构化生成", status: "running" },
            { id: "4", title: "同步飞书", status: "pending" },
          ],
        },
      },
    });
  });

  const mdChunks = [
    "## 实时草稿\n\n",
    "以下为统一 Agent 事件协议推送的 Markdown 片段，联调真实 WS / SSE 后将替换为服务端内容。\n\n",
    "### 要点\n\n",
    "- WebSocket 可用时由服务端推送 `result.created`\n",
    "- 不可用时使用本演示序列保持 UI 可验收\n\n",
    "---\n\n",
    "> 与「Word 预览」共用同一 `docMarkdownStream` 数据源。\n",
  ];

  let t = 3200;
  for (const chunk of mdChunks) {
    schedule(t, () => {
      emit(sessionId, {
        event: "result.created",
        status: "running",
        message: "文档内容生成中。",
        payload: { response: { artifact: { kind: "docx", content: chunk } }, session_id: sessionId, append: true },
      });
    });
    t += 280;
  }

  schedule(t + 400, () => {
    emit(sessionId, {
      event: "plan.created",
      status: "completed",
      message: "生成完成，准备同步。",
      payload: {
        plan: {
          goal: "生成文档",
          intent: "docx",
          task_complexity: "medium",
          missing_info: [],
          need_clarification: false,
          questions: [],
          assumptions: [],
          summary: "文档内容已生成，开始同步。",
          steps: [
            { id: "1", title: "意图解析", status: "completed" },
            { id: "2", title: "检索上下文", status: "completed" },
            { id: "3", title: "结构化生成", status: "completed" },
            { id: "4", title: "同步飞书", status: "running" },
          ],
        },
      },
    });
  });

  schedule(t + 1400, () => {
    emit(sessionId, {
      event: "result.created",
      status: "completed",
      message: "任务完成。",
      payload: { response: { status: "completed" }, session_id: sessionId },
    });
  });

  return () => {
    for (const id of timers) window.clearTimeout(id);
  };
}
