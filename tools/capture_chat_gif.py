# 抓取主页 hero 对话卡片，导出三语透明底 GIF
# 用法：python tools/capture_chat_gif.py  （需 http://localhost:8800 在跑）
import time, io
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

URL = "http://localhost:8800"
OUT = Path(__file__).resolve().parent.parent / "gif-export"
LOOP_MS = 6900          # 动画一个完整周期
TARGET_FPS = 10
LANGS = ["zh", "en", "ja"]

def quantize_frame(img: Image.Image) -> Image.Image:
    """RGBA -> 带 1bit 透明的调色板帧"""
    alpha = img.getchannel("A")
    p = img.convert("RGB").quantize(colors=255, method=Image.FASTOCTREE)
    mask = alpha.point(lambda a: 255 if a < 128 else 0)
    p.paste(255, mask)  # 索引 255 = 透明
    p.info["transparency"] = 255
    return p

def capture_lang(page, lang: str):
    page.goto(URL, wait_until="networkidle")
    page.add_style_tag(content="""
      html, body, .hero, .hero-inner, .hero-right { background: transparent !important; }
      .hero-chat { box-shadow: none !important; }
      .chat-caret { animation-duration: 1.15s !important; } /* 6 闪 / 6.9s，循环无缝 */
    """)
    page.evaluate("document.fonts.ready")
    page.evaluate(f"applyLang('{lang}')")
    card = page.locator(".hero-chat")

    # 锚定循环起点：等妈妈消息出现，再等它被 reset（= 新周期 t0）
    page.wait_for_function("document.getElementById('chat-msg-mom').classList.contains('show')", timeout=15000)
    page.wait_for_function("!document.getElementById('chat-msg-mom').classList.contains('show')", timeout=15000)
    # t0：重置光标闪烁相位，保证首尾衔接
    page.evaluate("""(() => {
      const c = document.getElementById('chat-caret');
      c.style.animation = 'none'; void c.offsetWidth;
      c.style.animation = 'caret-blink 1.15s steps(1) infinite';
    })()""")
    t0 = time.perf_counter()

    frames, stamps = [], []
    interval = 1.0 / TARGET_FPS
    next_t = 0.0
    while True:
        now = (time.perf_counter() - t0) * 1000
        if now >= LOOP_MS:
            break
        png = card.screenshot(omit_background=True)
        stamps.append((time.perf_counter() - t0) * 1000)
        frames.append(Image.open(io.BytesIO(png)).convert("RGBA"))
        next_t += interval
        sleep = t0 + next_t - time.perf_counter()
        if sleep > 0:
            time.sleep(sleep)

    durations = [max(20, int(stamps[i + 1] - stamps[i])) for i in range(len(stamps) - 1)]
    durations.append(max(20, int(LOOP_MS - stamps[-1])))

    pal = [quantize_frame(f) for f in frames]
    out = OUT / f"hero-chat-{lang}.gif"
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durations,
                loop=0, disposal=2, transparency=255, optimize=False)
    print(f"{out.name}: {len(frames)} frames, {out.stat().st_size/1024:.0f} KB, size {frames[0].size}")

def main():
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
        for lang in LANGS:
            capture_lang(page, lang)
        browser.close()

if __name__ == "__main__":
    main()
