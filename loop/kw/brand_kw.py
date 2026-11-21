"""Render original Kinda Wild Films channel art with the episode cast.

    ZK_TEX=/path/to/assets/tex blender -b -t 2 -P brand_kw.py -- profile /tmp/kw-art preview
    ZK_TEX=/path/to/assets/tex blender -b -t 2 -P brand_kw.py -- banner /tmp/kw-art preview
    # Repeat each without "preview" for the final transparent Cycles plate.
    python brand_kw.py compose /tmp/kw-art /path/to/brand preview
    python brand_kw.py compose /tmp/kw-art /path/to/brand

Compositing needs Pillow and NumPy, not Blender. Existing brand art is backed up
once, immediately before the reviewed final replacements are installed.
"""
import math
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
FONT = HERE.parent / "Montserrat-Black.ttf"
STRIP = (1536, 328)
STRIP_POS = (512, 603)
SAFE = (507, 509, 2053, 932)


def compose(source, out, preview):
    import shutil

    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    out.mkdir(parents=True, exist_ok=True)
    tag = "_preview" if preview else ""

    def gradient(width, height, cx, cy, rx, ry, inner, outer):
        y, x = np.ogrid[:height, :width]
        d = np.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)
        d = np.clip(d, 0, 1) ** 1.17
        a = np.asarray(inner, dtype=np.float32)
        b = np.asarray(outer, dtype=np.float32)
        return Image.fromarray(np.uint8(a + d[:, :, None] * (b - a) + .5)).convert("RGBA")

    def plate(name, size):
        im = Image.open(source / f"{name}_plate{tag}.png").convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        pixels = np.array(im)
        rgb = pixels[:, :, :3].astype(np.float32) / 255
        luma = rgb @ (0.2126, 0.7152, 0.0722)
        density = np.clip(.5 + (luma - .5) * 1.11, 0, 1)
        rgb = density[:, :, None] + (rgb - luma[:, :, None]) * 1.25
        pixels[:, :, :3] = np.uint8(np.clip(rgb, 0, 1) * 255 + .5)
        return Image.fromarray(pixels)

    def install(im, name):
        path = out / f"{name}{tag}.png"
        stage = out / f".{name}{tag}.png"
        im.convert("RGB").save(stage, optimize=True)
        if not preview and name == "banner" and stage.stat().st_size >= 6_000_000:
            im.convert("RGB").quantize(colors=256, method=Image.Quantize.FASTOCTREE).convert("RGB").save(stage, optimize=True)
            if stage.stat().st_size >= 6_000_000:
                raise RuntimeError("Banner must be under 6 MB")
        old = out / f"{name}_old.png"
        if not preview and path.exists() and not old.exists():
            shutil.copy2(path, old)
        stage.replace(path)

    profile = gradient(800, 800, 380, 275, 505, 510, (34, 216, 241), (0, 111, 159))
    profile.alpha_composite(plate("profile", (800, 800)))
    install(profile, "profile")

    banner = gradient(2560, 1440, 1280, 645, 1490, 910, (87, 226, 230), (6, 128, 168))
    accent = Image.new("RGBA", banner.size)
    draw = ImageDraw.Draw(accent)
    for offset, opacity in ((0, 37), (28, 20), (56, 10)):
        draw.line([(-120, 1190 + offset), (605, 465 + offset), (1960, 465 + offset),
                   (2690, 1190 + offset)], fill=(212, 255, 231, opacity), width=2)
        draw.line([(-120, 252 - offset), (605, 977 - offset), (1960, 977 - offset),
                   (2690, 252 - offset)], fill=(4, 82, 127, opacity), width=2)
    banner.alpha_composite(accent)

    cast = plate("banner", STRIP)
    alpha = np.asarray(cast.getchannel("A"), dtype=float)
    fade = np.clip((STRIP[1] - 1 - np.arange(STRIP[1])) / 15, 0, 1)
    cast.putalpha(Image.fromarray(np.uint8(alpha * fade[:, None])))
    visible = cast.getchannel("A").getbbox()
    if visible:
        x, y = STRIP_POS
        assert SAFE[0] <= x + visible[0] and x + visible[2] <= SAFE[2]
        assert SAFE[1] <= y + visible[1] and y + visible[3] <= SAFE[3]
    banner.alpha_composite(cast, STRIP_POS)

    draw = ImageDraw.Draw(banner)
    title = ImageFont.truetype(str(FONT), 89)
    tagline = ImageFont.truetype(str(HERE.parent / "Montserrat-ExtraBold.ttf"), 26)
    ink = (4, 30, 51, 255)
    draw.text((1280, 520), "KINDA WILD FILMS", font=title, fill=ink, anchor="mt",
              stroke_width=1, stroke_fill=ink)
    draw.text((1280, 592), "True stories. Wild endings.", font=tagline, fill=ink, anchor="mt")
    for x in (1035, 1491):
        draw.rounded_rectangle((x, 599, x + 34, 604), radius=2, fill=(255, 222, 62, 255))
    install(banner, "banner")


def render(kind, target, preview):
    import bpy
    from mathutils import Vector

    sys.path.insert(0, str(HERE))
    import cast as C
    import person as P
    import sets_kw as K
    import wardrobe_kw as Wd

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    K.set_world(scene, "studio")
    K.finish(scene, 8 if preview else 44)
    scene.use_nodes = False  # keep the transparent plate clean for the 2D compositor
    scene.cycles.caustics_refractive = True
    scene.cycles.max_bounces = 7
    scene.cycles.transparent_max_bounces = 12
    scene.cycles.adaptive_threshold = .11 if preview else .045
    scene.render.film_transparent = True
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"

    ned = P.build_person("Ned", **C.cast({
        "gender": "m", "age": "middle", "race": "caucasian", "build": "avg", "tee": "red",
    }, "sneeze", P.MP))
    K.skin(ned, amount=.41, pores=.13)
    K.flush(ned, .16)

    def face(p, **expressions):
        values = {}
        for key, weight in expressions.items():
            for path, multiplier in P.EXPR[key]:
                values[path] = max(values.get(path, 0), weight * multiplier)
        for path, key in p.keys.items():
            key.value = min(key.slider_max, values.get(path, 0))

    def cheeks(p, level):
        for path in ("cheek/l-cheek-volume-incr", "cheek/r-cheek-volume-incr"):
            p.keys[path].slider_max = max(1.5, level)
            p.keys[path].value = level

    def nose_tip(p):
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        obj = p.body.evaluated_get(dg)
        matrix = obj.matrix_world
        head = p.head_world()
        points = (matrix @ v.co for v in obj.data.vertices)
        return min((v for v in points if abs(v.x - head.x) < .012 and
                    -.02 < v.z - head.z < .12), key=lambda v: v.y)

    def pinch(p):
        # Angles tuned in ep_sneeze; solve the IK position against the live face.
        for j, ix in enumerate((60.4, 9.9, 12), 1):
            p.rot(f"finger2-{j}.R", (ix, 0, 0))
            for f in (3, 4, 5):
                p.rot(f"finger{f}-{j}.R", (76 if j == 1 else 95, 0, 0))
        for j, a in enumerate(((44.5, -10.9, 3.8), (-9.1, 0, 0), (0, 0, 0)), 1):
            p.rot(f"finger1-{j}.R", a)
        p.rot("wrist.R", (11.5, -11.5, -60.3))
        tip = nose_tip(p)
        target = tip + Vector((.0247, -.0295, -.0907))
        desired = tip + Vector((0, .007, .004))
        pole = p.rig.location + Vector((-.55, -.30, p.bone_world("spine03").z - p.rig.location.z - .50))
        for _ in range(9):
            p.reach("R", target, w=1, pole=pole)
            bpy.context.view_layer.update()
            index = p.bone_world("finger2-3.R", tail=True)
            thumb = p.bone_world("finger1-3.R", tail=True)
            target += (desired - index.lerp(thumb, .5)) * .85
        print("pinch / tip gap:", tip[:], round((index - thumb).length, 4), flush=True)
        return tip

    def relaxed(p, side):
        # Neutral weight-bearing stance, not the MPFB A-pose.
        sg = 1 if side == "L" else -1
        shoulder = p.bone_world(f"upperarm01.{side}")
        hip = p.bone_world("spine05")
        p.reach(side, (shoulder.x + sg * .046, shoulder.y - .072, hip.z - .068),
                pole=(shoulder.x + sg * .27, shoulder.y + .21, hip.z + .17))
        p.rot(f"wrist.{side}", (3, 0, sg * 6))
        P.fingers(p, side, .26, thumb=.24)

    def lamp(name, loc, target, watts, size, rgb):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size, data.color = watts, "DISK", size, rgb
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = loc
        obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

    def camera(pos, aim, width):
        data = bpy.data.cameras.new("Brand Camera")
        data.type, data.ortho_scale, data.clip_start = "ORTHO", width, .01
        obj = bpy.data.objects.new("Brand Camera", data)
        scene.collection.objects.link(obj)
        obj.location = pos
        obj.rotation_euler = (Vector(aim) - obj.location).to_track_quat("-Z", "Y").to_euler()
        scene.camera = obj

    if kind == "profile":
        face(ned, puff=1.5, pressed=1.05, bulge=.94, worry=.15)
        cheeks(ned, 1.95)
        ned.rot("head", (-3, 0, 0))
        tip = pinch(ned)
        relaxed(ned, "L")
        aim = tip + Vector((-.006, .025, -.004))
        camera(aim + Vector((.30, -2.5, .017)), aim, .378)
        scene.view_settings.exposure = -.31
        lamp("Warm key", (-.46, -.76, tip.z + .44), tip, 62, .65, (1, .91, .82))
        lamp("Eye fill", (.45, -.93, tip.z + .07), tip, 31, .45, (.80, .96, 1))
        lamp("Amber edge", (.42, .45, tip.z + .34), tip, 72, .50, (1, .77, .40))
        lamp("Cool edge", (-.35, .26, tip.z + .18), tip, 22, .44, (.40, .85, 1))
        side = 300 if preview else 960
        scene.render.resolution_x = scene.render.resolution_y = side
    else:
        police = Wd.person("Tess", "police", "brand-police", gender="f", age="young",
                           race="caucasian", build="avg", hair="short02")
        nurse = Wd.person("Nurse", "nurse", "sneeze-nurse", gender="m", age="young",
                          race="african", build="avg", clipboard=False)
        doctor = Wd.person("Doc", "doctor", "sneeze-doc", gender="f", age="young",
                           race="asian", build="slim", hair="ponytail01", gloves=False)
        medic = Wd.person("Ravi", "paramedic", "brand-medic", gender="m", age="young",
                          race="mixed", build="slim", hair="short02")
        fire = Wd.person("Marco", "firefighter", "brand-fire", gender="m", age="middle",
                         race="caucasian", build="avg", hair="short03")
        placements = [
            (police, -1.268, .24, .005, 8, (-8, 2, -3)),
            (nurse, -.760, .06, -.005, 5, (-2, -2, 0)),
            (ned, -.230, -.13, .042, 0, (-3, 0, 0)),
            (doctor, .273, .02, .044, -5, (-4, 3, 2)),
            (medic, .755, .22, .020, -5, (-2, -3, 2)),
            (fire, 1.265, .05, .012, -7, (-7, 2, 0)),
        ]
        for p, x, y, lift, turn, head in placements:
            if p is not ned:
                K.skin(p, amount=.115, pores=.09)
                face(p, smile=.18 if p is police else .27)
            else:
                face(p, puff=1.35, pressed=1.0, bulge=.63)
                cheeks(p, 1.75)
            bpy.context.view_layer.update()
            z = 1.54 + lift - p.head_world().z
            p.place((x, y, z), rz=turn)
            p.rot("head", head)
            bpy.context.view_layer.update()
            relaxed(p, "L")
            if p is ned:
                pinch(p)
            else:
                relaxed(p, "R")
        aim = (0, 0, 1.452)
        camera((0, -7, 1.465), aim, 3.27)
        scene.view_settings.exposure = -.72
        lamp("Long warm key", (-1.1, -2.05, 2.8), aim, 385, 2.35, (1, .91, .82))
        lamp("Eye fill", (1.23, -2.05, 1.46), aim, 152, 1.56, (.82, .97, 1))
        lamp("Warm cast edge", (1.0, .75, 2.53), aim, 243, 1.48, (1, .81, .49))
        lamp("Cyan cast edge", (-1.35, .68, 2.47), aim, 130, 1.42, (.41, .90, 1))
        scene.render.resolution_x, scene.render.resolution_y = (768, 164) if preview else STRIP

    target.mkdir(parents=True, exist_ok=True)
    tag = "_preview" if preview else ""
    scene.render.filepath = str(target / f"{kind}_plate{tag}.png")
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "compose":
        compose(Path(sys.argv[2]), Path(sys.argv[3]), "preview" in sys.argv[4:])
    else:
        args = sys.argv[sys.argv.index("--") + 1:]
        if len(args) not in (2, 3) or args[0] not in {"profile", "banner"}:
            raise SystemExit(__doc__)
        render(args[0], Path(args[1]), "preview" in args[2:])
