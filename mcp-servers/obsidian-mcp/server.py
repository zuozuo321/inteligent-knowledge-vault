"""Markdown vault MCP tools with explicit, confined filesystem access."""
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("obsidian-mcp")
VAULT_PATH = os.environ.get("VAULT_PATH") or os.environ.get("KNOWLEDGE_VAULT_PATH", "")


def _vault():
    if not VAULT_PATH:
        raise ValueError("Set VAULT_PATH to an existing vault directory.")
    root = Path(VAULT_PATH).resolve()
    if not root.is_dir():
        raise ValueError("VAULT_PATH is not an existing directory.")
    return root


def _path(relative=""):
    root = _vault()
    rel = Path(relative)
    if rel.is_absolute() or rel.drive or any(c in relative for c in (":", "*", "?")):
        raise ValueError("Only relative vault paths are allowed.")
    result = (root / rel).resolve()
    if not result.is_relative_to(root):
        raise ValueError("Path escapes the vault.")
    if any(p.startswith(".") for p in result.relative_to(root).parts):
        raise ValueError("Hidden configuration paths are not accessible.")
    return result


def _notes(folder=""):
    root = _vault()
    base = _path(folder)
    if not base.is_dir():
        raise ValueError(f"Directory not found: {folder}")
    for file in sorted(base.rglob("*.md")):
        resolved = file.resolve()
        if resolved.is_relative_to(root) and not any(p.startswith(".") for p in file.relative_to(root).parts):
            yield file


def _note(name):
    path = _path(name)
    if path.suffix.lower() != ".md":
        path = _path(str(path.relative_to(_vault())) + ".md")
    if path.is_file():
        return path
    if "/" not in name and "\\" not in name:
        matches = [f for f in _notes() if f.name == path.name]
        if len(matches) > 1:
            raise ValueError("Ambiguous note name; specify the relative path.")
        if matches:
            return matches[0]
    raise FileNotFoundError(f"Note not found: {name}")


def _json(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


def _links(content):
    return [m.split("|", 1)[0].split("#", 1)[0].removesuffix(".md")
            for m in re.findall(r"\[\[([^\]]+)\]\]", content)]


@mcp.tool()
def list_notes(folder: str = "") -> str:
    """列出知识库内的 Markdown 笔记，folder 为相对目录。"""
    return _json([{"path": f.relative_to(_vault()).as_posix(), "name": f.stem,
                   "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                   "size": f.stat().st_size} for f in _notes(folder)])


@mcp.tool()
def read_note(note_name: str) -> str:
    """读取笔记；支持相对路径及带或不带 .md 的文件名，重名须指定路径。"""
    return _note(note_name).read_text(encoding="utf-8-sig")


@mcp.tool()
def search_notes(query: str, folder: str = "") -> str:
    """按关键词搜索笔记，返回第一处匹配及上下文。"""
    results = []
    if not query.strip():
        return _json(results)
    for file in _notes(folder):
        try:
            lines = file.read_text(encoding="utf-8-sig").splitlines()
        except (OSError, UnicodeError):
            continue
        for i, line in enumerate(lines):
            if query.casefold() in line.casefold():
                results.append({"path": file.relative_to(_vault()).as_posix(), "name": file.stem,
                                "line": i + 1, "context": "\n".join(lines[max(0, i-2):i+3])})
                break
    return _json(results)


@mcp.tool()
def create_note(name: str, content: str, folder: str = "") -> str:
    """创建 Markdown 笔记，禁止覆盖已有笔记或写入库外。"""
    # Validate both inputs independently so an absolute name cannot discard folder.
    _path(name)
    _path(folder)
    relative = str(Path(folder) / name)
    if not relative.lower().endswith(".md"):
        relative += ".md"
    path = _path(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)
    except FileExistsError:
        return _json({"error": "Note already exists", "path": relative})
    return _json({"success": True, "path": path.relative_to(_vault()).as_posix()})


@mcp.tool()
def get_tags() -> str:
    """统计 YAML tags 及行内标签；每篇笔记同一标签只计一次。"""
    counts = Counter()
    for file in _notes():
        content = file.read_text(encoding="utf-8-sig")
        tags = set()
        match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", content, re.S)
        if match:
            try:
                metadata = yaml.safe_load(match.group(1))
                values = metadata.get("tags", []) if isinstance(metadata, dict) else []
                if isinstance(values, str):
                    values = [values]
                if isinstance(values, list):
                    tags.update(str(t).lstrip("#") for t in values if t)
            except yaml.YAMLError:
                pass
            content = content[match.end():]
        content = re.sub(r"```.*?```|`[^`]*`", "", content, flags=re.S)
        tags.update(re.findall(r"(?<![\w/#])#([^\W\d][\w/-]*)", content))
        counts.update(tags)
    return _json(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _documents():
    docs = {}
    for file in _notes():
        try:
            docs[file.relative_to(_vault()).with_suffix("").as_posix()] = file.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
    return docs


def _targets(target, source, docs):
    if not target:
        return []
    if target in docs:
        return [target]
    relative = (Path(source).parent / target).as_posix()
    if relative in docs:
        return [relative]
    matches = [p for p in docs if Path(p).name == target]
    return matches if len(matches) == 1 else []


@mcp.tool()
def get_backlinks(note_name: str) -> str:
    """查找内部链接，识别相对路径、别名和标题锚点。"""
    key = _note(note_name).relative_to(_vault()).with_suffix("").as_posix()
    docs = _documents()
    return _json([{"source": source + ".md", "name": Path(source).name}
                  for source, text in docs.items() if source != key
                  and any(key in _targets(target, source, docs) for target in _links(text))])


@mcp.tool()
def get_vault_stats() -> str:
    """统计笔记、词数、目录和无入链笔记；每个文件只读取一次。"""
    docs = _documents()
    linked = set()
    folders = Counter()
    for source, content in docs.items():
        folder = str(Path(source).parent).replace("\\", "/")
        folders["/" if folder == "." else folder] += 1
        for target in _links(content):
            linked.update(p for p in _targets(target, source, docs) if p != source)
    return _json({"total_notes": len(docs), "total_words": sum(len(t.split()) for t in docs.values()),
                  "folder_distribution": dict(sorted(folders.items())),
                  "orphan_notes": [p + ".md" for p in docs if "/" in p and p not in linked]})


if __name__ == "__main__":
    _vault()
    mcp.run(transport="stdio")
