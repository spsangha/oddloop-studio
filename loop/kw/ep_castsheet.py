"""Kinda Wild Films - CAST MASTER sheet (kit/cast_master.md section 4).  NEVER published: the permanent test of every
roster character, re-run after any change to a cast file or to the code that drives people.  Written only with kwkit.

    KW_NOCHECK=1 KW_HEADS=humgen blender -b -P ep_castsheet.py -- <outdir> 0 1      (ONLY=<frames> from --tiles)
    python3 ep_castsheet.py --tiles                                                  tile -> frame map (json)

One 0.75 s shot per tile; the still is the middle frame of the shot.  Tiles T1-T24 for each character (Ben, Howard).
"""
import sys, os, json; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW

SHOT = 0.75     # s per tile (18 frames: the pose blend and the camera settle before the middle frame)
ep = KW.Episode('ep_castsheet', voice_lines=["Cast master sheet."], duration=2 * 24 * SHOT + 0.1)
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')
sci = ep.person('Howard', 'scientist', 'eatmore-sci', gender='m', age='old', race='caucasian', hair='short02', clipboard=True)

st = lambda **k: KW.pose('stand', at='stand', face=k.pop('face', 'calm'), **k)       # standing, arms relaxed (kit rest hands)
sc = lambda **k: KW.pose('stand', at='stand', face=k.pop('face', 'calm'), **k)      # street stand: full body clear (room 'stand' is behind the desk, studio is backlit with a stool)


def tiles(p):
    """[(tile, label, set, pose, cam, pct)] - section 4 of kit/cast_master.md, in order"""
    return [
        ('T1', 'standing front', 'street', sc(), KW.cam.wide(p, side=0, push=0.0), 50),
        ('T2', 'standing three-quarter', 'street', sc(), KW.cam.wide(p, side=35, push=0.0), 50),
        ('T3', 'standing side', 'street', sc(), KW.cam.wide(p, side=90, push=0.0), 50),
        ('T4', 'standing back', 'street', sc(), KW.cam.wide(p, side=180, push=0.0), 50),
        ('T5', 'face front calm', 'room', st(), KW.cam.face(p, side=0, push=0.0), 100),
        ('T6', 'face three-quarter calm', 'room', st(), KW.cam.face(p, side=35, push=0.0), 50),
        ('T7', 'face profile calm', 'room', st(), KW.cam.profile(p, part='face', push=0.0), 50),
        ('T8', 'calm', 'room', st(face='calm'), KW.cam.face(p, side=30, push=0.0), 50),
        ('T9', 'smile', 'room', st(face='smile'), KW.cam.face(p, side=30, push=0.0), 50),
        ('T10', 'focus', 'room', st(face='focus'), KW.cam.face(p, side=30, push=0.0), 50),
        ('T11', 'relief', 'room', st(face='relief'), KW.cam.face(p, side=30, push=0.0), 50),
        ('T12', 'worry', 'room', st(face='worry'), KW.cam.face(p, side=30, push=0.0), 50),
        ('T13', 'mouth open (spoon)', 'room', st(face={'talk': 1.5}), KW.cam.face(p, side=30, push=0.0), 50),
        ('T14', 'eyes closed (mid blink)', 'room', st(face='sleep', blink=False), KW.cam.face(p, side=30, push=0.0), 50),
        ('T15', 'right hand relaxed', 'room', st(), KW.cam.part(p, 'wrist_r', push=0.0, aim_dz=-0.09, dist=0.42, fstop=5.6, front=True, side=-40), 100),
        ('T16', 'left hand relaxed', 'room', st(), KW.cam.part(p, 'wrist_l', push=0.0, aim_dz=-0.09, dist=0.42, fstop=5.6, front=True, side=40), 50),
        ('T17', 'seated on the bed edge', 'hospital', KW.pose('sit', at='bed_sit', face='calm'), KW.cam.medium(p, side=25, push=0.0), 50),
        ('T18', 'right hand at the mouth', 'room', st(right='to_mouth'), KW.cam.medium(p, side=-35, push=0.0), 50),
        ('T19', 'head turned 45', 'street', sc(head=(0, 45, 0)), KW.cam.medium(p, side=20, push=0.0), 50),
        ('T20', 'head back 12', 'street', sc(head=(-12, 0, 0)), KW.cam.medium(p, side=60, push=0.0), 50),
        ('T21', 'head forward 12', 'street', sc(head=(12, 0, 0)), KW.cam.medium(p, side=60, push=0.0), 50),
        ('T22', 'light: room', 'room', st(), KW.cam.face(p, side=25, push=0.0), 50),
        ('T23', 'light: studio set (ep05 lab = room set, T22)', 'studio', KW.pose('stand', at='centre', face='calm'), KW.cam.face(p, side=25, push=0.0), 50),
        ('T24', 'light: hospital', 'hospital', KW.pose('sit', at='bed_sit', face='calm'), KW.cam.face(p, side=25, push=0.0), 50),
    ]


MAP = []
t = 0.0
for p in (ben, sci):
    for tid, label, set_, pose_, cam_, pct in tiles(p):
        name = f'{p.name}_{tid}'
        ep.shot(round(t, 3), name, set=set_, cast={p: pose_}, cam=cam_)
        MAP.append(dict(tile=tid, who=p.name, label=label, shot=name, frame=int(round((t + SHOT / 2) * KW.FPS)), pct=pct))
        t += SHOT

if __name__ == '__main__' and '--tiles' in sys.argv:
    print(json.dumps(MAP)); sys.exit(0)
ep.run()
