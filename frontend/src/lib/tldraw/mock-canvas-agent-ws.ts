/**
 * 画布 Agent「远端推送」对接说明（当前为 `streamAgentStoryboard` 内 `sleep` 模拟）。
 *
 * 生产环境将 `await sleep(mockWsMessageGapMs)` 换成「下一条 WebSocket 消息到达」，
 * 再执行与现有一致的：createShapes（初始透明）→ `editor.animateShapes` 揭示。
 */

export {};
