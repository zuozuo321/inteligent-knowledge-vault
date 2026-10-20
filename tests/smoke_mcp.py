"""Exercise real stdio MCP initialization, tool discovery, reads and writes."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
async def main():
    with tempfile.TemporaryDirectory() as temporary:
        params = StdioServerParameters(command=sys.executable,
            args=[str(ROOT/'mcp-servers/obsidian-mcp/server.py')],
            env={**os.environ, 'VAULT_PATH':temporary})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = {t.name for t in (await session.list_tools()).tools}
                assert len(names) == 7, names
                created = await session.call_tool('create_note', {'name':'smoke','folder':'wiki','content':'MCP smoke check'})
                assert not created.isError, created
                readback = await session.call_tool('read_note', {'note_name':'wiki/smoke'})
                assert readback.content[0].text == 'MCP smoke check', readback
                denied = await session.call_tool('read_note', {'note_name':'../outside'})
                assert denied.isError, denied
        params = StdioServerParameters(command=sys.executable,
            args=[str(ROOT/'mcp-servers/bilibili-mcp/bilibili_mcp_server.py')])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = {t.name for t in (await session.list_tools()).tools}
                assert names == {'get_bilibili_subtitle','transcribe_bilibili_video','process_bilibili_video'}, names
    print('PASS: both MCP servers initialized; note write/read and denied traversal verified.')

if __name__ == '__main__': asyncio.run(main())
