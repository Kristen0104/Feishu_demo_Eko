import test from 'node:test'
import assert from 'node:assert/strict'

import { edgeArrowLayout } from './canvasGeometry.js'

test('edgeArrowLayout builds a horizontal arrow between neighboring nodes', () => {
  const nodeById = new Map([
    ['start', { id: 'start', x: 100, y: 80, width: 200, height: 100 }],
    ['next', { id: 'next', x: 420, y: 80, width: 200, height: 100 }],
  ])

  assert.deepEqual(
    edgeArrowLayout({ id: 'edge-1', from: 'start', to: 'next' }, nodeById),
    {
      x: 300,
      y: 130,
      start: { x: 0, y: 0 },
      end: { x: 120, y: 0 },
      kind: 'arc',
      bend: 0,
      elbowMidPoint: 0.5,
    },
  )
})

test('edgeArrowLayout creates a vertical boundary arrow for wrapped rows', () => {
  const nodeById = new Map([
    ['end-row-1', { id: 'end-row-1', x: 940, y: 140, width: 220, height: 100 }],
    ['start-row-2', { id: 'start-row-2', x: 940, y: 320, width: 220, height: 100 }],
  ])

  assert.deepEqual(
    edgeArrowLayout({ id: 'edge-2', from: 'end-row-1', to: 'start-row-2' }, nodeById),
    {
      x: 1050,
      y: 240,
      start: { x: 0, y: 0 },
      end: { x: 0, y: 80 },
      kind: 'arc',
      bend: 0,
      elbowMidPoint: 0.5,
    },
  )
})

test('edgeArrowLayout bends same-row return arrows away from intermediate nodes', () => {
  const nodeById = new Map([
    ['previous', { id: 'previous', x: 1268, y: 196, width: 352, height: 88 }],
    ['decision', { id: 'decision', x: 1716, y: 150, width: 240, height: 180 }],
    ['fix', { id: 'fix', x: 2052, y: 196, width: 324, height: 88 }],
  ])

  assert.deepEqual(
    edgeArrowLayout({ id: 'edge-return', from: 'fix', to: 'previous', label: '故障排除后' }, nodeById),
    {
      x: 2214,
      y: 284,
      start: { x: 0, y: 0 },
      end: { x: -770, y: 0 },
      kind: 'arc',
      bend: 220,
      elbowMidPoint: 0.5,
    },
  )
})

test('edgeArrowLayout routes decision branches into the target top edge', () => {
  const nodeById = new Map([
    [
      'decision',
      {
        id: 'decision',
        x: 500,
        y: 240,
        width: 240,
        height: 180,
        composite_shape: { type: 'diamond' },
      },
    ],
    ['yes', { id: 'yes', x: 320, y: 640, width: 220, height: 100 }],
  ])

  assert.deepEqual(
    edgeArrowLayout({ id: 'edge-yes', from: 'decision', to: 'yes' }, nodeById),
    {
      x: 560,
      y: 375,
      start: { x: 0, y: 0 },
      end: { x: -130, y: 265 },
      kind: 'arc',
      bend: 24,
      elbowMidPoint: 0.5,
    },
  )
})

test('edgeArrowLayout treats shape_kind diamond as a decision node', () => {
  const nodeById = new Map([
    [
      'decision',
      {
        id: 'decision',
        x: 500,
        y: 240,
        width: 240,
        height: 180,
        shape_kind: 'flow_chart_diamond',
      },
    ],
    ['yes', { id: 'yes', x: 320, y: 640, width: 220, height: 100 }],
  ])

  assert.equal(
    edgeArrowLayout({ id: 'edge-yes', from: 'decision', to: 'yes' }, nodeById).end.y,
    265,
  )
})

test('edgeArrowLayout skips edges with missing endpoints', () => {
  const nodeById = new Map([['start', { id: 'start', x: 100, y: 80 }]])

  assert.equal(edgeArrowLayout({ id: 'edge-1', from: 'start', to: 'missing' }, nodeById), null)
})
