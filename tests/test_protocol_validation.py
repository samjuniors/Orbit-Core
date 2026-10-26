"""Malformed clients must not terminate the stdio server or bypass its schemas."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source/runtime'))
import orbit_mcp


class ProtocolValidationTests(unittest.TestCase):
    def test_desktop_bundle_runtime_matches_source(self):
        import zipfile
        version = (ROOT / 'VERSION').read_text().strip()
        with zipfile.ZipFile(ROOT / f'ORBIT-Claude-Desktop-v{version}.mcpb') as bundle:
            for source in sorted((ROOT / 'source/runtime').glob('*.py')):
                with self.subTest(source=source.name):
                    self.assertEqual(bundle.read('server/' + source.name), source.read_bytes(),
                                     'Run python scripts/build_desktop_extension.py')

    def test_initialize_rejects_invalid_params(self):
        for params in (None, [], 'text', {'protocolVersion': []}):
            with self.subTest(params=params):
                result = orbit_mcp.handle(None, {
                    'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': params})
                self.assertEqual(result['error']['code'], -32602)

    def test_schema_rejects_array_limits_and_item_types(self):
        base = {'project_root': '/tmp/demo', 'project': 'demo',
                'build_id': 'demo', 'preview_id': 'demo'}
        for actions in ([{}] * 21, ['not an object'], 'not an array'):
            with self.subTest(actions=actions), self.assertRaises(ValueError):
                orbit_mcp.validate('orbit_browser_qa', {**base, 'actions': actions})
        orbit_mcp.validate('orbit_browser_qa', {**base, 'actions': []})
        with self.assertRaises(ValueError):
            orbit_mcp.validate('orbit_capability_select', {
                'project_root': '/tmp/demo', 'objective': 'test', 'host_tools': [1]})

    def test_schema_rejects_objects_booleans_and_unknown_properties(self):
        base = {'project_root': '/tmp/demo', 'project': 'demo',
                'expected_revision': 1, 'answers': {},
                'answer_source': 'user_choices', 'user_reference': 'user chose options'}
        for changed in ({'answers': []}, {'expected_revision': True},
                        {'confirm_write': 1}, {'extra': 'unknown'}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                orbit_mcp.validate('orbit_intake_approve', {**base, **changed})
        orbit_mcp.validate('orbit_intake_approve', base)
        with self.assertRaises(ValueError):
            orbit_mcp.validate([], {})

    def test_stdio_survives_malformed_and_oversized_frames(self):
        frames = [
            b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":null}\n',
            b'{"jsonrpc":"2.0","id":2,"method":"initialize","params":[]}\n',
            b'x' * (orbit_mcp.MAX_REQUEST_BYTES * 3) + b'\n',
            b'[' * 2000 + b'0' + b']' * 2000 + b'\n',
            b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n',
            b'{"jsonrpc":"2.0","id":3,"method":"ping"}\n',
            b'{"jsonrpc":"2.0","id":4,"method":"tools/list"}\n',
        ]
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(ROOT / 'source/runtime/orbit_mcp.py')],
                input=b''.join(frames), capture_output=True, timeout=10,
                env={**os.environ, 'ORBIT_LOCAL_DB': str(Path(tmp) / 'memory.sqlite3')})
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(replies), 6)
        self.assertEqual([r['error']['code'] for r in replies[:3]],
                         [-32602, -32602, -32600])
        # JSON decoder depth limits vary across Python builds. Either a rejected
        # parse or a successfully decoded non-object must leave the server alive.
        self.assertIn(replies[3]['error']['code'], (-32600, -32700))
        self.assertEqual(replies[4], {'jsonrpc': '2.0', 'id': 3, 'result': {}})
        self.assertEqual(len(replies[5]['result']['tools']), len(orbit_mcp.TOOLS))

    def test_reader_requests_only_bounded_chunks(self):
        from unittest.mock import patch

        class BoundedInput(io.BytesIO):
            def readline(self, size=-1):
                if size != orbit_mcp.MAX_REQUEST_BYTES + 1:
                    raise AssertionError('Unbounded frame read')
                return super().readline(size)

        from types import SimpleNamespace
        stream = BoundedInput(b'x' * (orbit_mcp.MAX_REQUEST_BYTES * 2) + b'\n'
                              b'{"jsonrpc":"2.0","id":8,"method":"ping"}\n')
        output = io.StringIO()
        with patch('orbit_mcp.db_connect') as connect, \
                patch('orbit_mcp.sys.stdin', SimpleNamespace(buffer=stream)), \
                patch('orbit_mcp.sys.stdout', output):
            orbit_mcp.main()
            connect.return_value.close.assert_called_once()
        replies = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(len(replies), 2)
        self.assertEqual(replies[1]['id'], 8)


if __name__ == '__main__':
    unittest.main()
