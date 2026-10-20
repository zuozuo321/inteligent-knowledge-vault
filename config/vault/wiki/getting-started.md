---
tags: [topic/knowledge-management, status/compiled]
source: "https://github.com/zuozuo321/inteligent-knowledge-vault"
---
# 使用指南

## 目录约定
- `index/`：入口和主题地图。
- `raw/`：原始素材，保留出处，不以摘要覆盖原文。
- `wiki/`：经过整理的概念、方法、问题和证据。
- `outputs/`：问答、分析和复盘记录。
- `templates/`：新建笔记的格式。
- `attachments/`：图片与附件。

## 导入与编译
1. 新建素材笔记，记录来源、采集日期和原文；给出 `status/uncompiled` 标签。
2. 按主题提取可复用知识，区别原文事实、个人观点和 AI 推断。
3. 新知识写入 wiki，已有条目则补充证据，注明 updated 日期。
4. 在条目中回链素材；在主题导航中添加新条目。
5. 将素材状态改为 `status/compiled`，记录编译去向。

## 查询与回填
先读 index，再查 wiki，需要核实时回到 raw。缺少证据时说明不足。
外部补充信息应注明 URL 和访问日期。不要把 AI 推断记为已经验证的事实。
保存有价值的回答到 outputs，必要时补充到 wiki。

## 使用入口
在 Obsidian 中打开本知识库目录；从 [[index/home]] 开始。
在本工作区对 AI 提出整理或查询要求，即可直接处理 Markdown 文件。
Claude Code 的 MCP 设置位于代码项目的 `.mcp.json`，需从代码项目启动客户端。
B 站字幕工具可用；无字幕视频转写需另装可选转写依赖、ffmpeg 和模型。

## 每周维护
检查未处理素材、断链、重名条目和过时结论。合并前核对来源，删除前确认。
