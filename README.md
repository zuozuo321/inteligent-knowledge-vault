# 知识库工作流

将原始素材 `raw/` 编译为可追溯的知识 `wiki/`，通过 `index/` 导航，问答和复盘保存在 `outputs/`。笔记为普通 Markdown，可由 Obsidian、Claude Code 或具备文件访问能力的 AI 助手处理。

## Windows 快速开始

需要 Python 3.10+（建议 3.12）和 Git。在 PowerShell 中运行：

```powershell
git clone https://github.com/zuozuo321/inteligent-knowledge-vault.git
cd inteligent-knowledge-vault
.\deploy\deploy-all.ps1 -VaultPath 'D:\my-knowledge-vault' -PythonPath 'python'
```

打开 Obsidian，选择该知识库文件夹，从 `index/home.md` 开始。未指定 `-VaultPath` 时使用代码项目下的 `vault/`；它被 Git 忽略。自己的知识库建议放在代码项目之外。

部署会创建首页、主题导航、素材队列、使用指南、整理记录及三类模板，并生成包含真实路径的项目级 `.mcp.json`。已有笔记、Obsidian 配置和 Claude 全局设置会保留；重复运行不会覆盖它们。修改项目 MCP 配置前会生成备份，其他服务条目保持不变。

### 分步配置

```powershell
.\deploy\02-setup-mcp-servers.ps1 -PythonPath 'C:\path\to\python.exe'
.\deploy\03-configure-claude.ps1 -VaultPath 'D:\my-knowledge-vault'
```

Claude Code 从代码项目目录启动时使用 `.mcp.json`。模型服务与登录沿用你自己的配置。本项目不预置 API 密钥、模型代理地址或账户信息。

社区插件按需安装：向配置脚本传入 `-InstallCommunityPlugins`，然后在 Obsidian 中自行启用。核心知识管理流程不依赖社区插件。

### B 站素材

默认安装元数据/字幕服务所需依赖。视频需要公开可访问且字幕接口可用；登录、风控或无字幕情形会返回错误信息。

无字幕视频需要本地转写时，可使用：

```powershell
.\deploy\deploy-all.ps1 -VaultPath 'D:\my-knowledge-vault' -WithTranscription
```

这会另装 ffmpeg、yt-dlp、faster-whisper 并加载 tiny 模型。模型下载需要网络和磁盘空间；GPU 可选，CPU 可运行。`WHISPER_MODELS_DIR` 可指定转写缓存目录，`HF_ENDPOINT` 可由使用者显式设置。部署不修改全局网络设置或 Git TLS 校验。

## 日常工作流

1. **收集**：保存原文和出处到 raw，登记素材队列。
2. **编译**：将结论、证据、例子和疑问整理到 wiki，回链原文。
3. **索引**：更新 index，连接相关条目。
4. **查询**：先检索 index/wiki，核实时读取 raw，回答注明出处。
5. **回填**：保存有价值的问答到 outputs，补充已有知识。

知识库内的 `AGENTS.md`、`CLAUDE.md` 和模板约束整理行为。不要把个人笔记或密钥提交到公开代码仓库。

## MCP 工具

Obsidian 服务提供 list_notes、read_note、search_notes、create_note、get_tags、get_backlinks、get_vault_stats。读写限制在显式配置的知识库中；拒绝库外路径和隐藏配置目录，创建不会覆盖已有文件。重名笔记必须使用相对路径。编辑已有笔记由客户端文件工具完成。

B 站服务提供字幕获取、音频转写和双版本文本处理。转写返回的片段用于生成阅读版和带时间戳的原始版。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\tests\test-deploy.ps1 -PythonPath .\.venv\Scripts\python.exe
.\.venv\Scripts\python.exe tests\smoke_mcp.py
```

单元测试验证路径限制、重名、覆盖保护、标签、反向链接及 B 站文本管线（网络与识别使用模拟数据）。MCP 烟雾测试启动真实 stdio 服务并调用工具，不下载视频或模型。部署测试在临时目录验证首次安装、重复运行及已有内容保留。符号链接测试在 Windows 不具备创建权限时跳过。

## 目录

- `config/vault/`：可复用知识库种子文件。
- `config/obsidian/`：Obsidian 配置和可选社区插件。
- `deploy/`：安装和配置脚本。
- `mcp-servers/`：Python MCP 服务。
- `tests/`：回归测试与协议测试。
- `workflow-docs/`：知识组织和工作流参考。
