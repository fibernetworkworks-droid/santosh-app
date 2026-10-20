"""Render the 100 female looks to app images (assets/avatars/fNNN.webp + fNNN_head.webp).

    python3 tool/avatars/gen_looks.py      # only when the catalogue changes
    python3 tool/avatars/render.py         # needs: pip install playwright pillow  (Chromium with SwiftShader is enough)

Uses the same builder as the live 3D avatar (assets/santosh3d/avatar.js), so pictures and 3D always match.
"""
import asyncio, base64, io, json, os
from playwright.async_api import async_playwright
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, 'assets', 'avatars')


async def main():
    looks = json.load(open(os.path.join(HERE, 'looks_full.json'), encoding='utf-8'))
    os.makedirs(OUT, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'])
        pg = await b.new_page()
        await pg.goto('file://' + os.path.join(HERE, 'render.html'))
        await pg.wait_for_function('window.ready', timeout=60000)
        for i, lk in enumerate(looks):
            full = await pg.evaluate('([l]) => renderLook(l, 480, 740, "figure", "idle", 0)', [lk])
            head = await pg.evaluate('([l]) => renderLook(l, 256, 256, "head", "idle", 0)', [lk])
            im = Image.open(io.BytesIO(base64.b64decode(full.split(',')[1]))).convert('RGBA')
            im = im.crop(im.getbbox()); im.thumbnail((300, 460), Image.LANCZOS)
            im.save(os.path.join(OUT, lk['id'] + '.webp'), 'WEBP', quality=82, method=6)
            h = Image.open(io.BytesIO(base64.b64decode(head.split(',')[1]))).convert('RGBA').resize((192, 192), Image.LANCZOS)
            h.save(os.path.join(OUT, lk['id'] + '_head.webp'), 'WEBP', quality=84, method=6)
            print(i + 1, lk['id'], lk['name'], lk['city'], flush=True)
        await b.close()
    slim = json.load(open(os.path.join(ROOT, 'server', 'app', 'avatar', 'looks.json'), encoding='utf-8'))
    json.dump(slim, open(os.path.join(OUT, 'looks.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

asyncio.run(main())
