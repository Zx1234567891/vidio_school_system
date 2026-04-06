---
name: nextjs-wechat-admin
description: 构建 Next.js 安防前端，风格参考微信的克制与秩序感，包含总览、多路矩阵、预警中心、历史记录、审核与训练管理
disable-model-invocation: true
---

实现 apps/web。

设计目标：
- 大气、现代、克制、企业级
- 借鉴微信的留白、秩序、圆角、柔和绿色强调，不要做成聊天产品
- 信息密度适中，优先可读性和实时态势感知

页面要求：
- /overview：总览 KPI、在线流、今日告警、风险趋势
- /streams：多路视频矩阵，支持选中放大、状态标识、筛选
- /alerts：实时告警列表与详情抽屉
- /history：历史事件查询、筛选、导出
- /review：事件审核、日志在线修改、角色修正
- /settings：流配置、区域配置、阈值配置
- /training：训练任务、模型版本、重训入口

工程要求：
1. 使用 Next.js App Router + TypeScript
2. 使用可组合组件，不要页面里堆大段重复 JSX
3. 服务端状态与本地 UI 状态分离
4. 支持 WebSocket 实时刷新
5. 多宫格页面做自适应渲染：
   - 默认仅少量流高质量展示
   - 其余用低帧率或缩略流
6. 所有页面必须提供 loading / empty / error 状态
7. 所有交互必须能接真实 API，不要只做纯前端假数据
