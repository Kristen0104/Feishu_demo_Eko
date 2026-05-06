import type { AgentChatStreamEvent } from "@/lib/agent/sse-stream";

function sseLine(event: AgentChatStreamEvent): string {
  return `data: ${JSON.stringify(event)}\n\n`;
}

export function encodeAgentChatDemoStream(events: AgentChatStreamEvent[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const payload = events.map(sseLine).join("");
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(payload));
      controller.close();
    },
  });
}

/** Generic SSE lines `data: {...}\\n\\n` for document/generate/stream mocks. */
export function encodeSseJsonLines(lines: unknown[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  const payload = lines.map((obj) => `data: ${JSON.stringify(obj)}\n\n`).join("");
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(payload));
      controller.close();
    },
  });
}
