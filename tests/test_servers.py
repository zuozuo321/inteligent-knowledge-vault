import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
vault = load('vault_server', 'mcp-servers/obsidian-mcp/server.py')
sys.path.insert(0, str(ROOT / 'mcp-servers/bilibili-mcp'))
bili = load('bili_server', 'mcp-servers/bilibili-mcp/bilibili_mcp_server.py')

class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'vault'
        self.root.mkdir()
        vault.VAULT_PATH = str(self.root)
    def tearDown(self):
        self.temp.cleanup()
    def test_missing_config_fails_closed(self):
        vault.VAULT_PATH = ''
        with self.assertRaises(ValueError): vault.list_notes()
    def test_missing_vault(self):
        vault.VAULT_PATH = str(self.root / 'missing')
        with self.assertRaises(ValueError): vault.list_notes()
    def test_create_read_search_and_no_overwrite(self):
        result = json.loads(vault.create_note('test.md', '中文 Evidence', 'wiki'))
        self.assertTrue(result['success'])
        self.assertEqual(vault.read_note('wiki/test'), '中文 Evidence')
        self.assertEqual(vault.read_note('test.md'), '中文 Evidence')
        self.assertIn('error', json.loads(vault.create_note('test', 'overwrite', 'wiki')))
        self.assertEqual(len(json.loads(vault.search_notes('evidence'))), 1)
        self.assertFalse((self.root/'wiki/test.md.md').exists())
    def test_traversal_absolute_hidden_and_ads(self):
        for path in ['../outside', str(self.root.parent/'outside'), '.obsidian/config', 'wiki/test:secret', '*.md']:
            for call in [lambda: vault.read_note(path), lambda: vault.create_note(path, 'x'), lambda: vault.list_notes(path), lambda: vault.search_notes('x', path)]:
                with self.subTest(path=path), self.assertRaises(ValueError): call()
        with self.assertRaises(ValueError): vault.create_note('test', 'x', '../outside')
    def test_symlink_escape(self):
        outside = self.root.parent/'outside.md'
        outside.write_text('secret')
        try: (self.root/'link.md').symlink_to(outside)
        except OSError: self.skipTest('OS does not allow symlinks for this user')
        self.assertEqual(json.loads(vault.list_notes()), [])
        with self.assertRaises(ValueError): vault.read_note('link')
    def test_ambiguous_name(self):
        vault.create_note('same', 'a', 'a')
        vault.create_note('same', 'b', 'b')
        with self.assertRaises(ValueError): vault.read_note('same')
        self.assertEqual(vault.read_note('a/same'), 'a')
    def test_tags_exclude_body_bullets_and_other_yaml(self):
        vault.create_note('tags', '---\ntags:\n  - topic/test\naliases:\n  - not-a-tag\n---\n- not-a-tag-either\n#topic/test #中文标签\n```\n#code\n```')
        self.assertEqual(dict(json.loads(vault.get_tags())), {'topic/test':1, '中文标签':1})
    def test_backlinks_and_orphans_with_paths_aliases_and_headings(self):
        vault.create_note('target', 'content', 'wiki')
        vault.create_note('home', '[[wiki/target#Heading|Alias]]', 'index')
        vault.create_note('orphan', '[[orphan]]', 'wiki')
        self.assertEqual(json.loads(vault.get_backlinks('wiki/target'))[0]['source'], 'index/home.md')
        stats=json.loads(vault.get_vault_stats())
        self.assertEqual(stats['total_notes'],3)
        self.assertNotIn('wiki/target.md',stats['orphan_notes'])
        self.assertIn('wiki/orphan.md',stats['orphan_notes'])

class BilibiliTests(unittest.TestCase):
    def test_pipeline_uses_segments_and_preserves_timestamps(self):
        sample={'title':'测试', 'duration':3, 'bvid':'BVtest', 'full_text':'文本', 'segments':[{'start':0,'end':3,'text':'文本'}]}
        with patch('transcribe_bv.transcribe_video',return_value=sample):
            full=json.loads(bili.process_bilibili_video('BVtest'))
            clean=json.loads(bili.process_bilibili_video('BVtest',mode='clean'))
        self.assertTrue(full['success'])
        self.assertIn('文本', full['reading_version'])
        self.assertIn('00:00', full['original_transcript'])
        self.assertNotIn('original_transcript',clean)
    def test_pipeline_propagates_transcription_error(self):
        with patch('transcribe_bv.transcribe_video',return_value={'error':'download failed'}):
            self.assertEqual(json.loads(bili.process_bilibili_video('BVtest')),{'error':'download failed'})
    def test_chinese_subtitle_uses_lan(self):
        responses=[{'code':0,'data':{'aid':1,'cid':2,'title':'t'}},
                   {'data':{'subtitle':{'subtitles':[{'lan':'en','subtitle_url':'https://example.com/en'}, {'lan':'zh-CN','subtitle_url':'https://example.com/zh'}]}}},
                   {'body':[{'content':'中文','to':2}]}]
        from unittest.mock import Mock
        with patch.object(bili.httpx,'get',side_effect=[Mock(json=Mock(return_value=r)) for r in responses]) as get:
            result=json.loads(bili.get_bilibili_subtitle('BVtest'))
            self.assertEqual(get.call_args.args[0],'https://example.com/zh')
            self.assertEqual(result['subtitle'],'中文')

if __name__=='__main__': unittest.main()
