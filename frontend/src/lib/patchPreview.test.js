import test from 'node:test'
import assert from 'node:assert/strict'

import { describeGenerationInfo, describePatch, formatElapsedMs } from './patchPreview.js'

test('describePatch summarizes targeted patch operations in natural Chinese', () => {
  const patch = {
    generation_mode: 'targeted_patch',
    summary: '为当前节点补充后续动作',
    operations: [
      {
        type: 'node.replace',
        target: 'node-1',
        content: '更清晰的总结',
      },
      {
        type: 'node.add',
        node: {
          id: 'node-2',
          text: '后续跟进事项',
        },
      },
      {
        type: 'edge.add',
        edge: {
          id: 'edge-1',
          from: 'node-1',
          to: 'node-2',
        },
      },
    ],
  }

  assert.deepEqual(describePatch(patch), [
    '这次是局部编辑。',
    '会把节点 node-1 改写成“更清晰的总结”。',
    '会新增节点“后续跟进事项”。',
    '会补一条连接线，把 node-1 连到 node-2。',
    '为当前节点补充后续动作',
  ])
})

test('describePatch summarizes full board generation', () => {
  const patch = {
    generation_mode: 'full_board',
    summary: '生成了一张新的执行计划画板',
    full_board: {
      nodes: [
        { id: 'n1', text: '准备' },
        { id: 'n2', text: '执行' },
        { id: 'n3', text: '复盘' },
      ],
      edges: [{ id: 'e1' }, { id: 'e2' }],
    },
    operations: [],
  }

  assert.deepEqual(describePatch(patch), [
    '这次是整板生成。',
    '预计会生成 3 个节点和 2 条连线。',
    '节点内容：准备 → 执行 → 复盘。',
    '生成了一张新的执行计划画板',
  ])
})

test('formatElapsedMs returns seconds with one decimal place', () => {
  assert.equal(formatElapsedMs(0), '0.0 秒')
  assert.equal(formatElapsedMs(3876), '3.9 秒')
  assert.equal(formatElapsedMs(6123), '6.1 秒')
})

test('describeGenerationInfo summarizes real model generation', () => {
  assert.deepEqual(
    describeGenerationInfo({
      source: 'ai',
      provider: 'volcengine',
      model: 'ep-test-model',
      latency_ms: 3876,
    }),
    ['本次走的是真实模型。', '模型来源：volcengine / ep-test-model。', '后端生成耗时 3.9 秒。'],
  )
})

test('describeGenerationInfo ignores unknown generation sources but keeps latency', () => {
  assert.deepEqual(describeGenerationInfo({ source: 'unknown', latency_ms: 24 }), [
    '后端生成耗时 0.0 秒。',
  ])
})
