#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站视频语音转文字工具 — 独立脚本
==============================================
用法: python transcribe_bv.py <BV号或URL> [--model medium] [--output srt|txt|md]

原理:
  1. yt-dlp 提取视频音频流（不下载视频，仅音频）
  2. faster-whisper 本地 GPU 语音识别
  3. 输出带时间戳的字幕文本

依赖: faster-whisper, yt-dlp, nvidia-cublas-cu12, nvidia-cudnn-cu12
模型: tiny(75M) / base(145M) / small(488M) / medium(1.5G) / large-v3(3G)
      推荐 medium — 中文效果好，4GB VRAM 可运行
"""

import sys
import os
# Respect an explicitly configured HF_ENDPOINT; use the official default otherwise.
import json
import subprocess
import tempfile
import hashlib
import argparse
import logging
import shutil
from pathlib import Path
from datetime import timedelta

from text_processor import process_transcript, format_markdown, clean_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# 确保 CUDA DLL 在 PATH 中（nvidia pip 包需要手动添加到 PATH）
_cuda_dll_paths = [
    str(Path(sys.prefix) / "Lib" / "site-packages" / "nvidia" / "cublas" / "bin"),
    str(Path(sys.prefix) / "Lib" / "site-packages" / "nvidia" / "cudnn" / "bin"),
    str(Path(sys.prefix) / "Lib" / "site-packages" / "nvidia" / "cuda_nvrtc" / "bin"),
]
for _p in _cuda_dll_paths:
    if Path(_p).exists() and _p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _p + os.pathsep + os.environ.get("PATH", "")

# --- 配置 ---
MODELS_DIR = Path(os.environ.get("WHISPER_MODELS_DIR", str(Path.home() / ".cache" / "whisper_models")))
YT_DLP_PATH = None  # 自动查找


def find_yt_dlp() -> str:
    """查找 yt-dlp 可执行文件路径。"""
    global YT_DLP_PATH
    if YT_DLP_PATH:
        return YT_DLP_PATH

    # 1. 直接命令
    if shutil.which("yt-dlp"):
        YT_DLP_PATH = "yt-dlp"
        return YT_DLP_PATH

    # User-local tools directory
    tool_path = Path.home() / ".local" / "bin" / "yt-dlp.exe"
    if tool_path.exists():
        YT_DLP_PATH = str(tool_path)
        return YT_DLP_PATH

    # 2. 常见 winget 路径
    candidates = list(Path.home().glob(
        "AppData/Local/Microsoft/WinGet/Packages/yt-dlp.yt-dlp_*/yt-dlp.exe"
    ))
    if candidates:
        YT_DLP_PATH = str(candidates[0])
        return YT_DLP_PATH

    # 3. pip 安装路径
    for scripts_dir in [
        Path(sys.executable).parent,
        Path(sys.executable).parent / "Scripts",
    ]:
        yt_dlp_exe = scripts_dir / "yt-dlp.exe"
        if yt_dlp_exe.exists():
            YT_DLP_PATH = str(yt_dlp_exe)
            return YT_DLP_PATH

    raise FileNotFoundError(
        "找不到 yt-dlp。请安装: winget install yt-dlp.yt-dlp\n"
        "或: pip install yt-dlp"
    )


def parse_video_id(video_input: str) -> tuple:
    """解析视频输入，返回 (url, bvid, title_placeholder)。"""
    video_input = video_input.strip()
    if video_input.startswith("http"):
        return video_input, "", ""
    if video_input.startswith("BV"):
        return f"https://www.bilibili.com/video/{video_input}", video_input, ""
    # Plain number without prefix
    return f"https://www.bilibili.com/video/BV{video_input}", f"BV{video_input}", ""


def extract_audio(video_url: str, output_dir: Path) -> tuple[Path, str]:
    """
    用 yt-dlp 提取视频音频。
    返回: (音频文件路径, 视频标题)
    """
    yt_dlp = find_yt_dlp()
    log.info(f"yt-dlp: {yt_dlp}")

    # 先获取视频标题
    cmd_info = [yt_dlp, "--cookies-from-browser", "chrome", "--print", "%(title)s", "--no-playlist", video_url]
    result = subprocess.run(cmd_info, capture_output=True, text=True, timeout=30)
    title = result.stdout.strip().split("\n")[-1] or "unknown"
    # 清理文件名非法字符
    safe_title = "".join(c for c in title if c not in r'<>:"/\|?*')[:80]
    log.info(f"视频标题: {safe_title}")

    # 下载音频（仅音频流，不下载视频）
    audio_path = output_dir / f"{safe_title}.wav"
    cmd_dl = [
        yt_dlp,
        "--cookies-from-browser", "chrome",  # B站 需要登录 Cookie
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "--extract-audio",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "-o", str(audio_path.with_suffix("")) + ".%(ext)s",
        "--no-playlist",
        "--no-continue",
        video_url,
    ]
    log.info(f"正在下载音频...")
    subprocess.run(cmd_dl, check=True, timeout=300)

    # 查找生成的 wav 文件
    wav_files = list(output_dir.glob("*.wav"))
    if not wav_files:
        raise FileNotFoundError(f"音频下载失败，未找到 .wav 文件于 {output_dir}")

    audio_file = wav_files[0]
    log.info(f"音频文件: {audio_file} ({audio_file.stat().st_size / 1024 / 1024:.1f} MB)")
    return audio_file, safe_title


def transcribe_audio(audio_path: Path, model_size: str = "medium", language: str = "zh") -> list[dict]:
    """
    用 faster-whisper 转写音频。
    返回: [{"start": float, "end": float, "text": str}, ...]
    """
    from faster_whisper import WhisperModel

    log.info(f"加载 Whisper 模型: {model_size} (语言: {language})")
    log.info(f"模型缓存目录: {MODELS_DIR}")

    # 检测 GPU（优先 CUDA，不可用则 CPU）
    device = "cuda"
    compute_type = "float16"
    try:
        import torch
        if not torch.cuda.is_available():
            device = "cpu"
            compute_type = "int8"
    except ImportError:
        pass  # faster-whisper 自带 CUDA 检测，先试 GPU

    log.info(f"设备: {device}, 计算类型: {compute_type}")

    try:
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=str(MODELS_DIR),
            num_workers=2,
        )
    except Exception as e:
        log.warning(f"GPU 初始化失败 ({e})，回退到 CPU")
        device = "cpu"
        compute_type = "int8"
        model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
            download_root=str(MODELS_DIR),
            num_workers=2,
        )

    log.info(f"开始转写: {audio_path.name}")
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        vad_filter=True,           # 过滤静音
        vad_parameters=dict(
            min_silence_duration_ms=500,
            threshold=0.5,
        ),
        temperature=0.0,            # 确定性输出
        repetition_penalty=1.1,
    )

    log.info(f"检测到语言: {info.language} (概率: {info.language_probability:.2%})")

    results = []
    for seg in segments:
        results.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })
        if len(results) % 20 == 0:
            log.info(f"  已转写 {len(results)} 段...")

    log.info(f"转写完成，共 {len(results)} 段")
    return results


def transcribe_video(video_input: str, model_size: str = "medium", language: str = "zh", text_mode: str = "raw") -> dict:
    """
    程序化接口：视频URL/BV号 -> 下载音频 -> 语音识别 -> 返回结构化结果。

    返回 dict:
        {
            "title": str,
            "bvid": str,
            "duration": float,
            "segments": [{"start": float, "end": float, "text": str}, ...],
            "full_text": str,
            "clean_text": str (if text_mode="reading"),
        }
    """
    video_url, bvid, _ = parse_video_id(video_input)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Step 1: Extract audio
        log.info("提取视频音频...")
        audio_path, title = extract_audio(video_url, tmp_path)

        # Step 2: Transcribe
        log.info(f"语音识别 (模型: {model_size})...")
        segments = transcribe_audio(audio_path, model_size, language)

        if not segments:
            return {"error": "转写结果为空"}

        # Build result
        full_text = "\n".join([s["text"] for s in segments])
        duration = segments[-1]["end"]

        result = {
            "title": title,
            "bvid": bvid or "auto",
            "duration": round(duration, 1),
            "segments": segments,
            "full_text": full_text,
            "num_segments": len(segments),
        }

        # Optional cleaning
        if text_mode == "reading":
            from text_processor import clean_text as ct
            cleaned = ct(full_text, level="reading")
            result["clean_text"] = cleaned

        return result


def format_time(seconds: float) -> str:
    """秒数 -> HH:MM:SS,mmm"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((td.total_seconds() - total_seconds) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def format_srt(segments: list[dict]) -> str:
    """转为 SRT 字幕格式。"""
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{format_time(seg['start'])} --> {format_time(seg['end'])}")
        lines.append(seg['text'])
        lines.append("")  # 空行
    return "\n".join(lines)


def format_txt(segments: list[dict]) -> str:
    """转为纯文本（带时间戳）。"""
    lines = []
    for seg in segments:
        ts = f"[{format_time(seg['start'])[:8]} -> {format_time(seg['end'])[:8]}]"
        lines.append(f"{ts} {seg['text']}")
    return "\n".join(lines)


def format_md(segments: list[dict], title: str, video_url: str) -> str:
    """转为 Markdown（适合 Obsidian）。"""
    lines = [
        f"---",
        f"tags: [视频转录]",
        f"created: {__import__('datetime').date.today().isoformat()}",
        f"source: {video_url}",
        f"---",
        f"",
        f"# {title}",
        f"",
        f"> [!abstract] 语音识别转录",
        f"> 本内容由 faster-whisper 从视频音频自动转写，共 {len(segments)} 段。",
        f"> 来源: [{video_url}]({video_url})",
        f"",
    ]
    # 合并连续短句成段落
    current_text = []
    current_start = None
    current_end = None

    for seg in segments:
        text = seg['text']
        if current_start is None:
            current_start = seg['start']
        current_end = seg['end']
        current_text.append(text)

        # 如果句子结束（以句号、问号、感叹号等结尾），则形成段落
        if text.rstrip().endswith(('。', '？', '！', '.', '?', '!', '"', '"', '」')):
            paragraph = ''.join(current_text)
            ts = f"[{format_time(current_start)[:8]} -> {format_time(current_end)[:8]}]"
            lines.append(f"{ts}  \n{paragraph}\n")
            current_text = []
            current_start = None

    # 剩余未结束的句子
    if current_text:
        paragraph = ''.join(current_text)
        ts = f"[{format_time(current_start)[:8]} -> {format_time(current_end)[:8]}]"
        lines.append(f"{ts}  \n{paragraph}\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="B站视频语音转文字 — 本地 GPU 识别",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python transcribe_bv.py BV1xx4y1a7Bx
  python transcribe_bv.py https://www.bilibili.com/video/BV1xx4y1a7Bx
  python transcribe_bv.py BV1xx4y1a7Bx --model large-v3 --output srt
  python transcribe_bv.py BV1xx4y1a7Bx --output md --save-to ./subtitles/
        """,
    )
    parser.add_argument("video", help="B站视频 BV 号或完整 URL")
    parser.add_argument("--model", default="medium",
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper 模型大小 (默认: medium)")
    parser.add_argument("--output", default="txt",
                        choices=["txt", "srt", "md"],
                        help="输出格式 (默认: txt)")
    parser.add_argument("--save-to", default=None,
                        help="输出目录 (默认: 当前目录)")
    parser.add_argument("--keep-audio", action="store_true",
                        help="保留下载的音频文件")
    parser.add_argument("--language", default="zh",
                        help="语言代码 (默认: zh)")
    parser.add_argument("--clean", action="store_true",
                        help="去除口语填充词，输出清洁阅读版文本")
    parser.add_argument("--dual", action="store_true",
                        help="同时输出原始版和阅读版两份文件")
    args = parser.parse_args()

    result = transcribe_video(
        video_input=args.video,
        model_size=args.model,
        language=args.language,
        text_mode="reading" if args.clean else "raw"
    )

    if "error" in result:
        log.error(result["error"])
        sys.exit(1)

    output_dir = Path(args.save_to) if args.save_to else Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(c for c in result["title"] if c not in r'<>:"/\|?*')[:60]

    if args.clean or args.dual:
        proc_result = process_transcript(result["segments"], level="both")
        stats = proc_result['stats']
        log.info(f"文本清洁: {stats['original_chars']}字 -> {stats['clean_chars']}字 (精简 {stats['reduction_pct']}%)")

        if args.dual:
            raw_file = output_dir / f"{safe_title}_raw.txt"
            raw_file.write_text(proc_result['raw_text'], encoding="utf-8")
            log.info(f"   原始版: {raw_file}")

            clean_file = output_dir / f"{safe_title}_clean.md"
            md_content = format_markdown(proc_result, result["title"], args.video, include_raw=True)
            clean_file.write_text(md_content, encoding="utf-8")
            log.info(f"   阅读版: {clean_file}")
        else:
            md_output = format_markdown(proc_result, result["title"], args.video, include_raw=False)
            output_file = output_dir / f"{safe_title}_clean.md"
            output_file.write_text(md_output, encoding="utf-8")
            log.info(f"   阅读版: {output_file}")
    else:
        if args.output == "srt":
            output_content = format_srt(result["segments"])
            ext = ".srt"
        elif args.output == "md":
            output_content = format_md(result["segments"], result["title"], args.video)
            ext = ".md"
        else:
            output_content = format_txt(result["segments"])
            ext = ".txt"

        output_file = output_dir / f"{safe_title}_transcript{ext}"
        output_file.write_text(output_content, encoding="utf-8")

    total_duration = result["duration"]
    log.info(f"   总时长: {total_duration:.0f}s ({total_duration/60:.1f}min)")
    log.info(f"   总段数: {result['num_segments']}")
    log.info(f"   总字数: {sum(len(s['text']) for s in result['segments'])}")

    if args.keep_audio:
        audio_dest = output_dir / f"{safe_title}.wav"
        shutil.copy2(result.get("_audio_path", ""), audio_dest) if result.get("_audio_path") else None


if __name__ == "__main__":
    main()