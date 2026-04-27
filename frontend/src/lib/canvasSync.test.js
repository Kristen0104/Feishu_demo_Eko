import test from 'node:test'
import assert from 'node:assert/strict'

import { hasSnapshotChanged } from './canvasSync.js'

test('hasSnapshotChanged returns false for equivalent snapshots', () => {
  const currentSnapshot = {
    nodes: [{ id: 'node-1', text: 'A', x: 10, y: 20, width: 200, height: 100 }],
    edges: [],
    viewport: { zoom: 1, x: 0, y: 0 },
  }

  const nextSnapshot = {
    viewport: { y: 0, x: 0, zoom: 1 },
    edges: [],
    nodes: [{ height: 100, width: 200, y: 20, x: 10, text: 'A', id: 'node-1' }],
  }

  assert.equal(hasSnapshotChanged(currentSnapshot, nextSnapshot), false)
})

test('hasSnapshotChanged returns true when node text changed', () => {
  const currentSnapshot = {
    nodes: [{ id: 'node-1', text: 'A' }],
    edges: [],
    viewport: { x: 0, y: 0, zoom: 1 },
  }
  const nextSnapshot = {
    nodes: [{ id: 'node-1', text: 'B' }],
    edges: [],
    viewport: { x: 0, y: 0, zoom: 1 },
  }

  assert.equal(hasSnapshotChanged(currentSnapshot, nextSnapshot), true)
})
