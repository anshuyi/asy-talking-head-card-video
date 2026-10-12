"""Internal renderer for the built-in talking-head card template only.

Browser launch and frame-pipe approach adapted from Kianzzz/xilo-opus-video.
Copyright (c) 2026 周行 (Kianzzz). See ../vendor/LICENSE-xilo.
No standalone CLI, external page, soundtrack, segment or format options.
"""
from contextlib import contextmanager
from pathlib import Path
import math
import subprocess
import sys

WIDTH, HEIGHT, FPS = 1080, 1440, 30


def _launch(playwright):
    args = ['--enable-gpu', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader']
    if sys.platform == 'darwin':
        args.append('--use-angle=metal')
    errors = []
    for options in ({}, {'channel': 'chrome'}, {'channel': 'msedge'}):
        try:
            return playwright.chromium.launch(headless=True, args=args, **options)
        except Exception as exc:
            errors.append(str(exc).splitlines()[0])
    raise RuntimeError('没有可用的本地浏览器，请配置Playwright浏览器、Chrome或Edge：' + '; '.join(errors))


@contextmanager
def card_page(project):
    """Open the project page freshly built by pipeline.build, at fixed size."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = _launch(playwright)
        try:
            page = browser.new_page(viewport={'width': WIDTH, 'height': HEIGHT}, device_scale_factor=1)
            page.goto((Path(project) / 'index.html').resolve().as_uri())
            page.wait_for_function('window.ready === true && typeof window.render === "function"', timeout=60000)
            page.evaluate('document.fonts.ready')
            yield page
        finally:
            browser.close()


def render_cards(project, duration, ffmpeg):
    """Render a silent, full-length card layer. Pipeline adds original media."""
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('卡片时长必须是有效正数')
    project = Path(project)
    temporary = project / 'tmp/graphics.partial.mp4'
    target = project / 'tmp/graphics.mp4'
    log_path = project / 'qa/graphics-ffmpeg.log'
    frames = round(FPS * duration)
    command = [str(ffmpeg), '-v', 'error', '-y', '-f', 'image2pipe',
               '-framerate', str(FPS), '-i', '-', '-an', '-c:v', 'libx264',
               '-crf', '18', '-pix_fmt', 'yuv420p', '-r', str(FPS), str(temporary)]
    try:
        with card_page(project) as page, log_path.open('wb') as log:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log)
            try:
                for frame in range(frames):
                    page.evaluate('t => window.render(t)', frame / FPS)
                    process.stdin.write(page.screenshot(type='png'))
                    if (frame + 1) % max(1, frames // 10) == 0:
                        print(f'卡片渲染 {frame + 1}/{frames} 帧', flush=True)
                process.stdin.close()
                if process.wait():
                    raise RuntimeError('卡片编码失败，详情见qa/graphics-ffmpeg.log')
            except BaseException:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                raise
            finally:
                if not process.stdin.closed:
                    try:
                        process.stdin.close()
                    except OSError:
                        pass
        temporary.replace(target)
        return target
    finally:
        if temporary.exists():
            temporary.unlink()


if __name__ == '__main__':
    sys.exit('此模块仅供真人卡片制作流程内部使用。请运行pipeline.py的preview或render命令。')
