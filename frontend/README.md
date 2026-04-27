# Canvas 联调台

这个前端工程用于验证单人画板业务闭环：

1. 输入飞书文档 `share_url`
2. 导入首个 whiteboard 到 canvas session
3. 在 Tldraw 中查看和编辑 working board
4. 生成并应用 patch
5. 刷新飞书源内容并处理冲突
6. 导出或发布回飞书

## 本地运行

先启动后端，默认地址为 `http://localhost:8000`。

然后在 `frontend/` 目录执行：

```bash
npm install
npm run dev
```

默认联调页地址：

- `http://localhost:5173`

生产构建验证：

```bash
npm run build
```

## 当前约束

- 只做单人联调，不做多人协同
- 画布使用 `Tldraw`
- 当前优先支持节点导入、拖拽、文本编辑和回写
- 边线只做弱展示，不追求完整白板能力
