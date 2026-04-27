import test from 'node:test'
import assert from 'node:assert/strict'

import { extractSnapshotFromEditor, snapshotToTldrawShapes } from './canvasSnapshot.js'

test('snapshotToTldrawShapes preserves Feishu node style metadata and previews shape/color', () => {
  const shapes = snapshotToTldrawShapes({
    nodes: [
      {
        id: 'decision-1',
        type: 'note',
        text: '是否下雨',
        x: 100,
        y: 80,
        width: 220,
        height: 120,
        visual_role: 'decision',
        shape_kind: 'flow_chart_diamond',
        font_weight: 'bold',
        style: {
          fill_color: '#fff6ee',
          border_color: '#ffa53d',
          border_style: 'solid',
          border_width: 'medium',
        },
      },
    ],
    edges: [],
  })

  const nodeShape = shapes.find((shape) => shape.type === 'geo')

  assert.equal(nodeShape.props.geo, 'diamond')
  assert.equal(nodeShape.props.color, 'orange')
  assert.deepEqual(nodeShape.meta.style, {
    fill_color: '#fff6ee',
    border_color: '#ffa53d',
    border_style: 'solid',
    border_width: 'medium',
  })
  assert.equal(nodeShape.meta.visual_role, 'decision')
  assert.equal(nodeShape.meta.shape_kind, 'flow_chart_diamond')
  assert.equal(nodeShape.meta.font_weight, 'bold')
})

test('snapshotToTldrawShapes maps clean flow template colors to visible tldraw tokens', () => {
  const shapes = snapshotToTldrawShapes({
    nodes: [
      {
        id: 'start',
        type: 'topic',
        text: '开始',
        style: { fill_color: '#e7f8ef', border_color: '#16a34a' },
      },
      {
        id: 'end',
        type: 'topic',
        text: '结束',
        style: { fill_color: '#eef2ff', border_color: '#4f46e5' },
      },
    ],
    edges: [],
  })

  const nodes = Object.fromEntries(
    shapes.filter((shape) => shape.type === 'geo').map((shape) => [shape.meta.nodeId, shape]),
  )

  assert.equal(nodes.start.props.color, 'green')
  assert.equal(nodes.end.props.color, 'violet')
})

test('snapshotToTldrawShapes maps sunset flow template colors to visible tldraw tokens', () => {
  const shapes = snapshotToTldrawShapes({
    nodes: [
      {
        id: 'start',
        type: 'topic',
        text: '开始',
        style: { fill_color: '#ffedd5', border_color: '#f97316' },
      },
      {
        id: 'step',
        type: 'note',
        text: '执行步骤',
        style: { fill_color: '#fff1f2', border_color: '#e11d48' },
      },
    ],
    edges: [],
  })

  const nodes = Object.fromEntries(
    shapes.filter((shape) => shape.type === 'geo').map((shape) => [shape.meta.nodeId, shape]),
  )

  assert.equal(nodes.start.props.color, 'orange')
  assert.equal(nodes.step.props.color, 'red')
})

test('snapshotToTldrawShapes maps forest and mono templates to visible tldraw tokens', () => {
  const shapes = snapshotToTldrawShapes({
    nodes: [
      {
        id: 'forest-step',
        type: 'note',
        text: '健康步骤',
        style: { fill_color: '#ccfbf1', border_color: '#0f766e' },
      },
      {
        id: 'mono-start',
        type: 'topic',
        text: '开始执行',
        style: { fill_color: '#f1f5f9', border_color: '#475569' },
      },
      {
        id: 'mono-step',
        type: 'note',
        text: '执行任务',
        style: { fill_color: '#dbeafe', border_color: '#2563eb' },
      },
    ],
    edges: [],
  })

  const nodes = Object.fromEntries(
    shapes.filter((shape) => shape.type === 'geo').map((shape) => [shape.meta.nodeId, shape]),
  )

  assert.equal(nodes['forest-step'].props.color, 'green')
  assert.equal(nodes['mono-start'].props.color, 'grey')
  assert.equal(nodes['mono-step'].props.color, 'blue')
})

test('snapshotToTldrawShapes decorates bare start and end nodes for preview', () => {
  const shapes = snapshotToTldrawShapes({
    nodes: [
      { id: 'start', type: 'topic', text: '开始吃饭流程' },
      { id: 'end', type: 'topic', text: '吃饭流程结束' },
    ],
    edges: [],
  })
  const nodes = Object.fromEntries(
    shapes.filter((shape) => shape.type === 'geo').map((shape) => [shape.meta.nodeId, shape]),
  )

  assert.equal(nodes.start.props.geo, 'ellipse')
  assert.equal(nodes.start.props.color, 'green')
  assert.equal(nodes.end.props.geo, 'ellipse')
  assert.equal(nodes.end.props.color, 'violet')
})

test('extractSnapshotFromEditor round-trips Feishu node style metadata', () => {
  const [nodeShape] = snapshotToTldrawShapes({
    nodes: [
      {
        id: 'start-1',
        type: 'topic',
        text: '开始',
        x: 10,
        y: 20,
        width: 240,
        height: 100,
        visual_role: 'start',
        shape_kind: 'flow_chart_round_rect',
        font_size: 16,
        font_weight: 'bold',
        theme_text_color_code: 1,
        theme_text_background_color_code: 2,
        style: {
          fill_color: '#e1eaff',
          border_color: '#4e83fd',
          border_style: 'solid',
          border_width: 'medium',
        },
      },
    ],
    edges: [],
  }).filter((shape) => shape.type === 'geo')

  const snapshot = extractSnapshotFromEditor(
    {
      getCurrentPageShapesSorted: () => [nodeShape],
    },
    { working_board: { latest_snapshot: { edges: [], viewport: { x: 0, y: 0, zoom: 1 } } } },
  )

  assert.equal(snapshot.nodes[0].visual_role, 'start')
  assert.equal(snapshot.nodes[0].shape_kind, 'flow_chart_round_rect')
  assert.equal(snapshot.nodes[0].font_size, 16)
  assert.equal(snapshot.nodes[0].font_weight, 'bold')
  assert.equal(snapshot.nodes[0].theme_text_color_code, 1)
  assert.equal(snapshot.nodes[0].theme_text_background_color_code, 2)
  assert.deepEqual(snapshot.nodes[0].style, {
    fill_color: '#e1eaff',
    border_color: '#4e83fd',
    border_style: 'solid',
    border_width: 'medium',
  })
})

test('extractSnapshotFromEditor round-trips Feishu edge style metadata', () => {
  const shapes = snapshotToTldrawShapes({
    nodes: [
      { id: 'a', type: 'topic', text: 'A', x: 0, y: 0, width: 200, height: 100 },
      { id: 'b', type: 'topic', text: 'B', x: 320, y: 0, width: 200, height: 100 },
    ],
    edges: [
      {
        id: 'edge-1',
        from: 'a',
        to: 'b',
        type: 'association',
        label: '下一步',
        shape: 'right_angled_polyline',
        arrow_style: 'triangle_arrow',
        start_arrow_style: 'none',
        end_arrow_style: 'triangle_arrow',
        style: {
          border_color: '#8f959e',
          border_width: 'narrow',
        },
      },
    ],
  })

  const snapshot = extractSnapshotFromEditor(
    {
      getCurrentPageShapesSorted: () => shapes,
    },
    { working_board: { latest_snapshot: { viewport: { x: 0, y: 0, zoom: 1 } } } },
  )

  assert.equal(snapshot.edges[0].label, '下一步')
  assert.equal(snapshot.edges[0].shape, 'right_angled_polyline')
  assert.equal(snapshot.edges[0].arrow_style, 'triangle_arrow')
  assert.equal(snapshot.edges[0].start_arrow_style, 'none')
  assert.equal(snapshot.edges[0].end_arrow_style, 'triangle_arrow')
  assert.deepEqual(snapshot.edges[0].style, {
    border_color: '#8f959e',
    border_width: 'narrow',
  })
})

test('snapshotToTldrawShapes lays out branched flows in columns instead of a snake row', () => {
  const shapes = snapshotToTldrawShapes({
    nodes: [
      { id: 'prepare', type: 'note', text: '准备乘坐地铁', x: 100, y: 100 },
      { id: 'station', type: 'note', text: '进入地铁站', x: 400, y: 100 },
      {
        id: 'ticket',
        type: 'note',
        text: '是否已购票',
        x: 700,
        y: 100,
        shape_kind: 'flow_chart_diamond',
      },
      { id: 'buy', type: 'note', text: '购票', x: 1000, y: 0 },
      { id: 'ride', type: 'note', text: '刷票进站', x: 1000, y: 100 },
      { id: 'sign', type: 'note', text: '查看线路标识', x: 1300, y: 100 },
      {
        id: 'arrived',
        type: 'note',
        text: '到站了吗',
        x: 1600,
        y: 100,
        shape_kind: 'flow_chart_diamond',
      },
      { id: 'wait', type: 'note', text: '继续乘车', x: 1000, y: 300 },
      { id: 'exit', type: 'note', text: '出站', x: 700, y: 300 },
      { id: 'done', type: 'note', text: '完成乘坐', x: 400, y: 300 },
    ],
    edges: [
      { id: 'e1', from: 'prepare', to: 'station' },
      { id: 'e2', from: 'station', to: 'ticket' },
      { id: 'e3', from: 'ticket', to: 'buy', label: '否' },
      { id: 'e4', from: 'buy', to: 'ride' },
      { id: 'e5', from: 'ticket', to: 'ride', label: '是' },
      { id: 'e6', from: 'ride', to: 'sign' },
      { id: 'e7', from: 'sign', to: 'arrived' },
      { id: 'e8', from: 'arrived', to: 'wait', label: '否' },
      { id: 'e9', from: 'wait', to: 'sign' },
      { id: 'e10', from: 'arrived', to: 'exit', label: '是' },
      { id: 'e11', from: 'exit', to: 'done' },
    ],
  })

  const nodes = Object.fromEntries(
    shapes.filter((shape) => shape.type === 'geo').map((shape) => [shape.meta.nodeId, shape]),
  )

  const centerY = (shape) => shape.y + shape.props.h / 2

  assert.equal(centerY(nodes.station), centerY(nodes.prepare))
  assert.equal(centerY(nodes.ticket), centerY(nodes.prepare))
  assert.equal(centerY(nodes.ride), centerY(nodes.prepare))
  assert.ok(nodes.buy.y < nodes.ticket.y)
  assert.ok(nodes.wait.y > nodes.arrived.y)
  assert.ok(nodes.exit.x > nodes.arrived.x)
  assert.ok(nodes.done.x > nodes.exit.x)
})

test('snapshotToTldrawShapes keeps long flow labels from overlapping decision diamonds', () => {
  const shapes = snapshotToTldrawShapes({
    nodes: [
      { id: 'start', type: 'topic', text: '开始' },
      { id: 'route', type: 'note', text: '查询公交线路，确认乘车点与发车时间' },
      { id: 'at-stop', type: 'note', text: '是否已在公交站?' , shape_kind: 'flow_chart_diamond' },
      { id: 'walk', type: 'note', text: '步行/骑行前往对应公交站' },
      { id: 'wait', type: 'note', text: '在站台等候目标线路公交，确认车辆线路信息' },
      { id: 'pay', type: 'note', text: '车辆到站后有序上车，刷交通卡/扫码支付车费' },
      { id: 'arrived', type: 'note', text: '是否到达目的地站点?', shape_kind: 'flow_chart_diamond' },
      { id: 'hold', type: 'note', text: '握住扶手站稳，留意报站信息，提前到车门等候' },
      { id: 'finish', type: 'note', text: '到站后有序下车，确认随身物品无遗漏' },
      { id: 'end', type: 'topic', text: '结束' },
    ],
    edges: [
      { id: 'e1', from: 'start', to: 'route' },
      { id: 'e2', from: 'route', to: 'at-stop' },
      { id: 'e3', from: 'at-stop', to: 'walk', label: '否' },
      { id: 'e4', from: 'walk', to: 'wait' },
      { id: 'e5', from: 'at-stop', to: 'wait', label: '是' },
      { id: 'e6', from: 'wait', to: 'pay' },
      { id: 'e7', from: 'pay', to: 'arrived' },
      { id: 'e8', from: 'arrived', to: 'hold', label: '否' },
      { id: 'e9', from: 'hold', to: 'finish' },
      { id: 'e10', from: 'arrived', to: 'finish', label: '是' },
      { id: 'e11', from: 'finish', to: 'end' },
    ],
  })
  const nodes = shapes.filter((shape) => shape.type === 'geo')

  for (let index = 0; index < nodes.length; index += 1) {
    for (let nextIndex = index + 1; nextIndex < nodes.length; nextIndex += 1) {
      assert.equal(nodesOverlap(nodes[index], nodes[nextIndex]), false)
    }
  }
})

function nodesOverlap(first, second) {
  const padding = 24
  return !(
    first.x + first.props.w + padding <= second.x ||
    second.x + second.props.w + padding <= first.x ||
    first.y + first.props.h + padding <= second.y ||
    second.y + second.props.h + padding <= first.y
  )
}
