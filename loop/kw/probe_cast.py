"""Cast fix B probe (stills on GitHub: render_kw.yml only=...).  Lash clumps (KW_LASH2) + brighter mouth fill (KW_MOUTH_W)
for Ben, Howard, Maya: eye close / front / speak / spoon tiles.  Baseline = same tiles without the env flags."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if os.environ.get('KW_PROBE_BASE') != '1':
    os.environ.setdefault('KW_LASH2', '1'); os.environ.setdefault('KW_MOUTH_W', '0.3')
import kwkit as KW
SHOT = 0.75
ep = KW.Episode('probe_cast', voice_lines=["Cast probe."], duration=12 * SHOT + 0.1)
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')
how = ep.person('Howard', 'scientist', 'eatmore-sci', gender='m', age='old', race='caucasian', hair='short02', clipboard=True)
maya = ep.person('Maya', 'civilian', 'cast-maya', gender='f', age='young', race='hispanic', hair='short02', tee='red')
st = lambda **k: KW.pose('stand', at='stand', face=k.pop('face', 'calm'), **k)
t = 0.0
for p in (ben, how, maya):
    for nm, pose_, cam in [('eye', st(), KW.cam.part(p, 'eye_l', push=0.0, dist=0.20, front=True, side=20)),
                           ('front', st(), KW.cam.face(p, side=0, push=0.0)),
                           ('speak', st(face='speak', blink=False), KW.cam.face(p, side=25, push=0.0)),
                           ('spoon', st(face='spoon', blink=False), KW.cam.face(p, side=0, push=0.0))]:
        ep.shot(round(t, 3), f'{p.name}_{nm}', set='room', cast={p: pose_}, cam=cam); print('TILE', p.name, nm, int(round((t + SHOT / 2) * KW.FPS))); t += SHOT
ep.waive = {k: 'local probe' for k in ('1 shots', 'last shot', 'HOOK', 'shot ', 'voice', 'injury')}
ep.mouth_fix = True; ep.eyes_fix = True; ep.relight_after_pose = True
ep.run()
