import { createShapeId, toRichText } from 'tldraw'
import { edgeArrowLayout } from './canvasGeometry.js'
import {
  branchNodeIdsFromEdges,
  decorateNodeForPreview,
  nodeColor,
  nodeGeo,
} from './canvasVisualTemplate.js'

const DEFAULT_NODE_WIDTH = 240
const DEFAULT_NODE_HEIGHT = 120
const MIN_TEXT_NODE_WIDTH = 180
const MIN_TEXT_NODE_HEIGHT = 88
const SMALL_BOARD_SCALE = 2.4
const FLOW_LAYOUT_X = 120
const FLOW_LAYOUT_Y = 180
const FLOW_LAYOUT_GAP_X = 96
const FLOW_LAYOUT_GAP_Y = 220
const NODE_STYLE_FIELDS = [
  'style',
  'composite_shape',
  'visual_role',
  'shape_kind',
  'font_size',
  'font_weight',
  'theme_text_color_code',
  'theme_text_background_color_code',
  'text_color',
  'text_background_color',
  'text_color_type',
  'text_background_color_type',
  'horizontal_align',
  'vertical_align',
]
const EDGE_STYLE_FIELDS = [
  'label',
  'shape',
  'arrow_style',
  'start_arrow_style',
  'end_arrow_style',
  'style',
  'caption_position',
  'caption_auto_direction',
]

function fallbackPosition(index) {
  return {
    x: 120 + (index % 3) * 280,
    y: 120 + Math.floor(index / 3) * 180,
  }
}

function cloneJsonValue(value) {
  if (value === undefined) return undefined
  if (value === null) return null
  if (typeof value !== 'object') return value
  return JSON.parse(JSON.stringify(value))
}

function copyDefinedFields(source, fields) {
  const target = {}
  for (const field of fields) {
    if (!source || typeof source !== 'object' || source[field] === undefined) continue
    target[field] = cloneJsonValue(source[field])
  }
  return target
}

function nodeStyleMetadata(node) {
  return copyDefinedFields(node, NODE_STYLE_FIELDS)
}

function edgeStyleMetadata(edge) {
  return copyDefinedFields(edge, EDGE_STYLE_FIELDS)
}

function isDecisionLikeNode(node) {
  return nodeGeo(node) === 'diamond' || String(node?.visual_role || '').trim() === 'decision'
}

function isRenderableNode(node) {
  if (!node || typeof node !== 'object' || !node.id) return false
  if (String(node.type || '').trim() === 'connector') return false
  return Boolean(extractNodeText(node) || node.type !== 'connector')
}

function readableNodeSize(node) {
  const text = extractNodeText(node)
  const rawWidth = Number(node.width) || DEFAULT_NODE_WIDTH
  const rawHeight = Number(node.height) || DEFAULT_NODE_HEIGHT
  const geo = nodeGeo(node)
  if (!text) {
    return { width: rawWidth, height: rawHeight }
  }
  if (geo === 'diamond') {
    return {
      width: Math.max(rawWidth, 240),
      height: Math.max(rawHeight, 180),
    }
  }
  const textWidth = Math.min(360, Math.max(MIN_TEXT_NODE_WIDTH, 72 + text.length * 28))
  return {
    width: Math.max(rawWidth, textWidth),
    height: Math.max(rawHeight, MIN_TEXT_NODE_HEIGHT),
  }
}

function shouldScaleImportedBoard(nodes) {
  const positionedNodes = nodes.filter(
    (node) => typeof node.x === 'number' && typeof node.y === 'number',
  )
  if (positionedNodes.length < 2) return false
  const minX = Math.min(...positionedNodes.map((node) => node.x))
  const maxX = Math.max(...positionedNodes.map((node) => node.x + (Number(node.width) || 0)))
  const minY = Math.min(...positionedNodes.map((node) => node.y))
  const maxY = Math.max(...positionedNodes.map((node) => node.y + (Number(node.height) || 0)))
  return maxX - minX < 420 || maxY - minY < 520
}

function nodePosition(node, index, shouldScale, size = readableNodeSize(node)) {
  const fallback = fallbackPosition(index)
  const x = typeof node.x === 'number' ? node.x : fallback.x
  const y = typeof node.y === 'number' ? node.y : fallback.y
  if (!shouldScale) return { x, y }
  const rawWidth = Number(node.width) || DEFAULT_NODE_WIDTH
  const rawHeight = Number(node.height) || DEFAULT_NODE_HEIGHT
  const centerX = 120 + (x + rawWidth / 2) * SMALL_BOARD_SCALE
  const centerY = 80 + (y + rawHeight / 2) * SMALL_BOARD_SCALE
  return {
    x: Math.round(centerX - size.width / 2),
    y: Math.round(centerY - size.height / 2),
  }
}

function edgeLabel(edge) {
  return extractTextPayload(edge?.label).trim()
}

function shouldUseFlowLayout(nodes, edges) {
  if (nodes.length < 5 || edges.length < 4) return false
  const nodeIds = new Set(nodes.map((node) => String(node.id)))
  const usableEdges = edges.filter((edge) => nodeIds.has(String(edge?.from)) && nodeIds.has(String(edge?.to)))
  if (usableEdges.length < 4) return false
  const outgoingCount = new Map()
  for (const edge of usableEdges) {
    const from = String(edge.from)
    outgoingCount.set(from, (outgoingCount.get(from) || 0) + 1)
  }
  return nodes.some(isDecisionLikeNode) || [...outgoingCount.values()].some((count) => count > 1)
}

function flowLayoutPositions(nodes, edges, nodeSizeById) {
  if (!shouldUseFlowLayout(nodes, edges)) return null

  const nodeIds = new Set(nodes.map((node) => String(node.id)))
  const nodeById = new Map(nodes.map((node) => [String(node.id), node]))
  const outgoing = new Map(nodes.map((node) => [String(node.id), []]))
  const indegree = new Map(nodes.map((node) => [String(node.id), 0]))

  for (const edge of edges) {
    const from = String(edge?.from || '')
    const to = String(edge?.to || '')
    if (!nodeIds.has(from) || !nodeIds.has(to)) continue
    outgoing.get(from).push(edge)
    indegree.set(to, (indegree.get(to) || 0) + 1)
  }

  const startId =
    nodes.find((node) => String(node?.visual_role || '') === 'start')?.id ||
    nodes.find((node) => (indegree.get(String(node.id)) || 0) === 0)?.id ||
    nodes[0]?.id
  if (!startId) return null

  const mainIds = []
  const seen = new Set()
  let currentId = String(startId)
  while (currentId && !seen.has(currentId) && nodeIds.has(currentId)) {
    mainIds.push(currentId)
    seen.add(currentId)
    const nextEdge = preferredMainEdge(outgoing.get(currentId) || [], seen)
    currentId = nextEdge ? String(nextEdge.to) : ''
  }

  const columnById = new Map(mainIds.map((id, index) => [id, index]))
  const laneById = new Map(mainIds.map((id) => [id, 0]))
  const queue = [...mainIds]
  const queued = new Set(queue)

  while (queue.length) {
    const fromId = queue.shift()
    const fromColumn = columnById.get(fromId) || 0
    const fromLane = laneById.get(fromId) || 0
    const branches = outgoing.get(fromId) || []
    for (const edge of branches) {
      const toId = String(edge.to)
      if (!nodeIds.has(toId) || toId === fromId) continue
      if (!columnById.has(toId)) {
        columnById.set(toId, fromColumn + 1)
      }
      if (!laneById.has(toId)) {
        laneById.set(toId, branchLane(edge, fromLane, fromColumn))
      }
      if (!queued.has(toId)) {
        queue.push(toId)
        queued.add(toId)
      }
    }
  }

  nodes.forEach((node, index) => {
    const id = String(node.id)
    if (!columnById.has(id)) columnById.set(id, index)
    if (!laneById.has(id)) laneById.set(id, 0)
  })
  avoidLaneCollisions(nodes, columnById, laneById)

  const columnX = flowColumnPositions(nodes, columnById, nodeSizeById)
  const positions = new Map()
  for (const node of nodes) {
    const id = String(node.id)
    const size = nodeSizeById.get(id) || readableNodeSize(node)
    const centerX = (columnX.get(columnById.get(id) || 0) || FLOW_LAYOUT_X) + size.width / 2
    const centerY =
      FLOW_LAYOUT_Y + DEFAULT_NODE_HEIGHT / 2 + (laneById.get(id) || 0) * FLOW_LAYOUT_GAP_Y
    positions.set(id, {
      x: Math.round(centerX - size.width / 2),
      y: Math.round(centerY - size.height / 2),
    })
  }
  return positions
}

function avoidLaneCollisions(nodes, columnById, laneById) {
  const occupied = new Set()
  for (const node of nodes) {
    const id = String(node.id)
    const column = columnById.get(id) || 0
    let lane = laneById.get(id) || 0
    const preferredDirection = lane < 0 ? -1 : 1
    while (occupied.has(`${column}:${lane}`)) {
      lane += preferredDirection
    }
    laneById.set(id, lane)
    occupied.add(`${column}:${lane}`)
  }
}

function flowColumnPositions(nodes, columnById, nodeSizeById) {
  const maxWidthByColumn = new Map()
  for (const node of nodes) {
    const id = String(node.id)
    const column = columnById.get(id) || 0
    const size = nodeSizeById.get(id) || readableNodeSize(node)
    maxWidthByColumn.set(column, Math.max(maxWidthByColumn.get(column) || 0, size.width))
  }
  const sortedColumns = [...maxWidthByColumn.keys()].sort((first, second) => first - second)
  const xByColumn = new Map()
  let cursor = FLOW_LAYOUT_X
  for (const column of sortedColumns) {
    xByColumn.set(column, cursor)
    cursor += (maxWidthByColumn.get(column) || DEFAULT_NODE_WIDTH) + FLOW_LAYOUT_GAP_X
  }
  return xByColumn
}

function preferredMainEdge(edges, seen) {
  const candidates = edges.filter((edge) => !seen.has(String(edge?.to || '')))
  if (!candidates.length) return null
  return (
    candidates.find((edge) => /^(是|yes|y|true|继续|下一步)$/i.test(edgeLabel(edge))) ||
    candidates.find((edge) => !/^(否|no|n|false|返回|等待)$/i.test(edgeLabel(edge))) ||
    candidates[0]
  )
}

function branchLane(edge, fromLane, fromColumn) {
  const label = edgeLabel(edge)
  if (/^(否|no|n|false|等待|返回)$/i.test(label)) {
    return fromLane + (fromColumn < 4 ? -1 : 1)
  }
  if (/^(是|yes|y|true)$/i.test(label)) return fromLane
  return fromLane - 1
}

function richTextToPlainText(richText) {
  if (!richText || typeof richText !== 'object') return ''
  if (!Array.isArray(richText.content)) return ''
  return richText.content
    .map((block) => {
      if (!block || typeof block !== 'object' || !Array.isArray(block.content)) return ''
      return block.content
        .map((child) => (child && typeof child.text === 'string' ? child.text : ''))
        .join('')
    })
    .filter(Boolean)
    .join('\n')
}

export function extractNodeText(node) {
  if (!node || typeof node !== 'object') return ''
  const titleText = extractTextPayload(node.title)
  if (titleText) return titleText
  const directText = extractTextPayload(node.text)
  if (directText) return directText
  return extractTextPayload(node.rich_text)
}

function extractTextPayload(payload) {
  if (typeof payload === 'string') return extractStringTextPayload(payload)
  if (Array.isArray(payload)) return extractTextElements(payload)
  if (!payload || typeof payload !== 'object') return ''
  const directText = extractTextPayload(payload.text)
  if (directText) return directText
  const plainText = extractTextPayload(payload.plain_text)
  if (plainText) return plainText
  const contentText = extractTextPayload(payload.content)
  if (contentText) return contentText
  if (Array.isArray(payload.elements)) return extractTextElements(payload.elements)
  return ''
}

function extractStringTextPayload(payload) {
  const text = payload.trim()
  if (!text) return ''
  if (text[0] !== '{' && text[0] !== '[') return text

  try {
    const parsed = JSON.parse(text)
    const parsedText = extractTextPayload(parsed)
    if (parsedText) return parsedText
  } catch {
    // Some persisted rows may contain Python repr strings from older backend code.
  }

  const textField = text.match(/['"]text['"]\s*:\s*['"]([^'"]+)['"]/)
  if (textField?.[1]) return textField[1].trim()
  return text
}

function extractTextElements(elements) {
  return elements
    .map((element) => {
      if (!element || typeof element !== 'object') return ''
      if (
        element.text_run &&
        typeof element.text_run === 'object' &&
        typeof element.text_run.content === 'string'
      ) {
        return element.text_run.content
      }
      return extractTextPayload(element.text) || extractTextPayload(element.content)
    })
    .join('')
    .trim()
}

export function snapshotToTldrawShapes(snapshot) {
  const nodes = Array.isArray(snapshot?.nodes) ? snapshot.nodes : []
  const edges = Array.isArray(snapshot?.edges) ? snapshot.edges : []
  const branchNodeIds = branchNodeIdsFromEdges(edges)
  const renderableNodes = nodes
    .filter(isRenderableNode)
    .map((node) => decorateNodeForPreview(node, branchNodeIds))
  const shouldScale = shouldScaleImportedBoard(renderableNodes)
  const nodeSizeById = new Map(
    renderableNodes.map((node) => [String(node.id), readableNodeSize(node)]),
  )
  const layoutPositions = flowLayoutPositions(renderableNodes, edges, nodeSizeById)
  const nodeById = new Map(
    renderableNodes.map((node, index) => {
      const size = nodeSizeById.get(String(node.id)) || readableNodeSize(node)
      const position =
        layoutPositions?.get(String(node.id)) || nodePosition(node, index, shouldScale, size)
      return [
        String(node.id),
        {
          ...node,
          x: position.x,
          y: position.y,
          width: size.width,
          height: size.height,
        },
      ]
    }),
  )
  const nodeShapes = renderableNodes
    .map((node, index) => {
      const size = nodeSizeById.get(String(node.id)) || readableNodeSize(node)
      const position =
        layoutPositions?.get(String(node.id)) || nodePosition(node, index, shouldScale, size)

      return {
        id: createShapeId(`node-${node.id}`),
        type: 'geo',
        x: position.x,
        y: position.y,
        props: {
          geo: nodeGeo(node),
          w: size.width,
          h: size.height,
          color: nodeColor(node),
          fill: 'solid',
          dash: 'draw',
          size: 'm',
          font: 'sans',
          align: 'middle',
          verticalAlign: 'middle',
          richText: toRichText(extractNodeText(node)),
        },
        meta: {
          nodeId: String(node.id),
          nodeType: String(node.type || 'note'),
          ...nodeStyleMetadata(node),
        },
      }
    })
  const edgeShapes = edges
    .filter((edge) => edge && typeof edge === 'object' && edge.id)
    .map((edge) => {
      const layout = edgeArrowLayout(edge, nodeById)
      if (!layout) return null

      return {
        id: createShapeId(`edge-${edge.id}`),
        type: 'arrow',
        x: layout.x,
        y: layout.y,
        props: {
          kind: layout.kind,
          elbowMidPoint: layout.elbowMidPoint,
          dash: 'solid',
          size: 'm',
          fill: 'none',
          color: 'grey',
          labelColor: 'black',
          bend: layout.bend,
          start: layout.start,
          end: layout.end,
          arrowheadStart: 'none',
          arrowheadEnd: 'triangle',
          text: extractTextPayload(edge.label),
          labelPosition: 0.5,
          font: 'draw',
          scale: 1,
        },
        meta: {
          edgeId: String(edge.id),
          fromNodeId: String(edge.from || ''),
          toNodeId: String(edge.to || ''),
          edgeType: String(edge.type || 'association'),
          ...edgeStyleMetadata(edge),
        },
      }
    })
    .filter(Boolean)

  return [...edgeShapes, ...nodeShapes]
}

export function extractSnapshotFromEditor(editor, detail) {
  const shapes =
    typeof editor.getCurrentPageShapesSorted === 'function'
      ? editor.getCurrentPageShapesSorted()
      : []
  const nodes = shapes
    .filter((shape) => shape?.type === 'geo')
    .map((shape) => ({
      id: String(shape.meta?.nodeId || shape.id),
      type: String(shape.meta?.nodeType || 'note'),
      text: richTextToPlainText(shape.props?.richText),
      x: Math.round(shape.x),
      y: Math.round(shape.y),
      width: Math.round(shape.props?.w || DEFAULT_NODE_WIDTH),
      height: Math.round(shape.props?.h || DEFAULT_NODE_HEIGHT),
      ...nodeStyleMetadata(shape.meta || {}),
    }))

  const edgeShapes = shapes.filter((shape) => shape?.type === 'arrow' && shape.meta?.edgeId)
  const currentSnapshot = detail?.working_board?.latest_snapshot || {}
  const edges = edgeShapes.length
    ? edgeShapes.map((shape) => ({
        id: String(shape.meta.edgeId),
        from: String(shape.meta.fromNodeId || ''),
        to: String(shape.meta.toNodeId || ''),
        type: String(shape.meta.edgeType || 'association'),
        ...edgeStyleMetadata(shape.meta || {}),
      }))
    : Array.isArray(currentSnapshot.edges)
      ? currentSnapshot.edges
      : []
  const viewport =
    currentSnapshot.viewport && typeof currentSnapshot.viewport === 'object'
      ? currentSnapshot.viewport
      : { x: 0, y: 0, zoom: 1 }

  return {
    nodes,
    edges,
    viewport,
  }
}

export function buildUserMappings(detail, snapshot) {
  const existingMappings = Array.isArray(detail?.element_mappings)
    ? detail.element_mappings
    : []
  const mappingByNodeId = new Map(
    existingMappings.map((mapping) => [mapping.working_element_id, mapping]),
  )

  const nodeMappings = snapshot.nodes.map((node) => {
    const existing = mappingByNodeId.get(node.id)
    if (existing) return existing
    return buildLocalMapping(node.id, 'node')
  })
  const edgeMappings = (Array.isArray(snapshot.edges) ? snapshot.edges : []).map((edge) => {
    const existing = mappingByNodeId.get(edge.id)
    if (existing) return existing
    return buildLocalMapping(edge.id, 'edge')
  })
  return [...nodeMappings, ...edgeMappings]
}

function buildLocalMapping(id, elementType) {
  return {
    source_element_id: `local:${id}`,
    working_element_id: id,
    element_type: elementType,
    origin_type: 'user',
    mapping_status: 'active',
    metadata: {
      created_from: 'tldraw_manual_edit',
    },
  }
}
