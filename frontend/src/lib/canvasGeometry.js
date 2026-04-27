export function nodeCenter(node) {
  return {
    x: Number(node?.x) + (Number(node?.width) || 240) / 2,
    y: Number(node?.y) + (Number(node?.height) || 120) / 2,
  }
}

function nodeBounds(node) {
  const x = Number(node?.x) || 0
  const y = Number(node?.y) || 0
  const width = Number(node?.width) || 240
  const height = Number(node?.height) || 120
  return { x, y, width, height, cx: x + width / 2, cy: y + height / 2 }
}

function isDecisionNode(node) {
  const shapeType = String(
    node?.shape_kind || node?.composite_shape?.type || node?.shape || node?.geo || node?.visual_role || '',
  ).trim()
  return shapeType === 'diamond' || shapeType === 'flow_chart_diamond' || shapeType === 'decision'
}

export function edgeArrowLayout(edge, nodeById) {
  const from = nodeById.get(String(edge?.from || ''))
  const to = nodeById.get(String(edge?.to || ''))
  if (!from || !to) return null

  const fromBox = nodeBounds(from)
  const toBox = nodeBounds(to)
  const horizontalGap = Math.abs(toBox.cx - fromBox.cx)
  const verticalGap = Math.abs(toBox.cy - fromBox.cy)
  const sameRow = verticalGap < Math.max(fromBox.height, toBox.height) * 0.7
  const sameColumn = horizontalGap < Math.max(fromBox.width, toBox.width) * 0.25

  let start
  let end
  let kind = 'elbow'
  let bend = 0

  if (sameRow) {
    if (toBox.cx >= fromBox.cx) {
      start = { x: fromBox.x + fromBox.width, y: fromBox.cy }
      end = { x: toBox.x, y: toBox.cy }
    } else if (isReturnEdge(edge)) {
      start = { x: fromBox.cx, y: fromBox.y + fromBox.height }
      end = { x: toBox.cx, y: toBox.y + toBox.height }
      bend = 220
    } else {
      start = { x: fromBox.x, y: fromBox.cy }
      end = { x: toBox.x + toBox.width, y: toBox.cy }
    }
    kind = 'arc'
  } else if (sameColumn) {
    if (toBox.cy > fromBox.cy) {
      start = { x: fromBox.cx, y: fromBox.y + fromBox.height }
      end = { x: toBox.cx, y: toBox.y }
    } else {
      start = { x: fromBox.cx, y: fromBox.y }
      end = { x: toBox.cx, y: toBox.y + toBox.height }
    }
    kind = 'arc'
  } else if (toBox.cy > fromBox.cy) {
    const useRightSide = toBox.cx >= fromBox.cx
    if (isDecisionNode(from)) {
      start = {
        x: fromBox.cx + (useRightSide ? 1 : -1) * (fromBox.width / 4),
        y: fromBox.cy + fromBox.height / 4,
      }
      end = { x: toBox.cx, y: toBox.y }
      kind = 'arc'
      bend = useRightSide ? -24 : 24
    } else {
      start = {
        x: useRightSide ? fromBox.x + fromBox.width : fromBox.x,
        y: fromBox.cy,
      }
      end = {
        x: useRightSide ? toBox.x + toBox.width : toBox.x,
        y: toBox.cy,
      }
    }
  } else {
    const useRightSide = toBox.cx > fromBox.cx
    start = {
      x: useRightSide ? fromBox.x + fromBox.width : fromBox.x,
      y: fromBox.cy,
    }
    end = {
      x: useRightSide ? toBox.x + toBox.width : toBox.x,
      y: toBox.cy,
    }
  }

  return {
    x: Math.round(start.x),
    y: Math.round(start.y),
    start: { x: 0, y: 0 },
    end: {
      x: Math.round(end.x - start.x),
      y: Math.round(end.y - start.y),
    },
    kind,
    bend,
    elbowMidPoint: horizontalGap > verticalGap && !sameRow && !sameColumn ? 0.2 : 0.5,
  }
}

function isReturnEdge(edge) {
  const label = String(edge?.label || edge?.text || '').trim()
  return /返回|回退|重试|故障排除后|修复后|处理后|retry|back/i.test(label)
}
