# 从 hero-chat-zh.gif 生成 embed 专用加宽版（左右补透明边撑开 Discord embed 宽度）
# 用法：python tools/make_embed_gif.py
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent / "screenshots"
SRC = ROOT / "hero-chat-zh.gif"
DST = ROOT / "hero-chat-zh-embed.gif"
TARGET_W = 880  # embed 宽度由图片宽度决定，补透明边把 embed 撑回全宽

src = Image.open(SRC)
w, h = src.size
pad = (TARGET_W - w) // 2
frames, durs = [], []
for i in range(src.n_frames):
    src.seek(i)
    durs.append(src.info["duration"])
    f = src.convert("RGBA")
    canvas = Image.new("RGBA", (TARGET_W, h), (0, 0, 0, 0))
    canvas.paste(f, (pad, 0))
    alpha = canvas.getchannel("A")
    p = canvas.convert("RGB").quantize(colors=255, method=Image.FASTOCTREE)
    mask = alpha.point(lambda a: 255 if a < 128 else 0)
    p.paste(255, mask)
    p.info["transparency"] = 255
    frames.append(p)

frames[0].save(DST, save_all=True, append_images=frames[1:], duration=durs,
               loop=0, disposal=2, transparency=255, optimize=False)
print(f"{DST.name}: {src.n_frames} frames, {DST.stat().st_size/1024:.0f} KB, {TARGET_W}x{h}")
