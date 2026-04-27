function quoteText(value) {
  const text = String(value || '').trim()
  return text ? `“${text}”` : '一段内容'
}

export function formatElapsedMs(value) {
  const ms = Number.isFinite(value) ? Math.max(value, 0) : 0
  return `${(ms / 1000).toFixed(1)} 秒`
}

export function describeGenerationInfo(generationInfo) {
  if (!generationInfo || typeof generationInfo !== 'object') return []

  const lines = []
  if (generationInfo.source === 'ai') {
    lines.push('本次走的是真实模型。')
    if (generationInfo.provider || generationInfo.model) {
      lines.push(
        `模型来源：${generationInfo.provider || '未知来源'} / ${generationInfo.model || '未知模型'}。`,
      )
    }
  }

  if (generationInfo.latency_ms !== undefined && generationInfo.latency_ms !== null) {
    lines.push(`后端生成耗时 ${formatElapsedMs(generationInfo.latency_ms)}。`)
  }

  return lines
}

export function describePatch(patch) {
  if (!patch || typeof patch !== 'object') return ['还没有生成 patch。']

  const lines = []
  if (patch.generation_mode === 'full_board') {
    lines.push('这次是整板生成。')
    const nodes = Array.isArray(patch.full_board?.nodes) ? patch.full_board.nodes.length : 0
    const edges = Array.isArray(patch.full_board?.edges) ? patch.full_board.edges.length : 0
    lines.push(`预计会生成 ${nodes} 个节点和 ${edges} 条连线。`)
    const nodeTexts = Array.isArray(patch.full_board?.nodes)
      ? patch.full_board.nodes
          .map((node) => String(node?.text || '').trim())
          .filter(Boolean)
          .slice(0, 6)
      : []
    if (nodeTexts.length) {
      lines.push(`节点内容：${nodeTexts.join(' → ')}。`)
    }
  } else {
    lines.push('这次是局部编辑。')
  }

  const operations = Array.isArray(patch.operations) ? patch.operations : []
  for (const operation of operations) {
    if (operation?.type === 'node.replace') {
      lines.push(
        `会把节点 ${operation.target || '未命名节点'} 改写成${quoteText(operation.content)}。`,
      )
      continue
    }
    if (operation?.type === 'node.add') {
      lines.push(`会新增节点${quoteText(operation.node?.text)}。`)
      continue
    }
    if (operation?.type === 'edge.add') {
      const edge = operation.edge || {}
      lines.push(`会补一条连接线，把 ${edge.from || '-'} 连到 ${edge.to || '-'}。`)
      continue
    }
  }

  const summary = String(patch.summary || '').trim()
  if (summary && !lines.includes(summary)) {
    lines.push(summary)
  }

  return lines.length ? lines : ['这次 patch 没有可展示的操作。']
}
