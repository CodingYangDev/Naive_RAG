# 辰光Agent平台 — 项目说明书

> 本文档旨在帮助开发者快速理解项目全貌，以便高效地修改和扩展代码。

---

## 一、项目概述

辰光Agent平台是一个**企业级AI Agent管理平台**，提供Agent全生命周期管理、知识库(RAG)管理、Prompt工程、模型管理、工具编排、对话日志分析等能力。

项目采用**前后端分离**架构：
- **后端**：Python 3.13 + FastAPI（异步），位于根目录 `src/`
- **前端**：React 19 + TypeScript + Vite，位于 `app/` 目录
- **数据库**：MySQL（通过 SQLAlchemy 异步 ORM）
- **缓存**：Redis（验证码存储等）
- **数据库迁移**：Alembic

### 当前开发状态

| 层 | 状态 |
|---|---|
| 后端 — RBAC模块（用户/角色/权限/认证/验证码） | ✅ 已实现 |
| 后端 — Agent/模型/Prompt/知识库/工具等业务模块 | ❌ 待实现 |
| 前端 — 全部页面UI + Mock数据 | ✅ 已实现 |
| 前端 — 对接真实后端API | ❌ 待实现（已预留API层） |

---

## 二、目录结构

```
chenguang-agent-platform/
├── .env / .env.example          # 后端环境变量
├── alembic.ini                  # Alembic配置
├── alembic/                     # 数据库迁移脚本
│   ├── env.py                   # 迁移环境（异步引擎）
│   └── versions/                # 迁移版本文件
├── requirements.txt             # Python依赖
├── src/                         # ===== 后端源码 =====
│   ├── main.py                  # FastAPI入口，注册路由/中间件/异常处理
│   ├── core/                    # 核心基础设施
│   │   ├── config.py            # 配置管理（pydantic-settings）
│   │   ├── base_model.py        # ORM基类（id + created_at + updated_at）
│   │   ├── base_repository.py   # 通用Repository（CRUD + 分页搜索）
│   │   ├── base_schema.py       # 通用响应Schema（ResponseSchema + PageResult）
│   │   ├── deps.py              # FastAPI依赖注入（get_current_user, PageParams）
│   │   ├── exceptions.py        # 业务异常 + 全局异常处理器
│   │   └── logger.py            # Loguru日志配置
│   ├── infra/                   # 基础设施
│   │   ├── database.py          # SQLAlchemy异步引擎 + 会话工厂
│   │   └── redis_cache.py       # Redis异步客户端
│   ├── middlewares/
│   │   └── logging.py           # 请求日志中间件
│   ├── modules/                 # ===== 业务模块 =====
│   │   ├── auth/                # 认证模块
│   │   ├── captcha/             # 验证码模块
│   │   ├── user/                # 用户模块
│   │   ├── role/                # 角色模块
│   │   └── permission/          # 权限模块
│   └── utils/
│       ├── jwt_utils.py         # JWT编解码
│       └── password_utils.py    # bcrypt密码加密
├── app/                         # ===== 前端源码 =====
│   ├── .env                     # 前端环境变量（VITE_USE_MOCK=true）
│   ├── package.json             # 前端依赖
│   ├── src/
│   │   ├── main.tsx             # 入口
│   │   ├── App.tsx              # 路由定义
│   │   ├── layouts/
│   │   │   └── DashboardLayout.tsx  # 主布局（侧边栏+面包屑+内容区）
│   │   ├── pages/               # 页面组件（按模块分目录）
│   │   ├── components/ui/       # Shadcn UI组件
│   │   ├── services/            # 数据服务层（核心抽象）
│   │   └── hooks/               # 自定义Hooks
│   └── docs/                    # 前端设计文档（各模块详细设计）
└── README.md
```

---

## 三、后端架构详解

### 3.1 启动入口 (`src/main.py`)

```python
# 启动命令
uvicorn src.main:app --port 8080 --reload
```

`create_app()` 函数中：
1. 创建 FastAPI 实例
2. 注册 `LoggingMiddleware`（请求耗时日志）
3. 注册全局异常处理器（`BizException` → 200 + 错误码，`Exception` → 500）
4. 注册路由（所有模块统一 `/api/v1` 前缀）
5. `lifespan` 上下文管理器负责启动/关闭时的资源管理

### 3.2 已注册的API路由

| 前缀 | 模块 | 关键接口 |
|------|------|---------|
| `/api/v1/auth` | 认证 | `POST /login` |
| `/api/v1/captcha` | 验证码 | `GET /`（获取）、`POST /`（验证） |
| `/api/v1/users` | 用户 | CRUD、`GET /me`、`GET /search`、`PUT /{id}/roles` |
| `/api/v1/roles` | 角色 | CRUD、`GET /search`、`PUT /{id}/permissions` |
| `/api/v1/permissions` | 权限 | CRUD、`GET /search` |

### 3.3 分层架构（每个模块统一结构）

```
modules/<module_name>/
├── api.py          # 路由层：接收请求 → 调用Service → 封装ResponseSchema返回
├── service.py      # 业务层：业务逻辑 + 校验 → 调用Repository
├── repository.py   # 数据层：继承BaseRepository，提供特定查询方法
├── model.py        # ORM模型：继承BaseModel（自带id/created_at/updated_at）
└── schema.py       # Pydantic模型：请求体(Create/Update) + 响应体(Read)
```

**依赖注入链**：
```
API层 ← Depends(get_xxx_service)
  └── Service ← __init__(db: AsyncSession)
        └── Repository ← __init__(Model, db)
              └── BaseRepository（通用CRUD + 分页搜索）
```

### 3.4 核心基类

**BaseModel** (`src/core/base_model.py`)：
- 所有ORM模型继承此类
- 自带字段：`id`(BigInteger, 自增主键)、`created_at`、`updated_at`（数据库自动维护）

**BaseRepository** (`src/core/base_repository.py`)：
- 泛型类 `BaseRepository[T]`，T 必须是 BaseModel 子类
- 提供：`get_by_id`、`get_all`、`create`、`update`、`delete`、`delete_by_id`
- 核心方法 `get_page(offset, limit, keyword, search_fields)` → 通用分页 + 模糊搜索

**ResponseSchema** (`src/core/base_schema.py`)：
```python
class ResponseSchema(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

class PageResult(BaseModel, Generic[T]):
    items: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
```

### 3.5 认证机制

1. **登录流程**：`POST /api/v1/auth/login`
   - 前端提交 `{username, password, captcha_key, captcha_code}`
   - 后端先验证验证码（Redis存储，5分钟过期）
   - 再校验用户名/密码（bcrypt）
   - 成功返回 JWT token（30分钟有效期，HS256算法）

2. **接口鉴权**：通过 `Depends(get_current_user)` 注入
   - 从 `Authorization: Bearer <token>` 提取token
   - 解码JWT获取 `user_id`
   - 查询数据库返回完整 User 对象（含角色信息，lazy="selectin"立即加载）

3. **验证码**：`GET /api/v1/captcha`
   - 生成4位随机字符 + UUID key
   - 存入Redis（`captcha:{uuid}` → code，5分钟过期）
   - 返回 base64 图片 + key

### 3.6 数据库模型关系

```
Users ──M:N──> Roles ──M:N──> Permissions
       (user_roles)     (role_permissions)
```

- `user_roles`：用户-角色关联表（复合主键 user_id + role_id）
- `role_permissions`：角色-权限关联表（复合主键 role_id + permission_id）
- 关联关系使用 `lazy="selectin"` 立即加载

### 3.7 配置管理

通过 `.env` 文件 + `pydantic-settings` 管理：

```env
APP_NAME=辰光Agent
APP_ENV=dev
APP_DEBUG=true
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=123456
DB_NAME=chenguang
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=123456
REDIS_DB=0
LOG_LEVEL=DEBUG
LOG_DIR=logs
```

数据库连接串自动拼接：`mysql+asyncmy://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4`

### 3.8 数据库迁移（Alembic）

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "描述本次变更"
# 执行迁移
alembic upgrade head
# 回滚
alembic downgrade -1
```

`alembic/env.py` 已配置异步引擎，从 `.env` 读取数据库URL。

---

## 四、前端架构详解

### 4.1 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 框架 | React + TypeScript | React 19, TS 5.9 |
| 构建 | Vite | 7.x |
| 路由 | React Router | v7 |
| UI组件库 | Shadcn UI (Radix UI) | 最新 |
| 样式 | Tailwind CSS | v4 |
| 图标 | Lucide React | 最新 |
| 状态管理 | React useState（无全局状态库） | - |
| HTTP客户端 | 原生 fetch 封装 | - |

### 4.2 启动方式

```bash
cd app
npm install
npm run dev          # Mock模式（默认）

# 连接真实后端
VITE_USE_MOCK=false VITE_API_BASE=http://localhost:8080/api npm run dev
```

### 4.3 路由结构 (`App.tsx`)

```
/login                          → Login（独立页面，无侧边栏）
/                               → DashboardLayout 包裹
  ├── /                         → Dashboard（工作台）
  ├── /profile                  → Profile（个人信息）
  ├── /settings                 → Settings（个人设置）
  ├── /agents                   → AgentList
  ├── /agents/create            → AgentCreate
  ├── /agents/:id               → AgentDetail
  ├── /agents/:id/edit          → AgentCreate（复用）
  ├── /agents/:id/test          → AgentTest
  ├── /agents/:id/versions      → AgentVersions
  ├── /agents/:id/monitor       → AgentMonitor
  ├── /models                   → ModelList
  ├── /models/providers         → ModelProviders
  ├── /prompts                  → PromptList
  ├── /prompts/create           → PromptCreate
  ├── /prompts/:id              → PromptCreate（复用）
  ├── /prompts/:id/versions     → PromptVersions
  ├── /knowledge                → KnowledgeList
  ├── /knowledge/create         → KnowledgeCreate
  ├── /knowledge/:id            → KnowledgeDetail
  ├── /knowledge/:id/documents  → KnowledgeDocuments
  ├── /knowledge/:id/segments   → KnowledgeSegments
  ├── /knowledge/:id/test       → KnowledgeTest
  ├── /tools                    → ToolList
  ├── /tools/create             → ToolCreate
  ├── /tools/:id                → ToolDetail
  ├── /conversations            → ConversationList
  ├── /conversations/:id        → ConversationDetail
  ├── /analytics                → AnalyticsUsage
  ├── /analytics/costs          → AnalyticsCosts
  ├── /analytics/evaluation     → AnalyticsEvaluation
  ├── /system/users             → SystemUsers
  ├── /system/roles             → SystemRoles
  ├── /system/permissions       → SystemPermissions
  ├── /system/api-keys          → SystemApiKeys
  ├── /system/audit             → SystemAudit
  ├── /system/alerts            → SystemAlerts
  └── /system/settings          → SystemSettings
```

### 4.4 数据服务层（核心设计）

这是前端最重要的架构设计——**Mock/API无缝切换**。

```
app/src/services/
├── config.ts              # USE_MOCK 开关 + API_BASE
├── agent.ts               # 对外暴露：export const agentService = USE_MOCK ? mock : api
├── model.ts               # 同上模式
├── prompt.ts
├── knowledge.ts
├── tool.ts
├── conversation.ts
├── analytics.ts
├── dashboard.ts
├── system.ts
├── types/                 # TypeScript类型定义（所有接口的数据结构）
│   ├── common.ts          # ApiResponse, PaginatedResponse, PaginationParams
│   ├── agent.ts           # Agent, AgentConfig, AgentVersion, AgentStats
│   ├── model.ts           # Model, ModelProvider, ModelCapability
│   ├── prompt.ts          # Prompt, PromptVariable, PromptVersion
│   ├── knowledge.ts       # KnowledgeBase, Document, Segment, RetrievalResult
│   ├── tool.ts            # Tool, ToolDetail, HttpApiConfig, FunctionDefinition
│   ├── conversation.ts    # Conversation, ConversationTurn, TurnTrace
│   ├── analytics.ts       # AnalyticsOverview, DailyStats, CostAnalysis, Evaluation
│   ├── dashboard.ts       # DashboardStats, TrendData, AgentRanking, Alert
│   └── system.ts          # User, Role, Permission, ApiKey, AuditLog, AlertRule
├── mock/                  # Mock实现（带模拟延迟，内存数据操作）
│   ├── agent.ts
│   ├── model.ts
│   ├── ...
│   └── data/              # Mock静态数据（中文内容，15-20条/列表）
└── api/                   # 真实API实现（调用apiClient）
    ├── client.ts          # fetch封装（GET/POST/PUT/DELETE，自动解析data字段）
    ├── agent.ts
    ├── model.ts
    └── ...
```

**切换原理**：
```typescript
// services/config.ts
export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080/api'

// services/agent.ts（每个模块都是这个模式）
import { USE_MOCK } from './config'
import { mockAgentService } from './mock/agent'
import { apiAgentService } from './api/agent'
export const agentService = USE_MOCK ? mockAgentService : apiAgentService
```

**页面调用方式**（所有页面统一）：
```typescript
import { agentService } from '@/services/agent'
const data = await agentService.getAgentList({ page: 1, pageSize: 20 })
```

### 4.5 API客户端 (`services/api/client.ts`)

基于原生 `fetch` 封装的 `ApiClient` 类：
- 支持 `get`、`post`、`put`、`delete` 方法
- GET 请求自动拼接 query params
- 自动解析响应中的 `data` 字段
- 统一 `Content-Type: application/json`
- **自动注入 `Authorization: Bearer <token>`**（从 `localStorage` 读取）
- **401 自动跳转 `/login`**（token 过期处理）
- 业务错误码（`code !== 200`）自动抛出 `Error`

Token 管理通过 `tokenStorage` 工具统一操作：
```typescript
import { tokenStorage } from '@/services/api/client'
tokenStorage.set(token)   // 登录后存储
tokenStorage.get()        // 读取
tokenStorage.remove()     // 退出时清除
```

### 4.5.1 认证服务 (`services/auth.ts`)

新增认证服务，统一管理登录/登出/验证码：

```typescript
import { authService } from '@/services/auth'

// 获取验证码（返回 { key, image } ）
const captcha = await authService.getCaptcha()

// 登录（成功后自动存储 token）
await authService.login({ username, password, captcha_key, captcha_code })

// 退出（清除 token）
authService.logout()

// 检查是否已登录
authService.isLoggedIn()
```

Mock 模式下：验证码前端自生成（4位随机字符），登录不校验密码强度，直接生成 mock token。

### 4.6 主布局 (`layouts/DashboardLayout.tsx`)

- 左侧固定侧边栏：导航菜单（工作台/Agent管理/模型管理/...）+ 系统管理子菜单
- 顶部面包屑导航（根据路由自动生成）
- 右上角用户头像下拉菜单（个人信息/设置/退出）
- 内容区通过 `<Outlet />` 渲染子路由

### 4.7 页面组件结构

每个模块的页面文件位于 `app/src/pages/<module>/`，通过 `index.ts` 统一导出：

```typescript
// pages/agent/index.ts
export { default as AgentList } from './List'
export { default as AgentCreate } from './Create'
export { default as AgentDetail } from './Detail'
// ...
```

页面组件的通用模式：
1. `useState` 管理本地状态
2. `useEffect` 中调用 service 加载数据
3. 使用 Shadcn UI 组件（Card, Table, Badge, Button 等）构建UI
4. 列表页支持搜索、筛选、分页
5. 详情页支持编辑、删除确认对话框

---

## 五、数据模型速查

### 5.1 后端ORM模型（已实现）

| 表名 | 模型类 | 关键字段 |
|------|--------|---------|
| `users` | `User` | username, email, hashed_password, is_active, is_superuser, last_login, roles(M:N) |
| `roles` | `Role` | code, name, description, permissions(M:N) |
| `permissions` | `Permission` | code, name, description |
| `user_roles` | 关联表 | user_id, role_id（复合主键） |
| `role_permissions` | 关联表 | role_id, permission_id（复合主键） |

### 5.2 前端类型定义（完整，对应未来后端模型）

**Agent** (`types/agent.ts`)：
- `Agent`：id, name, description, type(conversation/tool/analysis/creative/workflow), status(active/inactive/error/draft), modelId, config(AgentConfig), successRate, callCount7d, version, ...
- `AgentConfig`：model(模型参数), prompt(系统提示词), rag(知识库检索配置), tools(工具列表), advanced(欢迎语/建议问题/超时)
- `AgentVersion`：版本管理，含 changelog, isCurrent

**Model** (`types/model.ts`)：
- `Model`：id, name, modelId, providerId, capabilities[], contextLength, status, inputPrice, outputPrice, callCount7d, isDefault
- `ModelProvider`：id, name, type(openai/anthropic/aliyun/azure/local/custom), status, endpoint, modelCount

**Prompt** (`types/prompt.ts`)：
- `Prompt`：id, name, description, category, tags[], content, variables(PromptVariable[]), version, status(draft/published), usageCount
- `PromptVariable`：name, type(string/number/boolean/text), description, defaultValue, required

**KnowledgeBase** (`types/knowledge.ts`)：
- `KnowledgeBase`：id, name, description, status(ready/indexing/error/empty), documentCount, segmentCount, vectorCount, storageSize, embeddingModel
- `Document`：id, fileName, fileType(pdf/docx/md/txt/html/csv), status(pending/processing/completed/failed), segmentCount, wordCount
- `Segment`：id, content, wordCount, tokenCount, keywords[], hitCount

**Tool** (`types/tool.ts`)：
- `Tool`：id, name, description, type(builtin/http_api/custom_function), status, callCount7d, successRate, avgLatency
- `ToolDetail`：extends Tool + config(HttpApiConfig | CustomFunctionConfig) + functionDefinition

**Conversation** (`types/conversation.ts`)：
- `Conversation`：id, agentId, agentName, turnCount, totalTokens, totalCost, satisfaction
- `ConversationTurn`：role(user/assistant), content, trace(TurnTrace)
- `TurnTrace`：steps[](receive/retrieval/tool_call/prompt_build/llm_call/response), inputTokens, outputTokens

**System** (`types/system.ts`)：
- `User`：id, username, name, email, roleId, roleName, status
- `Role`：id, name, description, permissions[], userCount, isSystem
- `ApiKey`：id, name, key, permissions, status, rateLimit, callCount
- `AuditLog`：id, userId, action, module, targetId, detail, ipAddress
- `AlertRule`：id, name, condition(metric/operator/threshold/duration), status
- `SystemSettings`：systemName, defaultModel, defaultTemperature, smtpServer, ...

---

## 六、开发约定与规范

### 6.1 后端开发规范

**新增业务模块的标准步骤**：
1. 在 `src/modules/` 下创建模块目录
2. 创建 `model.py`（继承 `BaseModel`）
3. 创建 `schema.py`（Pydantic: XxxCreate, XxxUpdate, XxxRead）
4. 创建 `repository.py`（继承 `BaseRepository[Model]`，定义 `SEARCH_FIELDS`）
5. 创建 `service.py`（注入 Repository，实现业务逻辑）
6. 创建 `api.py`（定义路由，通过 `Depends` 注入 Service）
7. 在 `src/main.py` 中注册路由：`app.include_router(router, prefix="/api/v1")`
8. 在 `alembic/env.py` 中导入新模型
9. 执行 `alembic revision --autogenerate -m "xxx"` + `alembic upgrade head`

**API响应格式**（统一）：
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

**分页响应**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

**业务异常**：
```python
raise BizException(code=10001, message="验证码不存在或已过期")
# 返回 HTTP 200，body: {"code": 10001, "message": "...", "data": null}
```

### 6.2 前端开发规范

**新增页面的标准步骤**：
1. 在 `app/src/pages/<module>/` 下创建页面组件
2. 在 `index.ts` 中导出
3. 在 `App.tsx` 中添加路由
4. 在 `DashboardLayout.tsx` 中添加导航菜单项（如需要）

**新增服务接口的标准步骤**：
1. 在 `services/types/<module>.ts` 中定义类型
2. 在 `services/mock/<module>.ts` 中实现Mock版本
3. 在 `services/api/<module>.ts` 中实现API版本
4. 在 `services/<module>.ts` 中做 Mock/API 切换导出

**文件命名**：
- 页面组件：PascalCase（`AgentList.tsx`）
- 服务文件：camelCase（`agent.ts`）
- 类型文件：camelCase（`agent.ts`）

**路径别名**：`@/` 映射到 `app/src/`

---

## 七、环境搭建

### 后端

```bash
# 1. 创建Python环境
conda create -n chenguang python=3.13
conda activate chenguang

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入MySQL和Redis连接信息

# 4. 执行数据库迁移
alembic upgrade head

# 5. 启动
uvicorn src.main:app --port 8080 --reload
```

### 前端

```bash
cd app
npm install
npm run dev    # 默认Mock模式，访问 http://localhost:5173
```

### 健康检查

- 后端：`GET http://localhost:8080/health`
- 前端：浏览器访问 `http://localhost:5173`

---

## 八、关键依赖清单

### 后端 (Python)

| 包 | 用途 |
|---|---|
| fastapi | Web框架 |
| uvicorn | ASGI服务器 |
| sqlalchemy | 异步ORM |
| asyncmy | MySQL异步驱动 |
| alembic | 数据库迁移 |
| pydantic / pydantic-settings | 数据校验 / 配置管理 |
| redis | 异步Redis客户端 |
| PyJWT | JWT编解码 |
| bcrypt | 密码加密 |
| captcha + pillow | 图片验证码生成 |
| loguru | 日志 |

### 前端 (Node.js)

| 包 | 用途 |
|---|---|
| react / react-dom | UI框架 |
| react-router-dom | 路由 |
| radix-ui | 无样式UI原语（Shadcn底层） |
| tailwindcss | 原子CSS |
| lucide-react | 图标库 |
| class-variance-authority + clsx + tailwind-merge | 样式工具 |
| vite | 构建工具 |
| typescript | 类型系统 |

---

## 九、待实现功能清单

### 后端待实现模块

以下模块前端UI和Mock数据已就绪，需要后端实现对应的 API → Service → Repository → Model：

1. **Agent管理**：Agent CRUD、版本管理、启动/停止、发布、测试、监控
2. **模型管理**：模型 CRUD、供应商管理、连接测试
3. **Prompt管理**：Prompt CRUD、版本管理、发布、测试
4. **知识库管理**：知识库 CRUD、文档上传/处理、分段管理、检索测试、重新索引
5. **工具管理**：工具注册/CRUD、测试、启用/禁用、调用日志
6. **对话日志**：对话列表/详情、标注、导出
7. **数据统计**：用量统计、费用分析、效果评估
8. **系统管理扩展**：API Key管理、审计日志、告警规则、系统配置

### 前端待完善

1. ~~**API客户端增强**：添加 Authorization header（JWT token注入）~~ ✅ 已完成
2. ~~**登录页对接**：调用真实 `/api/v1/auth/login`，存储token~~ ✅ 已完成
3. ~~**路由守卫**：未登录重定向到 `/login`~~ ✅ 已完成
4. ~~**错误处理**：统一处理 401（token过期）→ 跳转登录~~ ✅ 已完成
5. ~~**用户管理页对接**：`/system/users` 对接真实后端 CRUD + 分配角色 + 分页~~ ✅ 已完成
6. ~~**角色管理页对接**：`/system/roles` 对接真实后端 CRUD + 分配权限 + 分页~~ ✅ 已完成
7. ~~**权限管理页**：`/system/permissions` 完整 CRUD + 分页 + 模块分类~~ ✅ 已完成
8. ~~**业务模块页面对接**：Agent/Prompt/Knowledge/Tool 的创建、详情、版本管理页面全部使用新 API 类型~~ ✅ 已完成
9. **表单校验**：集成 React Hook Form + Zod
10. **图表集成**：集成 Recharts 展示趋势图

---

## 十、前端API接口规范（后端实现参考）

前端已定义的完整API接口列表，后端实现时需遵循此规范。详见 `app/docs/10-API接口规范.md`。

通用响应格式：
```typescript
interface ApiResponse<T> {
  code: 0          // 成功
  message: 'success'
  data: T
}

interface PaginatedResponse<T> {
  data: T[]        // Mock层简化版
  total: number
  page: number
  pageSize: number
}
```

**注意**：前端 `apiClient` 会自动提取 `response.data`，所以后端返回 `{"code": 200, "message": "success", "data": {...}}` 即可，前端拿到的就是 `data` 部分。

---

## 十一、设计文档索引

前端详细设计文档位于 `app/docs/`：

| 文件 | 内容 |
|------|------|
| `00-架构总览.md` | 系统架构、路由、技术栈、数据服务层设计、开发约定 |
| `01-工作台.md` | Dashboard数据大盘设计 |
| `02-Agent管理.md` | Agent全生命周期管理设计 |
| `03-模型管理.md` | 模型和供应商管理设计 |
| `04-Prompt管理.md` | Prompt工程化管理设计 |
| `05-知识库管理.md` | RAG知识库全流程设计 |
| `06-工具管理.md` | 工具注册和编排设计 |
| `07-对话日志.md` | 对话记录和链路追踪设计 |
| `08-数据统计.md` | 用量、费用、效果评估设计 |
| `09-系统管理.md` | 用户、角色、安全、审计设计 |
| `10-API接口规范.md` | 完整接口定义、Mock层设计、切换方案 |

---

## 十二、变更记录

### 2026-03-19 — 前端对接真实后端（认证 + 系统管理）

**涉及文件**：

| 文件 | 变更内容 |
|------|---------|
| `app/src/services/api/client.ts` | 重写：自动注入 JWT token、401 自动跳转登录、业务错误码处理 |
| `app/src/services/api/auth.ts` | 新增：对接 `/api/v1/captcha`、`/api/v1/auth/login` |
| `app/src/services/mock/auth.ts` | 新增：Mock 认证服务（前端自生成验证码） |
| `app/src/services/auth.ts` | 新增：Mock/API 切换入口 |
| `app/src/services/api/system.ts` | 重写：对接真实后端用户/角色/权限 CRUD 接口 |
| `app/src/services/system.ts` | 更新：导出真实后端类型 |
| `app/src/components/AuthGuard.tsx` | 新增：路由守卫，未登录跳转 `/login` |
| `app/src/App.tsx` | 更新：所有受保护路由包裹 `AuthGuard` |
| `app/src/pages/Login.tsx` | 重写：对接真实验证码图片 + 登录接口，Mock 模式兼容 |
| `app/src/pages/system/Users.tsx` | 重写：支持真实后端分页搜索、创建用户、分配角色 |
| `app/src/pages/system/Roles.tsx` | 重写：支持真实后端 CRUD、分配权限 |
| `app/src/layouts/DashboardLayout.tsx` | 更新：退出登录调用 `authService.logout()` |

**接口对应关系**：

| 功能 | 前端调用 | 后端接口 |
|------|---------|---------|
| 获取验证码 | `authService.getCaptcha()` | `GET /api/v1/captcha` |
| 用户登录 | `authService.login(...)` | `POST /api/v1/auth/login` |
| 用户列表（分页） | `apiSystemService.getUsers(...)` | `GET /api/v1/users/search` |
| 创建用户 | `apiSystemService.createUser(...)` | `POST /api/v1/users` |
| 删除用户 | `apiSystemService.deleteUser(id)` | `DELETE /api/v1/users/{id}` |
| 分配用户角色 | `apiSystemService.assignUserRoles(...)` | `PUT /api/v1/users/{id}/roles` |
| 角色列表 | `apiSystemService.getRoles()` | `GET /api/v1/roles/` |
| 创建角色 | `apiSystemService.createRole(...)` | `POST /api/v1/roles` |
| 更新角色 | `apiSystemService.updateRole(...)` | `PUT /api/v1/roles/{id}` |
| 删除角色 | `apiSystemService.deleteRole(id)` | `DELETE /api/v1/roles/{id}` |
| 分配角色权限 | `apiSystemService.assignRolePermissions(...)` | `PUT /api/v1/roles/{id}/permissions` |
| 权限列表 | `apiSystemService.getPermissions()` | `GET /api/v1/permissions/` |
| 创建权限 | `apiSystemService.createPermission(...)` | `POST /api/v1/permissions` |
| 更新权限 | `apiSystemService.updatePermission(...)` | `PUT /api/v1/permissions/{id}` |
| 删除权限 | `apiSystemService.deletePermission(id)` | `DELETE /api/v1/permissions/{id}` |

**切换到真实后端**：
```bash
cd app
VITE_USE_MOCK=false VITE_API_BASE=http://localhost:8080/api npm run dev
```

### 2026-03-20 — 业务模块页面全面对接新API类型

**涉及文件**：

| 文件 | 变更内容 |
|------|---------|
| `app/src/pages/agent/Create.tsx` | 重写：支持创建/编辑模式，使用 snake_case 字段（`model_id`, `config.system_prompt` 等），加载已有 Agent 数据回填 |
| `app/src/pages/agent/Detail.tsx` | 重写：使用 `AgentRead` 类型，展示 `call_count_7d`/`success_rate`，内嵌版本历史列表 |
| `app/src/pages/agent/Versions.tsx` | 重写：调用真实 `getAgentVersions` + `rollbackAgent` API，支持回滚操作 |
| `app/src/pages/prompt/Create.tsx` | 重写：支持创建/编辑/发布，使用 `PromptVariableSchema` 类型，变量管理 + 预览 |
| `app/src/pages/prompt/Versions.tsx` | 重写：调用真实 `getPromptVersions` + `rollbackPrompt` API，点击版本查看内容 |
| `app/src/pages/knowledge/Create.tsx` | 重写：调用真实 `createKnowledgeBase` API，创建后跳转详情页 |
| `app/src/pages/tool/Create.tsx` | 重写：调用真实 `createTool` API，自动生成 `function_definition` |
| `app/src/pages/tool/Detail.tsx` | 重写：使用 `ToolRead` 类型，展示统计数据，支持 JSON 参数测试工具 |

**关键变化**：
- 所有页面不再引用旧 `@/services/types/` 目录下的类型，改用各模块 API 服务导出的类型
- 字段名全部改为 snake_case（`model_id`, `call_count_7d`, `success_rate`, `avg_latency` 等）
- 版本管理页面（Agent/Prompt）均支持真实回滚操作
- Tool Detail 支持 JSON 格式参数输入并调用 `testTool` API

### 2026-03-19（二）— 用户/角色/权限分页 + 权限管理完整页面

**变更内容**：

| 文件 | 变更内容 |
|------|---------|
| `app/src/components/Pagination.tsx` | 新增：通用分页组件，支持省略号、页码跳转 |
| `app/src/pages/system/Users.tsx` | 重写：加入分页（PAGE_SIZE=10），搜索时自动重置页码 |
| `app/src/pages/system/Roles.tsx` | 重写：加入分页，支持关键词搜索，编辑/删除/分配权限 |
| `app/src/pages/system/Permissions.tsx` | 新增：权限完整 CRUD 页面，含分页、模块分类标签、创建/编辑/删除弹窗 |
| `app/src/pages/system/index.ts` | 更新：导出 `SystemPermissions` |
| `app/src/App.tsx` | 更新：注册 `/system/permissions` 路由 |
| `app/src/layouts/DashboardLayout.tsx` | 更新：侧边栏加入「权限管理」菜单项 |
| `app/src/services/mock/system.ts` | 更新：新增 `getRolesPaged`、`getPermissionsPaged`、`createPermission`、`updatePermission`、`deletePermission` |
| `app/src/services/mock/data/system.ts` | 更新：新增 25 条 `mockPermissions` 数据 |

**分页组件使用方式**：
```tsx
import Pagination from '@/components/Pagination'

<Pagination page={page} total={total} pageSize={10} onChange={setPage} />
```

**权限页面功能**：
- 列表展示：ID、模块标签（颜色区分）、权限编码（code 格式）、名称、描述
- 搜索：按编码/名称关键词过滤，搜索时自动回到第1页
- 创建：填写编码（格式建议 `模块:操作`）、名称、描述
- 编辑：可修改名称和描述（编码不可改）
- 删除：二次确认，提示影响范围
- 统计卡片：总权限数 + 当前页前3个模块的权限数

### 2026-03-20（二）— 知识库管理完整功能（MinIO + 配置 + 分段预览）

**涉及文件**：

| 文件 | 变更内容 |
|------|---------|
| `app/src/services/api/knowledge.ts` | 扩展类型：`KnowledgeBaseRead` 新增分段策略/检索策略字段；`DocumentRead` 新增 `minio_path`；新增 `KnowledgeBaseConfig`、`RetrievalTestResult` 类型；新增 `updateKnowledgeBaseConfig`、`retryDocument`、`getDocumentSegments`、`testRetrieval` 接口 |
| `app/src/services/mock/knowledge.ts` | 对应补充所有新接口的 Mock 实现 |
| `app/src/services/knowledge.ts` | 重新导出新类型和方法 |
| `app/src/pages/knowledge/Create.tsx` | 重写：左右两栏，左=基本信息+Embedding，右=分段策略+检索策略 |
| `app/src/pages/knowledge/Detail.tsx` | 重写：文档管理Tab（表格+分页+Sheet分段预览）、概览Tab、配置Tab（可编辑） |
| `app/src/pages/knowledge/Documents.tsx` | 重写：文档列表分页，"查看分段"打开 Sheet 抽屉，支持重试失败文档 |
| `app/src/pages/knowledge/Segments.tsx` | 重写：新增文档下拉过滤，支持 `document_id` 参数 |
| `app/src/pages/knowledge/Test.tsx` | 重写：左右两栏，调用真实 `testRetrieval` API |
| `app/docs/知识库后端开发流程.md` | 新增：后端完整开发流程文档（MinIO、异步分段处理、pgvector） |

**新增 API 接口**：

| 接口 | 说明 |
|------|------|
| `PUT /knowledge-bases/{id}/config` | 更新分段策略/检索策略配置 |
| `POST /knowledge-bases/{kb_id}/documents/{doc_id}/retry` | 重试失败文档 |
| `GET /knowledge-bases/{kb_id}/documents/{doc_id}/segments` | 按文档查询分段 |
| `GET /knowledge-bases/{kb_id}/segments?document_id=` | 按文档过滤分段 |
| `POST /knowledge-bases/{kb_id}/retrieval-test` | 检索测试 |
