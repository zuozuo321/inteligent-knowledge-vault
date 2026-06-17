# 知识库工作流 (Knowledge Base Workflow)

基于 **Karpathy LLM Wiki 方法论** 的个人知识库系统。
利用 Claude Code 作为 AI 引擎，通过 MCP 服务端连接 Obsidian 知识库，
实现素材的自动导入、编译、查询和回填。

## 架构图

```
+------------+     +---------+     +-------------+     +----------+
|  用户      | --> | VSCode  | --> | Claude Code | --> | 知识库   |
| (提问/整理) |     | (IDE)   |     | (AI 引擎)   |     | (Vault)  |
+------------+     +---------+     +-------------+     +----------+
                      |                  |                  |
                      |                  v                  |
                      |         +-----------------+         |
                      |         | MCP 服务端      |         |
                      +-------->| - obsidian-mcp  |<--------+
                                | - bilibili-mcp  |
                                +-----------------+
                                       |
                                       v
                                +-----------------+
                                | 外部服务        |
                                | - B站 API      |
                                | - Whisper (本地)|
                                +-----------------+
```

## 六大组件

### 1. ccswitch (API 代理)
管理 API 密钥和请求路由，将 Claude Code 的 API 请求转发到兼容的模型后端。

### 2. VSCode (集成开发环境)
提供编辑器界面，集成 Claude Code 扩展，是 AI 交互的主要界面。

### 3. Claude Code (AI 引擎)
工作流的智能核心，负责理解用户意图、调用 MCP 工具、
操作知识库、执行编译和查询。

### 4. Obsidian (可视化知识库)
Markdown 笔记管理工具，提供双向链接和图谱视图，
让知识可视化。

### 5. Claudian (会话管理)
管理 AI 会话上下文和历史记录，保持会话连续性。

### 6. 知识库 (Vault)
按 Karpathy 三层架构组织的结构化知识存储：
- **index/** - 索引层：主题导航和目录
- **wiki/** - 知识层：深度结构化知识
- **raw/** - 素材层：原始材料暂存

## 快速开始

### 从零到完整部署

```powershell
# 1. 克隆仓库
git clone <仓库URL> D:\<你的路径>\knowledge-base-workflow
cd knowledge-base-workflow

# 2. 一键部署
.\deploy\deploy-all.ps1

# 3. 编辑配置
#    编辑 config/claude-settings.json，替换占位符为实际路径
#    编辑 .mcp.json，确认 MCP 服务路径正确

# 4. 启动 Obsidian
#    打开 Obsidian，选择知识库目录

# 5. 在 VSCode 中打开项目根目录
#    按 Ctrl+Shift+P，选择 "Claude: 启动"

# 6. 开始使用
#    提问或导入素材
```

### 手动部署（分步）

```powershell
# 安装工具链
.\deploy\01-install-tools.ps1

# 部署 MCP 服务端
.\deploy\02-setup-mcp-servers.ps1

# 配置 Claude Code
.\deploy\03-configure-claude.ps1

# 安装语音识别
.\deploy\04-install-whisper.ps1
```

### 前提条件

- Windows 10/11
- Python 3.10+（建议 3.11）
- Node.js 18+（VSCode 和 Claude 扩展需要）
- NVIDIA GPU 4GB+ VRAM（可选，用于 GPU 加速语音识别）
- 网络连接（B站 API 和模型下载需要）

## 目录说明

```
knowledge-base-workflow/
|
|-- README.md                  # 项目总览（本文件）
|-- .gitignore                 # Git 忽略规则
|
|-- deploy/                    # 部署脚本
|   |-- 01-install-tools.ps1   # 安装工具链
|   |-- 02-setup-mcp-servers.ps1 # 部署 MCP 服务端
|   |-- 03-configure-claude.ps1  # 配置 Claude Code
|   |-- 04-install-whisper.ps1   # 安装语音识别
|   +-- deploy-all.ps1           # 一键部署
|
|-- config/                    # 配置模板
|   |-- claude-settings.json   # Claude Code 全局配置
|   |-- mcp-template.json      # MCP 服务配置模板
|   |-- claude-skills/
|   |   +-- vault-CLAUDE.md    # 知识库操作手册
|   +-- obsidian/              # Obsidian 即装即用配置
|       |-- app.json           # 编辑器设置
|       |-- appearance.json    # 主题设置
|       |-- community-plugins.json  # 启用插件清单
|       |-- core-plugins.json  # 核心插件开关
|       +-- plugins/           # 社区插件文件（含 main.js）
|           |-- obsidian42-brat/   # BRAT 插件
|           +-- realclaudian/      # Claudian 会话管理
|
|-- mcp-servers/               # MCP 服务端代码
|   |-- obsidian-mcp/
|   |   +-- server.py          # Obsidian MCP 服务端
|   +-- bilibili-mcp/
|       |-- bilibili_mcp_server.py # B站 MCP 服务端
|       |-- transcribe_bv.py       # 语音转写
|       +-- text_processor.py      # 文本后处理
|
+-- workflow-docs/             # 工作流文档
    |-- OVERVIEW.md            # 系统总览
    |-- KARPATHY-LLM-WIKI.md   # 方法论详解
    |-- INGEST-FLOW.md         # 素材导入流程
    |-- QUERY-FLOW.md          # 查询与回填流程
    +-- VAULT-SCHEMA.md        # 知识库 Schema
```

## 工作流概览

### 素材导入 (Ingest)

```
B站视频/网页/笔记 -> raw/ -> AI 编译 -> wiki/ 更新
```

### 查询 (Query)

```
用户提问 -> AI 查 index/ -> 深入阅读 wiki/ -> 合成回答
```

### 回填 (Backfill)

```
回答中的有价值内容 -> 保存到 wiki/ 或 outputs/
```

### 维护 (Maintain)

```
检查 orphan notes -> 合并重复 -> 更新索引
```

## 使用场景

### 场景 1：从 B站视频学习

1. 用户提供 B站视频链接
2. AI 通过 `bilibili-mcp` 下载音频并转写为文字
3. AI 去除口语化内容，生成阅读版
4. AI 将整理后的内容保存到 `raw/bilibili/`
5. AI 检查现有 wiki/ 知识，将新概念编译到 wiki/

### 场景 2：查询已有知识

1. 用户提问技术问题
2. AI 在 `index/` 中定位相关主题
3. AI 深入阅读 `wiki/` 中的相关文件
4. AI 综合信息并生成回答
5. 如有新信息产生，AI 回填到知识库

### 场景 3：整理网页笔记

1. 用户分享网页链接
2. AI 获取网页内容并保存为 Markdown
3. AI 提取关键概念
4. AI 创建或更新 wiki/ 文件

## 技术栈

| 组件 | 技术 |
|------|------|
| AI 引擎 | Claude Code (Anthropic SDK) |
| MCP 框架 | FastMCP (Python) |
| 知识库 | Obsidian (Markdown) |
| 语音识别 | faster-whisper (本地 GPU) |
| 视频下载 | yt-dlp |
| 音频处理 | ffmpeg |
| API 代理 | ccswitch |

## 相关文档

- [系统总览](workflow-docs/OVERVIEW.md)
- [Karpathy LLM Wiki 方法论](workflow-docs/KARPATHY-LLM-WIKI.md)
- [素材导入流程](workflow-docs/INGEST-FLOW.md)
- [查询与回填流程](workflow-docs/QUERY-FLOW.md)
- [知识库 Schema](workflow-docs/VAULT-SCHEMA.md)

## 许可证

本项目仅供个人学习使用。