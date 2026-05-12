import { WorkspaceData } from "@/types/workspace";

export const workspaceData: WorkspaceData = {
  title: "Eko 工作台",
  subtitle: "将 IM 讨论转化为文档、汇报画布和可同步的项目记录。",
  statusBadges: [
    { label: "演示就绪", tone: "success" },
    { label: "模拟模式", tone: "info" },
    { label: "实时连接待接入", tone: "neutral" },
  ],
  systemNote:
    "当前使用本地模拟数据支撑演示，后续可替换为真实飞书接口、多维表格接口和实时状态流。",
  scenarios: {
    chat: {
      key: "chat",
      label: "聊天",
      accent: "chat",
      railTitle: "桌面端 /",
      railSubtitle: "聊天",
      railCaption: "即时回复模式",
      switcherLabel: "A",
      chatPanelTitle: "聊天面板",
      groupName: "飞书项目群",
      missionTitle: "飞书即时回复确认",
      missionDescription: "轻量问答只返回文本，不触发主创作区域重绘。",
      intentBadge: "聊天",
      confidence: "96%",
      contextQuality: "高",
      messages: [
        {
          id: "chat-1",
          author: "Mia",
          role: "member",
          time: "09:12",
          body: "大家下午开会时间再确认一下，今天的 Eko 演示到底几点开始？",
          avatar: "M",
        },
        {
          id: "chat-2",
          author: "Leo",
          role: "member",
          time: "09:13",
          body: "咱们下午几点开会？顺便提醒一下今天要把会议议程和设备都确认好。",
          mention: "@Eko",
          avatar: "L",
        },
        {
          id: "chat-3",
          author: "Eko",
          role: "eko",
          time: "09:13",
          body: "今天下午 3:30 在产品组飞书会议室，建议仅安排 20 分钟。我会在 3:25 再同步一次提醒。",
          avatar: "E",
        },
        {
          id: "chat-4",
          author: "Mia",
          role: "member",
          time: "09:14",
          body: "收到，谢谢！",
          avatar: "M",
        },
      ],
      workflow: [
        { id: "1", title: "分析消息上下文", status: "completed" },
        { id: "2", title: "判断当前意图", status: "completed" },
        { id: "3", title: "按需检索知识库", status: "completed" },
        { id: "4", title: "生成回复 / 文档 / 画布", status: "running" },
        { id: "5", title: "同步到多维表格", status: "pending" },
        { id: "6", title: "回传飞书群", status: "pending" },
      ],
      output: {
        kind: "chat",
        title: "聊天回复",
        description: "在聊天模式下，Eko 只在 IM 中回复，不刷新文档或画布区域。",
        reply:
          "今天下午 3:30 在产品组飞书会议室，建议仅安排 20 分钟。我会在 3:25 再同步一次提醒。",
        placeholders: [
          { title: "文档区", subtitle: "聊天模式下未刷新" },
          { title: "画布区", subtitle: "聊天模式下未刷新" },
        ],
      },
      contextSources: [
        {
          id: "chat-context-1",
          title: "即时消息上下文",
          description: "最近 5 轮群聊上下文已读取。",
          status: "completed",
        },
        {
          id: "chat-context-2",
          title: "知识库检索",
          description: "已载入活动复盘与项目模板。",
          status: "completed",
        },
        {
          id: "chat-context-3",
          title: "多维表格进度",
          description: "当前尚未触发同步动作。",
          status: "pending",
        },
      ],
      sourceEvidence: [
        {
          id: "chat-evidence-1",
          title: "飞书聊天记录",
          description: "来自项目组的会议提醒与时间确认线程。",
          tone: "chat",
        },
        {
          id: "chat-evidence-2",
          title: "知识库文档",
          description: "活动复盘文档与执行清单。",
          tone: "document",
        },
        {
          id: "chat-evidence-3",
          title: "多维表格记录",
          description: "轻量回复场景未创建记录。",
          tone: "record",
        },
      ],
      syncActions: [
        { id: "chat-sync-1", title: "同步到多维表格", status: "pending" },
        { id: "chat-sync-2", title: "发送到飞书群", status: "running" },
        { id: "chat-sync-3", title: "生成待办", status: "pending" },
      ],
    },
    doc: {
      key: "doc",
      label: "文稿",
      accent: "doc",
      railTitle: "桌面端 /",
      railSubtitle: "文稿",
      railCaption: "文档预览模式",
      switcherLabel: "B",
      chatPanelTitle: "聊天面板",
      groupName: "飞书项目群",
      missionTitle: "周会需求排期同步纪要",
      missionDescription: "将本周项目群的排期同步讨论整理为结构化会议纪要，明确各端进度和上线安排。",
      intentBadge: "文稿",
      confidence: "98%",
      contextQuality: "高",
      messages: [
        {
          "id": "chat_001",
          "author": "刘明（产品）",
          "role": "member",
          "time": "09:12",
          "body": "大家早上好，今天同步一下本周的需求排期哈",
          "avatar": "刘"
        },
        {
          "id": "chat_005",
          "author": "刘明（产品）",
          "role": "member",
          "time": "09:15",
          "body": "本周重点是用户中心2.0的上线，现在各端进度怎么样了？",
          "avatar": "刘"
        },
        {
          "id": "chat_006",
          "author": "张雯（设计）",
          "role": "member",
          "time": "09:16",
          "body": "设计这边已经全部完成了，原型和UI稿都上传到Figma了，链接在群公告里，有问题随时找我",
          "avatar": "张"
        },
        {
          "id": "chat_007",
          "author": "李军（后端）",
          "role": "member",
          "time": "09:17",
          "body": "后端接口开发完了，今天上午在做单元测试，下午可以提测",
          "avatar": "李"
        },
        {
          "id": "chat_008",
          "author": "王浩（前端）",
          "role": "member",
          "time": "09:18",
          "body": "前端页面开发了80%，剩下的个人中心设置页今天能做完，明天可以和后端联调",
          "avatar": "王"
        },
        {
          "id": "chat_020",
          "author": "刘明（产品）",
          "role": "member",
          "time": "09:35",
          "body": "好的，那今天的同步就到这里，大家有问题随时在群里说哈",
          "avatar": "刘"
        }
      ],
      workflow: [
        { id: "1", title: "分析消息上下文", status: "completed" },
        { id: "2", title: "判断当前意图", status: "completed" },
        { id: "3", title: "按需检索知识库", status: "completed" },
        { id: "4", title: "生成回复 / 文档 / 画布", status: "running" },
        { id: "5", title: "同步到多维表格", status: "pending" },
        { id: "6", title: "回传飞书群", status: "pending" },
      ],
      output: {
        kind: "doc",
        title: "周会排期同步纪要",
        description: "基于2026年5月12日项目群聊天记录生成的结构化会议纪要，明确各端进度和上线安排。",
        badge: "会议纪要",
        documentTitle: "用户中心2.0上线排期同步会议纪要",
        sections: [
          {
            title: "会议概览",
            body: "本次会议于2026年5月12日上午9:12在项目群召开，由产品经理刘明主持，设计、前端、后端负责人参会，主要同步用户中心2.0版本上线进度及本周工作安排。"
          },
          {
            title: "各端进度汇报",
            bullets: [
              "设计端：原型和UI稿已全部完成并上传至Figma，链接已发布在群公告，可随时查阅",
              "后端：接口开发全部完成，今日上午进行单元测试，下午可提交测试",
              "前端：页面开发完成80%，剩余个人中心设置页今日内完成，明日开始与后端联调"
            ]
          },
          {
            title: "上线时间安排",
            bullets: [
              "周三下午：内部测试",
              "周四：预发布环境验证",
              "周五：正式上线",
              "各端均已确认时间节点可行，无明显风险"
            ]
          },
          {
            title: "新增需求与优化",
            bullets: [
              "登录页验证码优化：用户反馈现有验证码体验不佳，设计今日下午输出新版设计稿，前端半天可完成开发，随本次版本一同上线"
            ]
          },
          {
            title: "重要通知",
            bullets: [
              "周三晚上将进行数据迁移，预计会有15分钟的服务不可用，产品将提前发布公告通知用户",
              "首页加载慢的bug已由前端修复完成，可进行测试验证"
            ]
          },
          {
            title: "下一步行动",
            body: "各端按计划推进工作，遇到问题及时在群内沟通，确保用户中心2.0版本按计划顺利上线。"
          }
        ],
      },
      contextSources: [
        {
          id: "doc-context-1",
          title: "即时消息上下文",
          description: "已整理项目群20条聊天记录，提取核心进度和安排。",
          status: "completed",
        },
        {
          id: "doc-context-2",
          title: "知识库检索",
          description: "已加载会议纪要模板和项目上线流程规范。",
          status: "completed",
        },
        {
          id: "doc-context-3",
          title: "多维表格进度",
          description: "文档内容尚未正式回写。",
          status: "pending",
        },
      ],
      sourceEvidence: [
        {
          id: "doc-evidence-1",
          title: "飞书聊天记录",
          description: "包含2026年5月12日项目群排期同步完整对话。",
          tone: "chat",
        },
        {
          id: "doc-evidence-2",
          title: "知识库文档",
          description: "会议纪要标准模板v3.0。",
          tone: "document",
        },
        {
          id: "doc-evidence-3",
          title: "多维表格记录",
          description: "项目进度记录待同步。",
          tone: "record",
        },
      ],
      syncActions: [
        { id: "doc-sync-1", title: "同步到多维表格", status: "pending" },
        { id: "doc-sync-2", title: "发送到飞书群", status: "running" },
        { id: "doc-sync-3", title: "生成待办", status: "pending" },
      ],
    },
    canvas: {
      key: "canvas",
      label: "画布",
      accent: "canvas",
      railTitle: "桌面端 /",
      railSubtitle: "画布",
      railCaption: "汇报画布模式",
      switcherLabel: "C",
      chatPanelTitle: "聊天面板",
      groupName: "飞书项目群",
      missionTitle: "汇报画布与演示结构生成",
      missionDescription: "将会议纪要与执行方案进一步转为汇报画布，用于生成可讲述的演示文稿结构。",
      intentBadge: "画布",
      confidence: "88%",
      contextQuality: "中",
      messages: [
        {
          id: "canvas-1",
          author: "Leo",
          role: "member",
          time: "11:06",
          body: "我们这周要向老师汇报，把刚才整理好的会议纪要转成更适合展示的故事线吧。",
          avatar: "L",
        },
        {
          id: "canvas-2",
          author: "Leo",
          role: "member",
          time: "11:07",
          body: "能不能把刚整理好的方案做成汇报结构？最好分模块展示，后面直接拿去做 PPT。",
          mention: "@Eko",
          avatar: "L",
        },
        {
          id: "canvas-3",
          author: "Eko",
          role: "eko",
          time: "11:08",
          body: "已进入汇报画布模式，我会把会议结论和执行方案转换成演示文稿结构，提炼模块、流程、风险与下一步动作。",
          avatar: "E",
        },
        {
          id: "canvas-4",
          author: "Mia",
          role: "member",
          time: "11:10",
          body: "这个结构挺清楚，帮我再补一下风险提醒和下一步计划，之后就能直接出 PPT 了。",
          avatar: "M",
        },
      ],
      workflow: [
        { id: "1", title: "分析消息上下文", status: "completed" },
        { id: "2", title: "判断当前意图", status: "completed" },
        { id: "3", title: "按需检索知识库", status: "completed" },
        { id: "4", title: "生成回复 / 文档 / 画布", status: "running" },
        { id: "5", title: "同步到多维表格", status: "warning" },
        { id: "6", title: "回传飞书群", status: "pending" },
      ],
      output: {
        kind: "canvas",
        title: "汇报画布预览",
        description: "用于讲述会议结论与执行方案的汇报画布，已经具备继续细化成演示文稿的基础。",
        buttonLabel: "在画布中打开",
        nodes: [
          {
            id: "canvas-node-1",
            index: 1,
            title: "为什么要做",
            bullets: ["市场场景", "用户需求上升", "活动场景串起关键痛点"],
            icon: "trend",
          },
          {
            id: "canvas-node-2",
            index: 2,
            title: "我们的方案",
            bullets: ["传播节点", "内容规划", "触达节奏清晰"],
            icon: "rocket",
          },
          {
            id: "canvas-node-3",
            index: 3,
            title: "执行计划",
            bullets: ["时间线", "负责人分工", "关键里程碑"],
            icon: "calendar",
          },
          {
            id: "canvas-node-4",
            index: 4,
            title: "复盘收益",
            bullets: ["到场率提升", "经验沉淀", "协作提效"],
            icon: "spark",
          },
          {
            id: "canvas-node-5",
            index: 5,
            title: "风险与对策",
            bullets: ["时间冲突", "素材准备不足", "预留替代方案"],
            icon: "alert",
          },
          {
            id: "canvas-node-6",
            index: 6,
            title: "下一步行动",
            bullets: ["确认时间", "同步老师", "回写到多维表格"],
            icon: "check",
          },
        ],
        flowCards: [
          { id: "flow-1", title: "输入", description: "飞书群讨论" },
          { id: "flow-2", title: "智能体", description: "意图路由 + 知识检索 + 生成" },
          { id: "flow-3", title: "输出", description: "汇报画布预览 + 同步项目记录" },
        ],
      },
      contextSources: [
        {
          id: "canvas-context-1",
          title: "即时消息上下文",
          description: "已识别来自群主的汇报画布请求。",
          status: "completed",
        },
        {
          id: "canvas-context-2",
          title: "知识库检索",
          description: "已载入文档摘要与演示结构提示。",
          status: "completed",
        },
        {
          id: "canvas-context-3",
          title: "多维表格进度",
          description: "导出元数据与负责人映射仍待处理。",
          status: "warning",
        },
      ],
      sourceEvidence: [
        {
          id: "canvas-evidence-1",
          title: "飞书聊天记录",
          description: "群内已明确提出生成汇报结构与演示文稿的需求。",
          tone: "chat",
        },
        {
          id: "canvas-evidence-2",
          title: "知识库文档",
          description: "汇报叙事指南与案例示例。",
          tone: "document",
        },
        {
          id: "canvas-evidence-3",
          title: "多维表格记录",
          description: "审批后仍待同步汇报记录。",
          tone: "record",
        },
      ],
      syncActions: [
        { id: "canvas-sync-1", title: "同步到多维表格", status: "warning" },
        { id: "canvas-sync-2", title: "发送到飞书群", status: "pending" },
        { id: "canvas-sync-3", title: "生成待办", status: "running" },
      ],
    },
  },
};
