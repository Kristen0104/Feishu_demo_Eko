const START_STYLE = {
  fill_color: '#e7f8ef',
  border_color: '#16a34a',
  border_style: 'solid',
  border_width: 'medium',
}
const END_STYLE = {
  fill_color: '#eef2ff',
  border_color: '#4f46e5',
  border_style: 'solid',
  border_width: 'medium',
}
const STEP_STYLE = {
  fill_color: '#eff6ff',
  border_color: '#2563eb',
  border_style: 'solid',
  border_width: 'narrow',
}
const DECISION_STYLE = {
  fill_color: '#fff7ed',
  border_color: '#f59e0b',
  border_style: 'solid',
  border_width: 'medium',
}
const BRANCH_STYLE = {
  fill_color: '#f5f3ff',
  border_color: '#7c3aed',
  border_style: 'solid',
  border_width: 'medium',
}

export function decorateNodeForPreview(node, branchNodeIds = new Set()) {
  const role = inferNodeRole(node, branchNodeIds)
  const defaults = nodeDefaults(role)
  return {
    ...node,
    visual_role: node.visual_role || (role === 'step' || role === 'branch' ? undefined : role),
    shape_kind: node.shape_kind || defaults.shape_kind,
    style: {
      ...defaults.style,
      ...(node.style && typeof node.style === 'object' ? node.style : {}),
    },
    font_weight: node.font_weight || defaults.font_weight,
    font_size: node.font_size || defaults.font_size,
  }
}

export function branchNodeIdsFromEdges(edges) {
  if (!Array.isArray(edges)) return new Set()
  return new Set(
    edges
      .filter((edge) => /^(否|no|n|false|等待|返回)$/i.test(String(edge?.label || '').trim()))
      .map((edge) => String(edge?.to || '').trim())
      .filter(Boolean),
  )
}

export function nodeGeo(node) {
  const visualRole = String(node?.visual_role || '').trim()
  if (visualRole === 'start' || visualRole === 'end') return 'ellipse'
  const shapeType = String(
    node?.shape_kind || node?.composite_shape?.type || node?.shape || visualRole || '',
  ).trim()
  if (shapeType === 'diamond' || shapeType === 'flow_chart_diamond') return 'diamond'
  if (shapeType === 'decision') return 'diamond'
  if (shapeType === 'ellipse' || shapeType === 'circle') return 'ellipse'
  if (shapeType === 'state_start' || shapeType === 'state_end') return 'ellipse'
  if (shapeType === 'flow_chart_ellipse' || shapeType === 'flow_chart_circle') return 'ellipse'
  if (shapeType === 'flow_chart_parallelogram') return 'trapezoid'
  if (shapeType === 'flow_chart_trapezoid') return 'trapezoid'
  if (shapeType === 'flow_chart_hexagon') return 'hexagon'
  return 'rectangle'
}

export function nodeColor(node) {
  const geo = nodeGeo(node)
  if (geo === 'diamond') return 'orange'
  const colorText = [
    node?.style?.fill_color,
    node?.style?.border_color,
    node?.style?.theme_fill_color_code,
    node?.style?.theme_border_color_code,
  ]
    .map((value) => String(value || '').toLowerCase())
    .join(' ')
  if (/(e7f8ef|dcfce7|bbf7d0|d1fae5|ccfbf1|ecfccb|16a34a|15803d|22c55e|059669|0f766e|65a30d|e5fff2|f1f9f2|29a874|34a853)/.test(colorText)) {
    return 'green'
  }
  if (/(eef2ff|ede9fe|f5f3ff|4f46e5|7c3aed|8b5cf6|f3edff|8f5cff|9254de)/.test(colorText)) {
    return 'violet'
  }
  if (/(e1eaff|f0f4ff|4e83fd|3370ff|1f5fff|eff6ff|2563eb)/.test(colorText)) return 'blue'
  if (/(f1f5f9|e2e8f0|f8fafc|475569|64748b|0f172a)/.test(colorText)) return 'grey'
  if (/(feead2|fff6ee|ffedd5|ffa53d|f59e0b|f97316|f6c02d|d97706)/.test(colorText)) return 'orange'
  if (/(ffeceb|fee2e2|fff1f2|f04438|ef4444|dc2626|e11d48)/.test(colorText)) return 'red'
  const role = inferNodeRole(node)
  if (role === 'start') return 'green'
  if (role === 'end' || role === 'branch') return 'violet'
  if (role === 'decision') return 'orange'
  return 'blue'
}

function nodeDefaults(role) {
  if (role === 'start') {
    return { shape_kind: 'state_start', style: START_STYLE, font_weight: 'bold', font_size: 14 }
  }
  if (role === 'end') {
    return { shape_kind: 'state_end', style: END_STYLE, font_weight: 'bold', font_size: 14 }
  }
  if (role === 'decision') {
    return {
      shape_kind: 'flow_chart_diamond',
      style: DECISION_STYLE,
      font_weight: 'bold',
      font_size: 13,
    }
  }
  if (role === 'branch') {
    return {
      shape_kind: 'flow_chart_round_rect',
      style: BRANCH_STYLE,
      font_weight: 'regular',
      font_size: 13,
    }
  }
  return {
    shape_kind: 'flow_chart_round_rect',
    style: STEP_STYLE,
    font_weight: 'regular',
    font_size: 13,
  }
}

function inferNodeRole(node, branchNodeIds = new Set()) {
  const visualRole = String(node?.visual_role || '').trim()
  if (['start', 'end', 'decision'].includes(visualRole)) return visualRole
  const shapeKind = String(node?.shape_kind || node?.shape || node?.composite_shape?.type || '').trim()
  if (shapeKind === 'flow_chart_diamond') return 'decision'
  if (shapeKind === 'state_start') return 'start'
  if (shapeKind === 'state_end') return 'end'
  const text = String(node?.text || '').trim()
  const lowerText = text.toLowerCase()
  if (text.startsWith('开始') || lowerText.startsWith('start')) return 'start'
  if (text.endsWith('结束') || text.endsWith('完成') || lowerText.endsWith('end')) return 'end'
  const id = String(node?.id || '').trim()
  if (branchNodeIds.has(id)) return 'branch'
  return 'step'
}
