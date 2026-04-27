import { useEffect, useMemo, useRef, useState, startTransition } from 'react'
import { Tldraw } from 'tldraw'
import {
  buildUserMappings,
  extractSnapshotFromEditor,
  snapshotToTldrawShapes,
} from './lib/canvasSnapshot'
import { hasSnapshotChanged } from './lib/canvasSync'
import { describeGenerationInfo, describePatch, formatElapsedMs } from './lib/patchPreview'

function buildUrl(apiBase, path) {
  return `${apiBase.replace(/\/$/, '')}${path}`
}

async function requestJson(url, options) {
  const response = await fetch(url, options)
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const detail =
      payload?.detail?.message ||
      payload?.detail?.feishu_message ||
      payload?.message ||
      response.statusText
    const error = new Error(String(detail || `HTTP ${response.status}`))
    error.status = response.status
    error.payload = payload
    throw error
  }

  return payload
}

function summarizeError(error) {
  if (!error) return ''
  const payloadMessage = error.payload?.detail?.message || error.payload?.message
  const payloadReason = error.payload?.detail?.reason || error.payload?.reason
  if (payloadMessage === 'Canvas AI generation failed') {
    if (String(payloadReason || '').includes('invalid JSON')) {
      return `AI 输出不是合法 JSON：${payloadReason}`
    }
    return payloadReason ? `AI 生成失败：${payloadReason}` : 'AI 生成失败，请重试。'
  }
  if (payloadMessage === 'Canvas AI provider is not configured') {
    return 'AI 服务没有配置可用模型，请检查后端模型凭证。'
  }
  if (error.message === 'Failed to fetch' || error.message === 'Load failed') {
    return '浏览器没拿到后端响应，通常是联调后端没启动，或 127.0.0.1 / localhost 跨域来源没放通。'
  }
  if (error.status === 404) return '文档中没有可导入的 whiteboard。'
  if (error.status === 409) return '存在未解决冲突，请先完成 merge review。'
  if (error.status === 502) return '飞书上游接口失败，请检查凭证、链接和上游状态。'
  return error.message || '请求失败'
}

function summarizePublishGuard(publishResult) {
  if (publishResult?.accepted !== false) return ''
  const reason = publishResult?.upstream_payload?.reason || ''
  if (reason === 'target_board_not_empty') {
    const count = publishResult?.upstream_payload?.existing_node_count
    return typeof count === 'number'
      ? `目标飞书画板不是空白，已存在 ${count} 个节点，后端已按保护策略拒绝覆盖。`
      : '目标飞书画板不是空白，后端已按保护策略拒绝覆盖。'
  }
  return reason ? `发布未被飞书接受：${reason}` : '发布请求已返回，但飞书没有接受这次写入。'
}

function usePrettyJson(value) {
  return useMemo(() => JSON.stringify(value ?? {}, null, 2), [value])
}

function createMessage(role, content, meta = {}) {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    role,
    content,
    meta,
  }
}

function selectedNodeSummary(selectedNodeIds) {
  if (!selectedNodeIds.length) return '未选中节点，AI 会基于整张画板生成建议。'
  if (selectedNodeIds.length === 1) return `已选中节点 ${selectedNodeIds[0]}，AI 会优先做局部修改。`
  return `已选中 ${selectedNodeIds.length} 个节点，AI 会优先围绕这些节点修改。`
}

export function App() {
  const [apiBase, setApiBase] = useState('http://127.0.0.1:8000/api/v1')
  const [sessionId, setSessionId] = useState('canvas-demo-001')
  const [shareUrl, setShareUrl] = useState(
    'https://jcneyh7qlo8i.feishu.cn/docx/QFQVd8EEnoD58zxNwLNcmJRJnAg?from=from_copylink',
  )
  const [mermaidCode, setMermaidCode] = useState(
    'graph TD; A[Start] --> B[Validate Input] --> C[Generate Board] --> D[Review] --> E[Publish];',
  )
  const [userPrompt, setUserPrompt] = useState('')
  const [preferredMode, setPreferredMode] = useState('auto')
  const [detail, setDetail] = useState(null)
  const [currentPatch, setCurrentPatch] = useState(null)
  const [mergeReviews, setMergeReviews] = useState([])
  const [currentReviewId, setCurrentReviewId] = useState('')
  const [resolutions, setResolutions] = useState({})
  const [status, setStatus] = useState('等待导入飞书文档。')
  const [error, setError] = useState('')
  const [rawModelOutput, setRawModelOutput] = useState('')
  const [rawPanel, setRawPanel] = useState({})
  const [isGenerating, setIsGenerating] = useState(false)
  const [lastGenerateDurationMs, setLastGenerateDurationMs] = useState(null)
  const [selectedNodeIds, setSelectedNodeIds] = useState([])
  const [chatMessages, setChatMessages] = useState(() => [
    createMessage(
      'assistant',
      '先导入飞书文档，然后在右侧画板编辑。你可以直接告诉我想怎么调整画板，我会生成一份可应用的修改。',
    ),
    createMessage('system', '当前默认连接真实联调后端 8000；如需离线自检可手动切到 Stub 8012。'),
  ])
  const [showAdvanced, setShowAdvanced] = useState(false)
  const editorRef = useRef(null)

  const currentReview = useMemo(
    () => mergeReviews.find((review) => review.review_id === currentReviewId) || null,
    [currentReviewId, mergeReviews],
  )

  const rawPanelText = usePrettyJson(rawPanel)
  const patchDescriptionLines = useMemo(() => describePatch(currentPatch), [currentPatch])
  const generationInfoLines = useMemo(
    () => describeGenerationInfo(currentPatch?.generation_info),
    [currentPatch],
  )
  const boardNodes = detail?.working_board?.latest_snapshot?.nodes || []
  const boardEdges = detail?.working_board?.latest_snapshot?.edges || []
  const hasPendingConflicts = Boolean(
    currentReview?.status !== 'resolved' && currentReview?.conflicts?.length,
  )
  const pendingConflictCount = hasPendingConflicts ? currentReview?.conflicts?.length || 0 : 0

  useEffect(() => {
    if (!editorRef.current || !detail) return
    syncEditorFromDetail(editorRef.current, detail)
    setSelectedNodeIds([])
  }, [detail])

  function appendMessage(role, content, meta = {}) {
    setChatMessages((messages) => [...messages, createMessage(role, content, meta)])
  }

  function setFeedback(nextStatus, nextRaw = null) {
    setError('')
    setRawModelOutput('')
    setStatus(nextStatus)
    if (nextRaw !== null) setRawPanel(nextRaw)
  }

  function handleFailure(err, fallback) {
    const nextError = summarizeError(err)
    setError(nextError)
    setRawModelOutput(String(err?.payload?.detail?.raw_model_output || ''))
    setStatus(fallback)
    appendMessage('system', `${fallback} ${nextError}`)
    setRawPanel(err?.payload || { message: err?.message || fallback })
  }

  async function loadDetail() {
    try {
      setFeedback('读取 Canvas detail...')
      const json = await requestJson(
        buildUrl(apiBase, `/canvas/sessions/${encodeURIComponent(sessionId)}/detail`),
      )
      startTransition(() => {
        setDetail(json.data)
        setRawPanel(json)
        setStatus('Canvas detail 已刷新。')
      })
    } catch (err) {
      handleFailure(err, '读取 Canvas detail 失败。')
    }
  }

  async function importFeishuDocument() {
    try {
      setFeedback('导入飞书文档中的首个 whiteboard...')
      const json = await requestJson(
        buildUrl(
          apiBase,
          `/canvas/sessions/${encodeURIComponent(sessionId)}/import-feishu-document`,
        ),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ share_url: shareUrl }),
        },
      )
      startTransition(() => {
        setDetail(json.data)
        setRawPanel(json)
        setStatus('飞书文档导入完成，画布已加载。')
        setCurrentPatch(null)
      })
      appendMessage('system', '飞书文档导入完成，右侧画板已加载为 working board。')
      await loadMergeReviews(true)
    } catch (err) {
      handleFailure(err, '导入飞书文档失败。')
    }
  }

  async function importMermaidSyntax() {
    const code = mermaidCode.trim()
    if (!detail?.source_board?.board_id) {
      setStatus('请先导入飞书文档，以便获得目标白板。')
      return
    }
    if (!code) {
      setStatus('请先输入 Mermaid 语法。')
      return
    }

    try {
      setFeedback('把 Mermaid 语法导入当前飞书画板...')
      const json = await requestJson(
        buildUrl(apiBase, `/canvas/sessions/${encodeURIComponent(sessionId)}/import-mermaid`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            code,
            style_type: 1,
            diagram_type: 0,
          }),
        },
      )
      startTransition(() => {
        setDetail(json.data.detail)
        setRawPanel(json)
        setStatus('Mermaid 语法已提交到飞书画板。')
      })
      appendMessage(
        'system',
        `Mermaid 语法已提交到白板 ${detail.source_board.board_id}，并已同步回 working board。`,
      )
    } catch (err) {
      handleFailure(err, '导入 Mermaid 语法失败。')
    }
  }

  async function refreshFeishuDocument(withReview = false) {
    const endpoint = withReview
      ? `/canvas/sessions/${encodeURIComponent(sessionId)}/refresh-feishu-document-review`
      : `/canvas/sessions/${encodeURIComponent(sessionId)}/refresh-feishu-document`

    try {
      await syncCanvasIfNeeded(
        withReview ? '刷新前先同步当前画布...' : '刷新前先同步当前画布...',
      )
      setFeedback(withReview ? '刷新飞书文档并检查冲突...' : '刷新飞书文档...')
      const json = await requestJson(buildUrl(apiBase, endpoint), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ share_url: shareUrl }),
      })
      const nextDetail = withReview ? json.data.detail : json.data
      startTransition(() => {
        setDetail(nextDetail)
        setRawPanel(json)
        setStatus(
          withReview
            ? '飞书文档刷新完成，已同步 merge review 状态。'
            : '飞书文档刷新完成。',
        )
        if (withReview && json.data.merge_review) {
          setMergeReviews((reviews) => mergeReviewListWithLatest(reviews, json.data.merge_review))
          setCurrentReviewId(json.data.merge_review.review_id)
        }
      })
      appendMessage(
        'system',
        withReview
          ? '飞书文档已刷新，并检查了是否存在冲突。'
          : '飞书文档已刷新到当前会话。',
      )
      await loadMergeReviews(true)
    } catch (err) {
      handleFailure(err, '刷新飞书文档失败。')
    }
  }

  async function syncCanvasIfNeeded(statusText = '同步当前 Tldraw 编辑到 working board...') {
    if (!editorRef.current || !detail) {
      return detail
    }

    const snapshot = extractSnapshotFromEditor(editorRef.current, detail)
    const currentSnapshot = detail?.working_board?.latest_snapshot || {}
    if (!hasSnapshotChanged(currentSnapshot, snapshot)) {
      return detail
    }

    try {
      setFeedback(statusText)
      const mappings = buildUserMappings(detail, snapshot)
      await requestJson(
        buildUrl(apiBase, `/canvas/sessions/${encodeURIComponent(sessionId)}/changes`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            change_id: `tldraw-sync-${Date.now()}`,
            session_id: sessionId,
            change_type: 'user_edit',
            actor_type: 'user',
            actor_id: 'tldraw-debugger',
            target_scope: 'board:working',
            payload: {
              latest_snapshot: snapshot,
              crdt_document: snapshot,
              element_mappings: mappings,
            },
            base_version: `v${detail.working_board.latest_version}`,
            result_version: `v${detail.working_board.latest_version + 1}`,
          }),
        },
      )
      const refreshedDetail = await requestJson(
        buildUrl(apiBase, `/canvas/sessions/${encodeURIComponent(sessionId)}/detail`),
      )
      startTransition(() => {
        setDetail(refreshedDetail.data)
      })
      return refreshedDetail.data
    } catch (err) {
      handleFailure(err, '同步当前画布失败。')
      throw err
    }
  }

  async function saveCanvas() {
    const nextDetail = await syncCanvasIfNeeded('同步当前 Tldraw 编辑到 working board...')
    if (nextDetail) {
      setStatus('当前画布已同步到 working board。')
    }
  }

  async function generatePatch(promptText = userPrompt) {
    const normalizedPrompt = String(promptText || '').trim()
    if (!normalizedPrompt) {
      setStatus('请先输入一条 AI 指令。')
      return
    }
    const startedAt = Date.now()
    try {
      const latestDetail =
        (await syncCanvasIfNeeded('生成前先同步当前画布...')) || detail
      const selectedNodeIds = getSelectedNodeIds(editorRef.current)
      const nextMode =
        preferredMode === 'auto'
          ? selectedNodeIds.length
            ? 'targeted_patch'
            : 'full_board'
          : preferredMode === 'targeted_patch' && !selectedNodeIds.length
            ? 'full_board'
          : preferredMode
      setIsGenerating(true)
      setSelectedNodeIds(selectedNodeIds)
      setFeedback(
        nextMode === 'targeted_patch'
          ? '正在根据选中节点生成局部修改...'
          : '正在根据整张画板生成修改...',
      )
      const json = await requestJson(
        buildUrl(apiBase, `/canvas/sessions/${encodeURIComponent(sessionId)}/generate`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            generation_mode: nextMode,
            chat_context: chatMessages
              .filter((message) => message.role === 'user' || message.role === 'assistant')
              .slice(-8)
              .map((message) => ({ role: message.role, content: message.content })),
            user_prompt: normalizedPrompt,
            board_context: latestDetail?.working_board?.latest_snapshot || {},
            session_metadata: {
              source: latestDetail?.source_board?.raw_payload?.source_metadata || {},
            },
            selection_context:
              nextMode === 'targeted_patch' && selectedNodeIds.length
                ? { selectedNodeIds }
                : null,
          }),
        },
      )
      const nextPatchLines = describePatch(json.data)
      const nextInfoLines = describeGenerationInfo(json.data?.generation_info)
      startTransition(() => {
        setCurrentPatch(json.data)
        setRawPanel(json)
        setLastGenerateDurationMs(Date.now() - startedAt)
        setStatus('Patch 已生成，可以直接应用。')
      })
      appendMessage(
        'assistant',
        [
          nextMode === 'targeted_patch'
            ? '我把这次理解成局部修改。'
            : '我把这次理解成整板生成。',
          ...nextPatchLines.slice(1),
          ...nextInfoLines,
          '确认后可以直接应用到右侧画板。',
        ].join('\n'),
        { patchId: json.data?.patch_id },
      )
    } catch (err) {
      setLastGenerateDurationMs(Date.now() - startedAt)
      handleFailure(err, '生成 patch 失败。')
    } finally {
      setIsGenerating(false)
    }
  }

  async function applyPatch() {
    if (!currentPatch) {
      setStatus('请先生成 patch。')
      return
    }
    try {
      setFeedback('应用生成的 patch...')
      const json = await requestJson(
        buildUrl(apiBase, `/canvas/sessions/${encodeURIComponent(sessionId)}/apply-patch`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(currentPatch),
        },
      )
      startTransition(() => {
        setDetail(json.data)
        setRawPanel(json)
        setStatus('Patch 已应用到 working board。')
        setCurrentPatch(null)
      })
      appendMessage('system', 'AI 修改已应用到右侧画板，并写入 working board。')
    } catch (err) {
      handleFailure(err, '应用 patch 失败。')
    }
  }

  async function sendChatMessage(event) {
    event?.preventDefault()
    const prompt = userPrompt.trim()
    if (!prompt || isGenerating) return
    const latestSelectedIds = getSelectedNodeIds(editorRef.current)
    setSelectedNodeIds(latestSelectedIds)
    appendMessage('user', prompt, { selectedNodeIds: latestSelectedIds })
    setUserPrompt('')
    await generatePatch(prompt)
  }

  async function loadMergeReviews(silent = false) {
    try {
      if (!silent) setFeedback('读取 merge reviews...')
      const json = await requestJson(
        buildUrl(apiBase, `/canvas/sessions/${encodeURIComponent(sessionId)}/merge-reviews`),
      )
      startTransition(() => {
        setMergeReviews(json.data || [])
        if (!currentReviewId && json.data?.[0]?.review_id) {
          setCurrentReviewId(json.data[0].review_id)
        }
        if (!silent) {
          setRawPanel(json)
          setStatus('Merge reviews 已刷新。')
        }
      })
    } catch (err) {
      handleFailure(err, '读取 merge reviews 失败。')
    }
  }

  async function resolveReview() {
    if (!currentReview) {
      setStatus('请先读取并选择一个 merge review。')
      return
    }
    try {
      const conflictItems = Array.isArray(currentReview.conflicts) ? currentReview.conflicts : []
      const payloadResolutions = conflictItems
        .map((conflict) => {
          const workingElementId = conflict.working_element_id || conflict.element_id
          const resolution = resolutions[workingElementId]
          if (!workingElementId || !resolution) return null
          return {
            working_element_id: workingElementId,
            resolution,
          }
        })
        .filter(Boolean)

      if (!payloadResolutions.length) {
        setStatus('请先为冲突项选择 source 或 working。')
        return
      }

      setFeedback('提交 merge review 解决结果...')
      const json = await requestJson(
        buildUrl(apiBase, `/canvas/sessions/${encodeURIComponent(sessionId)}/merge-resolve`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            review_id: currentReview.review_id,
            actor_id: 'tldraw-debugger',
            resolutions: payloadResolutions,
          }),
        },
      )
      startTransition(() => {
        setDetail(json.data)
        setRawPanel(json)
        setStatus('Merge review 已提交。')
      })
      appendMessage('system', '冲突解决结果已提交，working board 已更新。')
      await loadMergeReviews(true)
    } catch (err) {
      handleFailure(err, '提交 merge review 失败。')
    }
  }

  async function exportBoard() {
    await exportOrPublish('export')
  }

  async function publishBoard() {
    await exportOrPublish('publish')
  }

  async function exportOrPublish(mode) {
    const action = mode === 'publish' ? '发布' : '导出'
    try {
      await syncCanvasIfNeeded(`${action}前先同步当前画布...`)
      setFeedback(`${action}当前画板到飞书...`)
      const endpoint =
        mode === 'publish'
          ? `/canvas/sessions/${encodeURIComponent(sessionId)}/publish-feishu-board`
          : `/canvas/sessions/${encodeURIComponent(sessionId)}/export-feishu-board`
      const json = await requestJson(buildUrl(apiBase, endpoint), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ allow_conflicted_export: false }),
      })
      const publishGuardMessage =
        mode === 'publish' ? summarizePublishGuard(json.data.publish_result) : ''
      startTransition(() => {
        setDetail(json.data.detail)
        setRawPanel(json)
        setStatus(
          publishGuardMessage ? `画板${action}未完成。` : `画板${action}成功。`,
        )
        setError(publishGuardMessage)
      })
      appendMessage(
        'system',
        publishGuardMessage ? `画板${action}未完成。${publishGuardMessage}` : `画板已${action}到飞书。`,
      )
    } catch (err) {
      handleFailure(err, `画板${action}失败。`)
    }
  }

  async function runFlowSmokeCheck() {
    try {
      setFeedback('运行单人业务链路自检...')
      const smokePrompt = userPrompt.trim() || '根据当前内容整理一张下一步行动画板'
      const importResult = await requestJson(
        buildUrl(
          apiBase,
          `/canvas/sessions/${encodeURIComponent(sessionId)}/import-feishu-document`,
        ),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ share_url: shareUrl }),
        },
      )

      const generateResult = await requestJson(
        buildUrl(apiBase, `/canvas/sessions/${encodeURIComponent(sessionId)}/generate`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            generation_mode: 'full_board',
            chat_context: [],
            user_prompt: smokePrompt,
            board_context: importResult.data.working_board.latest_snapshot,
            session_metadata: {
              source: importResult.data.source_board.raw_payload?.source_metadata || {},
            },
            selection_context: null,
          }),
        },
      )

      const applyResult = await requestJson(
        buildUrl(apiBase, `/canvas/sessions/${encodeURIComponent(sessionId)}/apply-patch`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(generateResult.data),
        },
      )

      const refreshResult = await requestJson(
        buildUrl(
          apiBase,
          `/canvas/sessions/${encodeURIComponent(sessionId)}/refresh-feishu-document-review`,
        ),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ share_url: shareUrl }),
        },
      )

      let currentDetail = refreshResult.data.detail
      let smokeSummary = {
        importedNodes: importResult.data.working_board.latest_snapshot.nodes?.length || 0,
        generatedNodes: generateResult.data.full_board?.nodes?.length || 0,
        appliedVersion: applyResult.data.working_board.latest_version,
        syncStateAfterRefresh: refreshResult.data.detail.session.sync_state,
        resolvedConflicts: 0,
        exportStatus: null,
        publishMode: null,
      }

      if (refreshResult.data.merge_review?.conflicts?.length) {
        const resolveResult = await requestJson(
          buildUrl(apiBase, `/canvas/sessions/${encodeURIComponent(sessionId)}/merge-resolve`),
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              review_id: refreshResult.data.merge_review.review_id,
              actor_id: 'tldraw-debugger',
              resolutions: refreshResult.data.merge_review.conflicts.map((conflict) => ({
                working_element_id: conflict.working_element_id || conflict.element_id,
                resolution: 'working',
              })),
            }),
          },
        )
        currentDetail = resolveResult.data
        smokeSummary = {
          ...smokeSummary,
          resolvedConflicts:
            refreshResult.data.merge_review.summary?.total_conflicts ||
            refreshResult.data.merge_review.conflicts.length,
        }
      }

      const exportResult = await requestJson(
        buildUrl(apiBase, `/canvas/sessions/${encodeURIComponent(sessionId)}/export-feishu-board`),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ allow_conflicted_export: false }),
        },
      )

      const publishResult = await requestJson(
        buildUrl(
          apiBase,
          `/canvas/sessions/${encodeURIComponent(sessionId)}/publish-feishu-board`,
        ),
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ allow_conflicted_export: false }),
        },
      )

      startTransition(() => {
        setDetail(publishResult.data.detail || currentDetail)
        setCurrentPatch(generateResult.data)
        setRawPanel({
          smokeSummary: {
            ...smokeSummary,
            exportStatus: exportResult.data.export_status,
            publishMode: publishResult.data.publish_result.mode,
            publishAccepted: publishResult.data.publish_result.accepted,
          },
          importResult,
          generateResult,
          applyResult,
          refreshResult,
          exportResult,
          publishResult,
        })
        setStatus('单人业务链路自检完成。')
      })
      appendMessage('system', '单人业务链路自检完成，导入、生成、应用、刷新、导出和发布均已跑过。')
      await loadMergeReviews(true)
    } catch (err) {
      handleFailure(err, '单人业务链路自检失败。')
    }
  }

  return (
    <div className="workspace-shell">
      <aside className="conversation-rail">
        <section className="product-header">
          <div>
            <p className="eyebrow">Eko Canvas</p>
            <h1>AI 画板工作台</h1>
          </div>
          <span className={detail ? 'session-pill ready' : 'session-pill'}>
            {detail ? `v${detail.working_board.latest_version}` : '未导入'}
          </span>
        </section>

        <section className="flow-card">
          <div className="section-title">
            <h2>开始工作</h2>
            <span>{detail ? `${boardNodes.length} 个节点` : '等待文档'}</span>
          </div>
          <label>
            飞书文档链接
            <textarea value={shareUrl} onChange={(event) => setShareUrl(event.target.value)} />
          </label>
          <button type="button" className="primary-action" onClick={importFeishuDocument}>
            导入飞书文档
          </button>
        </section>

        <section className="flow-card">
          <div className="section-title">
            <h2>Mermaid 导入</h2>
            <span>
              {detail?.source_board?.board_id
                ? `目标白板 ${detail.source_board.board_id}`
                : '先导入文档'}
            </span>
          </div>
          <label>
            Mermaid 语法
            <textarea value={mermaidCode} onChange={(event) => setMermaidCode(event.target.value)} />
          </label>
          <button
            type="button"
            className="primary-action"
            onClick={importMermaidSyntax}
            disabled={!detail?.source_board?.board_id}
          >
            导入 Mermaid 到当前会话
          </button>
        </section>

        <section className="context-card">
          <div>
            <span className="context-label">当前上下文</span>
            <strong>{selectedNodeSummary(selectedNodeIds)}</strong>
          </div>
          <dl className="compact-meta">
            <div>
              <dt>同步状态</dt>
              <dd>{detail?.session?.sync_state || '-'}</dd>
            </div>
            <div>
              <dt>连线</dt>
              <dd>{boardEdges.length}</dd>
            </div>
            <div>
              <dt>冲突</dt>
              <dd>{pendingConflictCount}</dd>
            </div>
          </dl>
        </section>

        <section className="chat-card">
          <div className="section-title">
            <h2>AI 对话</h2>
            <select
              className="mode-select"
              value={preferredMode}
              onChange={(event) => setPreferredMode(event.target.value)}
            >
              <option value="auto">自动判断</option>
              <option value="targeted_patch">局部修改</option>
              <option value="full_board">整板生成</option>
            </select>
          </div>

          <div className="message-list" aria-live="polite">
            {chatMessages.map((message) => (
              <div key={message.id} className={`message ${message.role}`}>
                <span>
                  {message.role === 'user'
                    ? '你'
                    : message.role === 'assistant'
                      ? 'AI'
                      : '系统'}
                </span>
                <p>{message.content}</p>
              </div>
            ))}
            {isGenerating ? (
              <div className="message assistant pending">
                <span>AI</span>
                <p>正在理解你的指令并生成可应用修改...</p>
              </div>
            ) : null}
          </div>

          {currentPatch ? (
            <div className="pending-patch">
              <div>
                <span>待应用修改</span>
                <strong>{currentPatch.patch_id}</strong>
              </div>
              <ul>
                {patchDescriptionLines.slice(0, 5).map((line, index) => (
                  <li key={`${line}-${index}`}>{line}</li>
                ))}
              </ul>
              <p className="patch-apply-note">
                右侧画板还没有更新；点击下面按钮后才会写入 working board。
              </p>
              {generationInfoLines.length ? (
                <p>{generationInfoLines.join(' ')}</p>
              ) : null}
              <button type="button" onClick={applyPatch}>
                应用这次 AI 修改
              </button>
            </div>
          ) : null}

          <form className="composer" onSubmit={sendChatMessage}>
            <textarea
              value={userPrompt}
              onChange={(event) => setUserPrompt(event.target.value)}
              placeholder="例如：把选中的节点改成下一步行动，或基于整张画板整理一版执行计划"
            />
            <button type="submit" disabled={!userPrompt.trim() || isGenerating}>
              {isGenerating ? '生成中' : '发送'}
            </button>
          </form>
        </section>

        <section className="flow-card">
          <div className="section-title">
            <h2>交付</h2>
            <span>
              {currentPatch ? '先应用 AI 修改，再导出或发布。' : status}
            </span>
          </div>
          {error ? <div className="inline-error">{error}</div> : null}
          {rawModelOutput ? (
            <details className="raw-model-output">
              <summary>查看模型原始输出</summary>
              <pre>{rawModelOutput}</pre>
            </details>
          ) : null}
          {currentPatch ? (
            <button type="button" className="primary-action apply-action" onClick={applyPatch}>
              应用到右侧画板
            </button>
          ) : null}
          <div className="action-row">
            <button
              type="button"
              className="secondary-action"
              onClick={() => refreshFeishuDocument(true)}
            >
              检查冲突
            </button>
            <button type="button" className="secondary-action" onClick={exportBoard}>
              导出
            </button>
            <button
              type="button"
              className={currentPatch ? 'secondary-action' : ''}
              onClick={publishBoard}
            >
              发布
            </button>
          </div>
        </section>

        {hasPendingConflicts ? (
          <section className="flow-card">
            <div className="section-title">
              <h2>冲突处理</h2>
              <span>{currentReview?.status}</span>
            </div>
            <label>
              当前 Review
              <select
                value={currentReviewId}
                onChange={(event) => setCurrentReviewId(event.target.value)}
              >
                <option value="">未选择</option>
                {mergeReviews.map((review) => (
                  <option key={review.review_id} value={review.review_id}>
                    {review.review_id} · {review.status}
                  </option>
                ))}
              </select>
            </label>
            <div className="conflict-list">
              {currentReview.conflicts.map((conflict) => {
                const conflictId = conflict.working_element_id || conflict.element_id
                return (
                  <div className="conflict-card" key={conflictId}>
                    <strong>{conflictId}</strong>
                    <p>飞书：{conflict?.source_node?.text || '-'}</p>
                    <p>画板：{conflict?.working_node?.text || '-'}</p>
                    <select
                      value={resolutions[conflictId] || ''}
                      onChange={(event) =>
                        setResolutions((current) => ({
                          ...current,
                          [conflictId]: event.target.value,
                        }))
                      }
                    >
                      <option value="">选择保留版本</option>
                      <option value="source">保留飞书版本</option>
                      <option value="working">保留画板版本</option>
                    </select>
                  </div>
                )
              })}
            </div>
            <button type="button" onClick={resolveReview}>
              应用冲突处理结果
            </button>
          </section>
        ) : null}

        <section className="advanced-card">
          <button
            type="button"
            className="advanced-toggle"
            onClick={() => setShowAdvanced((value) => !value)}
          >
            {showAdvanced ? '收起高级/调试' : '高级/调试'}
          </button>
          {showAdvanced ? (
            <div className="advanced-content">
              <label>
                API Base
                <input value={apiBase} onChange={(event) => setApiBase(event.target.value)} />
              </label>
              <div className="quick-switches">
                <button
                  type="button"
                  className="secondary-action"
                  onClick={() => setApiBase('http://127.0.0.1:8012/api/v1')}
                >
                  Stub 8012
                </button>
                <button
                  type="button"
                  className="secondary-action"
                  onClick={() => setApiBase('http://127.0.0.1:8000/api/v1')}
                >
                  后端 8000
                </button>
              </div>
              <label>
                Session ID
                <input value={sessionId} onChange={(event) => setSessionId(event.target.value)} />
              </label>
              <div className="button-grid">
                <button type="button" className="secondary-action" onClick={loadDetail}>
                  读取 Detail
                </button>
                <button
                  type="button"
                  className="secondary-action"
                  onClick={() => refreshFeishuDocument(false)}
                >
                  刷新飞书
                </button>
                <button type="button" className="secondary-action" onClick={saveCanvas}>
                  同步画布
                </button>
                <button
                  type="button"
                  className="secondary-action"
                  onClick={() => loadMergeReviews(false)}
                >
                  读取冲突
                </button>
                <button type="button" className="secondary-action" onClick={runFlowSmokeCheck}>
                  链路自检
                </button>
              </div>
              <details>
                <summary>Raw Response</summary>
                <pre>{rawPanelText}</pre>
              </details>
            </div>
          ) : null}
        </section>
      </aside>

      <main className="board-workspace">
        <header className="board-header">
          <div>
            <p className="eyebrow">Tldraw Board</p>
            <h2>右侧画板是主工作区</h2>
            <p>
              导入后可以直接拖拽、编辑文本；发送 AI 指令前会自动同步当前 working board。
            </p>
          </div>
          <div className="board-actions">
            <span className="patch-chip">
              {currentPatch
                ? '有待应用 AI 修改'
                : isGenerating
                  ? 'AI 正在生成'
                  : '画板可编辑'}
            </span>
            {currentPatch ? (
              <button type="button" onClick={applyPatch}>
                应用到画板
              </button>
            ) : null}
            <button type="button" className="secondary-action" onClick={saveCanvas}>
              保存当前编辑
            </button>
          </div>
        </header>

        <section className="canvas-frame">
          <div
            className="canvas-surface"
            onPointerUp={() => setSelectedNodeIds(getSelectedNodeIds(editorRef.current))}
            onKeyUp={() => setSelectedNodeIds(getSelectedNodeIds(editorRef.current))}
          >
            <Tldraw
              onMount={(editor) => {
                editorRef.current = editor
                setSelectedNodeIds(getSelectedNodeIds(editor))
              }}
            />
          </div>
        </section>

        <section className="board-footer">
          <article>
            <span>源画板</span>
            <strong>{detail?.source_board?.source_board_id || '-'}</strong>
          </article>
          <article>
            <span>飞书文档</span>
            <strong>{detail?.source_board?.raw_payload?.source_metadata?.document_id || '-'}</strong>
          </article>
          <article>
            <span>Whiteboard</span>
            <strong>{detail?.source_board?.raw_payload?.source_metadata?.whiteboard_id || '-'}</strong>
          </article>
          <article>
            <span>最近生成</span>
            <strong>
              {lastGenerateDurationMs === null ? '-' : formatElapsedMs(lastGenerateDurationMs)}
            </strong>
          </article>
        </section>
      </main>
    </div>
  )
}

function mergeReviewListWithLatest(reviews, latest) {
  const next = Array.isArray(reviews) ? [...reviews] : []
  const index = next.findIndex((review) => review.review_id === latest.review_id)
  if (index === -1) next.unshift(latest)
  else next[index] = latest
  return next
}

function getSelectedNodeIds(editor) {
  if (!editor || typeof editor.getSelectedShapes !== 'function') return []
  return editor
    .getSelectedShapes()
    .map((shape) => shape?.meta?.nodeId)
    .filter(Boolean)
}

function syncEditorFromDetail(editor, detail) {
  const existingShapes =
    typeof editor.getCurrentPageShapesSorted === 'function'
      ? editor.getCurrentPageShapesSorted()
      : []
  if (existingShapes.length && typeof editor.deleteShapes === 'function') {
    editor.deleteShapes(existingShapes.map((shape) => shape.id))
  }

  const snapshot = detail?.working_board?.latest_snapshot || {}
  const shapes = snapshotToTldrawShapes(snapshot)
  if (shapes.length && typeof editor.createShapes === 'function') {
    editor.createShapes(shapes)
    if (typeof editor.zoomToFit === 'function') {
      editor.zoomToFit({ duration: 0 })
    }
  }
}
