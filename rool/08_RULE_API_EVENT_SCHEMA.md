---
paths:
  - "apps/api/**/*.py"
  - "apps/web/**/*"
  - "packages/shared-types/**/*"
  - "services/ai-runtime/**/*"
---

# API 与事件协议规则

## 统一事件结构
所有模块必须围绕统一事件 schema 协作。

### Event
- eventId: string
- streamId: string
- eventType: string
- severity: "low" | "medium" | "high" | "critical"
- confidence: number
- timestamp: string
- startTime?: string
- endTime?: string
- trackIds: string[]
- participants: Participant[]
- roles: RoleAssignment[]
- sourceFrameRef?: string
- clipRef?: string
- reviewStatus: "pending" | "approved" | "rejected" | "modified"
- reviewerNote?: string

### Participant
- personId?: string
- trackId: string
- bbox?: [number, number, number, number]
- role?: string

### RoleAssignment
- trackId: string
- role: "aggressor" | "victim" | "bystander" | "mutual"
- confidence: number

## 关键要求
- 前端字段命名与后端完全一致
- 不允许前端自己猜字段
- 不允许后端临时返回未登记字段
- 修改 schema 时必须同步更新：
  - packages/shared-types
  - docs/api-contract.md
  - 对应 DTO/类型定义
