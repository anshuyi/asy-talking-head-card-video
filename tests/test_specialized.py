"""Behavior checks for the dedicated card pipeline, without media dependencies."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pipeline = load('specialized_pipeline', ROOT / 'scripts/pipeline.py')
renderer = pipeline.renderer()


class Specialized(unittest.TestCase):
    def test_pipeline_rejects_generic_render_inputs(self):
        for option in ('--page', '--size', '--fps', '--audio', '--start', '--subframes', '--still'):
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/pipeline.py'),
                                     'render', '--project', '.', '--name', 'unused.mp4', option, 'value'],
                                    capture_output=True)
            self.assertEqual(result.returncode, 2, option)
            self.assertIn(b'unrecognized arguments', result.stderr)

    def test_internal_module_is_not_a_render_command(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/card_renderer.py'), 'arbitrary.html'],
                                capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_build_regenerates_builtin_template_and_escapes_content(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            data = json.loads((ROOT / 'examples/timeline.json').read_text(encoding='utf-8'))
            data['header'] = '</script>'
            pipeline.save(project / 'timeline.json', data)
            (project / 'font.otf').write_bytes(b'font fixture; build only')
            (project / 'index.html').write_text('unrelated-custom-page', encoding='utf-8')
            with patch.object(pipeline, 'source', return_value=({'duration': 8, 'width': 720, 'height': 1280}, None)):
                pipeline.build(project, {'font_file': str(project / 'font.otf')})
            html = (project / 'index.html').read_text(encoding='utf-8')
            self.assertNotIn('unrelated-custom-page', html)
            self.assertIn('width="1080" height="1440"', html)
            self.assertIn('\\u003c/script>', html)

    def _render(self, *, fail_page=False, fail_encoder=False):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / 'tmp').mkdir()
            (project / 'qa').mkdir()
            target = project / 'tmp/graphics.mp4'
            target.write_bytes(b'previous-good-layer')
            page = Mock()
            page.screenshot.return_value = b'png-frame'
            if fail_page:
                page.screenshot.side_effect = RuntimeError('page failure')
            @contextlib.contextmanager
            def fake_page(_):
                yield page
            process = Mock()
            process.stdin = io.BytesIO()
            process.poll.return_value = None
            process.wait.return_value = 1 if fail_encoder else 0
            def start(command, **kwargs):
                Path(command[-1]).write_bytes(b'new-layer')
                return process
            with patch.object(renderer, 'card_page', fake_page), patch.object(renderer.subprocess, 'Popen', side_effect=start) as spawn:
                if fail_page or fail_encoder:
                    with self.assertRaises(RuntimeError):
                        renderer.render_cards(project, .1, 'configured-ffmpeg')
                    self.assertEqual(target.read_bytes(), b'previous-good-layer')
                    if fail_page:
                        process.terminate.assert_called_once()
                else:
                    renderer.render_cards(project, .1, 'configured-ffmpeg')
                    self.assertEqual(target.read_bytes(), b'new-layer')
                    self.assertEqual(page.screenshot.call_count, 3)
                    self.assertEqual([call.args[1] for call in page.evaluate.call_args_list], [0, 1/30, 2/30])
                    command = spawn.call_args.args[0]
                    self.assertEqual(command[0], 'configured-ffmpeg')
                    self.assertEqual(command[command.index('-framerate') + 1], '30')
                    self.assertIn('-an', command)
                    self.assertNotIn('-ss', command)
                self.assertFalse((project / 'tmp/graphics.partial.mp4').exists())

    def test_fixed_full_length_silent_layer(self):
        self._render()

    def test_page_failure_keeps_previous_layer(self):
        self._render(fail_page=True)

    def test_encoder_failure_keeps_previous_layer(self):
        self._render(fail_encoder=True)

    def test_bad_duration_does_not_start_browser(self):
        with patch.object(renderer, 'card_page') as browser:
            for duration in (0, -1, float('nan'), float('inf')):
                with self.assertRaises(ValueError):
                    renderer.render_cards(Path('.'), duration, 'ffmpeg')
            browser.assert_not_called()


if __name__ == '__main__':
    unittest.main()
