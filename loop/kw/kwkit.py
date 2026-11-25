import math
"""kwkit - the Kinda Wild Films episode kit.  An episode is a short, mostly declarative file:

    import kwkit as KW
    ep = KW.Episode('ep_xxx', voice_lines=[...6 sentences...])
    ned = ep.person('Ned', 'civilian', 'xxx-ned', gender='m', age='middle', race='caucasian', tee='red')
    ep.shot(0.0, 'car_face', set='car', cast={ned: KW.pose('drive', right='pinch_nose', face='strain')},
            cam=KW.cam.face(ned, push=0.2))
    ...
    ep.run()

Run exactly like ep_sneeze.py (the GitHub workflow is unchanged):
    blender -b -P ep_xxx.py -- <outdir> <i0> <i1>      renders frames i0..i1-1  (env ONLY=20,150 / PCT / SAMPLES)
    blender -b -P ep_xxx.py -- --cues cues.json        timing, voice, foley and caption data for post_kw.py
    blender -b -P ep_xxx.py -- --check                 builds the scene and runs every guard rail (no render)
    python3 kwkit.py --check ep_xxx.py                 script-only guard rails, no Blender needed (fast)

Every name a weaker model may use is listed in kit/kw_card.md and in the tables below (SETS/SPOTS, FACES, HANDS,
ACTS, PARTS, cameras in class cam, effects in class fx).  Unknown names raise errors that list the valid ones.
All times inside a shot (act at=, fx at=, then()) are LOCAL seconds from the start of that shot.
Coordinates: metres, Z up, people face -Y when rz=0.  A person's 'left' is +X (their own left).
"""
import sys, os, math, json, random, re
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
# fx_kw puts ../b3d first on sys.path and b3d has its own cast.py: pin the kw one now
import importlib.util as _ilu
if 'cast' not in sys.modules:
    _sp = _ilu.spec_from_file_location('cast', os.path.join(HERE, 'cast.py')); _cm = _ilu.module_from_spec(_sp)
    sys.modules['cast'] = _cm; _sp.loader.exec_module(_cm)
FPS = 24
try:
    import bpy
    from mathutils import Vector, Matrix, Euler, Quaternion
except ImportError:          # plain python: only the script checks are available
    bpy = None

# ===================================================================================== small maths
def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def ease(u): u = clamp(u); return u * u * (3 - 2 * u)
def ramp(t, a, b):
    """0 before a, eased 0..1 between a and b, 1 after b."""
    return ease((t - a) / (b - a)) if b > a else float(t >= a)
def bump(t, c, w):
    """bell curve: 1 at t=c, ~0 beyond +-2w."""
    return math.exp(-((t - c) / w) ** 2)
def pop(u, s=2.2):
    """overshooting 0..1 'pop in' (for labels)."""
    u = clamp(u) - 1; return 1 + u * u * ((s + 1) * u + s)
def window(t, a, b, fade=0.15):
    """1 inside [a, b] with soft edges."""
    return ramp(t, a - fade, a) * (1 - ramp(t, b, b + fade))
def _lerp(a, b, w): return a + (b - a) * w
def _lerp3(a, b, w): return tuple(_lerp(x, y, w) for x, y in zip(a, b))

# ===================================================================================== names (validated)
SETS = ('car', 'hospital', 'room', 'street', 'studio', 'xray', 'macro', 'graphic')
WORLDS = ('car', 'hospital', 'studio_hdr', 'sky', 'night', 'warm', 'teal', 'room', 'street')
SET_WORLD = {'car': 'car', 'hospital': 'hospital', 'room': 'room', 'street': 'street', 'studio': 'warm',
             'xray': 'night', 'macro': 'sky', 'graphic': 'sky'}
# spot -> (kind, (x, y), rz deg, extra).  kind: seat | stand | stand_near (standing beside a seated patient, lifted with
# stand_z so heads keep real proportions) | lie.  extra for stand_near = head height above the patient's head.
SPOTS = {
    'car': {'driver': ('seat', (0.0, 0.0), 0, 0), 'passenger': ('seat', (0.75, 0.0), 0, 0)},
    'hospital': {'bed_sit': ('seat', (0.0, 0.0), 0, 0), 'bed_lie': ('lie', (-0.55, 0.25), 0, 0),
                 'bedside_l': ('stand_near', (0.47, -0.27), -119, 0.07), 'bedside_r': ('stand_near', (-0.48, -0.42), 135, 0.07),
                 'behind': ('stand_near', (0.36, 0.62), 12, 0.12), 'front': ('stand_near', (0.12, -0.78), 180, 0.08),
                 'lie_side': ('stand', (-0.55, -0.5), 180, 0), 'lie_far': ('stand', (-0.7, 0.98), 0, 0)},
    'room': {'desk': ('seat', (0.0, 0.0), 0, 0), 'stand': ('stand', (0.0, -0.15), 0, 0), 'stand_l': ('stand', (0.75, 0.05), -25, 0),
             'stand_r': ('stand', (-0.75, 0.05), 25, 0), 'counter': ('stand', (-1.25, 0.55), 90, 0), 'coworker': ('stand', (1.05, 0.55), -35, 0)},
    'street': {'walk': ('stand', (0.0, 0.0), 0, 0), 'stand': ('stand', (0.0, 0.0), 0, 0), 'stand_l': ('stand', (0.7, 0.05), -30, 0),
               'stand_r': ('stand', (-0.7, 0.05), 30, 0), 'bench': ('seat', (0.0, 1.05), 0, 0), 'ground': ('lie', (0.0, -0.1), 0, 0)},
    'studio': {'centre': ('stand', (60.0, 0.0), 0, 0), 'centre_l': ('stand', (60.42, 0.12), -22, 0), 'centre_r': ('stand', (59.58, 0.12), 22, 0),
               'centre_sit': ('seat', (60.0, 0.0), 0, 0)},
}
SEAT_H = {'room': 0.47, 'street': 0.46, 'studio': 0.5}        # seat surface heights (car / hospital seat the patient at origin)
BASES = ('stand', 'sit', 'drive', 'lie', 'walk')
# faces: name -> {expression key: weight}.  Keys are person.EXPR names (+ the extra ones added below).
FACES = {
    'neutral': {}, 'calm': {'smile': 0.15},
    'strain': {'puff': 1.3, 'pressed': 1.0, 'bulge': 0.9, 'squint': 0.25}, 'puffed': {'puff': 1.3, 'pressed': 1.0},
    'shock': {'wide': 1.0, 'open': 0.55, 'worry': 0.3}, 'pain': {'grimace': 0.8, 'squint': 0.45, 'worry': 0.6},
    'worry': {'worry': 0.9, 'wide': 0.35}, 'relief': {'smile': 0.8, 'squint': 0.1}, 'smile': {'smile': 0.95},
    'sleep': {'blink': 1.0}, 'talk': {'talk': 1.0}, 'disgust': {'twitch': 0.8, 'squint': 0.35, 'pressed': 0.4, 'frown': 0.6},
    'focus': {'frown': 0.35, 'squint': 0.15}, 'scream': {'open': 1.0, 'wide': 0.8, 'worry': 0.5}, 'nausea': {'pressed': 0.7, 'worry': 0.6, 'squint': 0.3, 'puff': 0.4},
    'sniff': {'twitch': 0.9, 'squint': 0.3}, 'blow': {'puff': 0.9, 'pressed': 0.6, 'squint': 0.6, 'bulge': 0.4},
}
if os.environ.get('KW_CAST', 'v1.1') == 'v1.1':
    # cast v1.1 (kit/kw_api.md "Faces v1.1"): six tuned expressions + three named jaw openings (front-teeth gap in mm,
    # per-character calibrated in heads_hg). Old names that meant the same thing now use them.
    FACES.update({
        'surprise': {'x_surprise': 1.0}, 'fear': {'x_fear': 1.0}, 'disgust': {'x_disgust': 1.0}, 'pain': {'x_pain': 1.0},
        'wince': {'x_wince': 1.0}, 'laugh': {'x_laugh': 1.0},
        'speak': {'x_gap': 8.0}, 'spoon': {'x_gap': 20.0}, 'bite': {'x_gap': 32.0, 'x_lips': 0.7},
        'shock': {'x_surprise': 1.0}, 'scream': {'x_fear': 1.0, 'x_gap': 26.0}, 'nausea': {'x_disgust': 0.6, 'pressed': 0.5},
    })
EXTRA_EXPR = {   # extra shape keys loaded on every person (MakeHuman CC0 targets)
    'blink': [('expression/units/caucasian/eye-left-closure', 1.0), ('expression/units/caucasian/eye-right-closure', 1.0)],
    'talk': [('expression/units/caucasian/mouth-open', 0.35), ('expression/units/caucasian/mouth-pursing', 0.15)],
    'frown': [('expression/units/caucasian/eyebrows-left-down', 0.8), ('expression/units/caucasian/eyebrows-right-down', 0.8), ('expression/units/caucasian/mouth-depression', 0.5)],
    'eyeswell_l': [('eyes/l-eye-bag-incr', 1.0), ('eyes/l-eye-eyefold-convex', 1.0), ('eyes/l-eye-push1-out', 0.6), ('expression/units/caucasian/eye-left-closure', 1.0), ('cheek/l-cheek-volume-incr', 0.5)],
    'eyeswell_r': [('eyes/r-eye-bag-incr', 1.0), ('eyes/r-eye-eyefold-convex', 1.0), ('eyes/r-eye-push1-out', 0.6), ('expression/units/caucasian/eye-right-closure', 1.0), ('cheek/r-cheek-volume-incr', 0.5)],
    'cheekswell_l': [('cheek/l-cheek-volume-incr', 1.0), ('cheek/l-cheek-bones-incr', 0.5)],
    'cheekswell_r': [('cheek/r-cheek-volume-incr', 1.0), ('cheek/r-cheek-bones-incr', 0.5)],
    'lipswell': [('mouth/mouth-lowerlip-volume-incr', 1.0), ('mouth/mouth-upperlip-volume-incr', 1.0)],
    'bloat': [('stomach/stomach-pregnant-incr', 1.0)],
}
SWELL = {'neck': 'neckswell', 'eye_l': 'eyeswell_l', 'eye_r': 'eyeswell_r', 'cheek_l': 'cheekswell_l', 'cheek_r': 'cheekswell_r',
         'lips': 'lipswell', 'belly': 'bloat'}
# body parts a hand can reach (of the same person or of another person); measured on the real mesh by ray casts
PARTS = ('nose', 'mouth', 'chin', 'forehead', 'head_top', 'eye_l', 'eye_r', 'cheek_l', 'cheek_r', 'ear_l', 'ear_r', 'neck_l', 'neck_r',
         'throat', 'chest', 'chest_l', 'chest_r', 'belly', 'shoulder_l', 'shoulder_r', 'wrist_l', 'wrist_r', 'back', 'knee_l', 'knee_r')
HAND_SHAPES = ('relaxed', 'open', 'fist', 'pinch', 'point', 'press2', 'hold', 'cup', 'claw')
HANDS = ('rest', 'lap', 'wheel', 'pinch_nose', 'cover_mouth', 'cover_nose', 'tissue_nose', 'wave', 'point_fwd', 'clipboard', 'write', 'hips',
         'to_mouth', 'phone_ear') + tuple('touch_' + p for p in PARTS) + tuple('clutch_' + p for p in ('chest', 'belly', 'neck', 'head', 'throat', 'forehead', 'eye_l', 'eye_r', 'cheek_l', 'cheek_r', 'ear_l', 'ear_r'))
ACTS = ('sneeze', 'cough', 'blow_nose', 'swallow', 'eat', 'drink', 'wince', 'nod', 'shake_head', 'gasp', 'breathe_hard', 'look_around', 'flinch', 'yawn', 'sniff', 'scratch', 'chew')
ITEMS = ('tray', 'burger', 'fries', 'salmon', 'wedges', 'salad', 'cup', 'penlight', 'tweezers', 'probe', 'magnifier',
         'paperclip', 'pea', 'ball', 'bulb', 'bench', 'sweet_potato', 'beans', 'ketchup', 'fork', 'bar')      # table-top props (kwprops) placed with fx.item
ITEM_CONTROLS = {'burger': ('eaten', 'gone'), 'fries': ('eaten', 'gone'), 'salmon': ('eaten', 'gone'), 'sweet_potato': ('gone',), 'beans': ('gone',), 'bar': ('fill', 'alpha', 'br'), 'tray': ('dx', 'dy'), 'wedges': ('eaten',), 'salad': ('eaten',),
                 'penlight': ('on',), 'pea': ('sprout',), 'ball': ('squash',)}
PROPS = ('tissue', 'cup', 'apple', 'pill', 'phone', 'pen', 'spoon', 'bottle', 'can', 'earbud', 'swab', 'pepper', 'slushie')
ORGANS = ('airway', 'lungs', 'esophagus', 'stomach', 'heart', 'brain', 'intestines', 'sinus', 'eyes', 'skull', 'vessels', 'kidneys', 'bladder', 'liver')
MACRO_KINDS = ('windpipe', 'esophagus', 'artery', 'vein', 'intestine', 'stomach', 'bone', 'nerve', 'sinus')
BANNED_SOUNDS = ('whoosh', 'swoosh', 'woosh', 'swish')
FX_FALLBACK = ('bounce', 'bubbles', 'crackle', 'engine', 'heal', 'inhale', 'pinch', 'pressure', 'puff', 'rip', 'rush', 'sneeze', 'sniff', 'thud', 'tick')

HG_AGE = {'kid': 'young', 'teen': 'young', 'young': 'young', 'middle': 'young', 'old': 'old'}


def hg_slot(role):
    """KW_HEADS=humgen cast slot name for a person role (m_young_caucasian ...); file = $KW_HG_LIB/<slot>.blend"""
    g = {'male': 'm', 'female': 'f'}.get(role.get('gender'), role.get('gender'))
    return f"{g}_{HG_AGE.get(role.get('age'), 'young')}_{role.get('race')}"


def _sound_names():
    try:
        import fx_kw
        return set(fx_kw.FX)
    except Exception:
        return set(FX_FALLBACK)

def _check_name(kind, name, valid):
    if name not in valid:
        raise ValueError(f"unknown {kind} {name!r}. Valid {kind}s: {', '.join(valid)}")
    return name

# ===================================================================================== declarative pieces
class Actor:
    """A person in the episode (built on demand).  Use the returned handle in cast={...} and camera/hand targets."""
    def __init__(self, ep, name, job, seed, role):
        self.ep, self.name, self.job, self.seed, self.role = ep, name, job, seed, dict(role)
        self.tan = self.role.pop('tan', None)
        self.p = None
    def __repr__(self): return f'<Actor {self.name} ({self.job})>'
    def part(self, name, offset=(0, 0, 0)):
        """a point on this person: KW.fx.label(..., at=ned.part('neck_l', (0, -0.05, 0.03)))"""
        _check_name('part', name, PARTS + ('face', 'head', 'hips', 'feet'))
        return Anchor(self, name, offset)

class Anchor:
    """a point relative to a person part; offset is (their-left, forward, up) metres."""
    def __init__(self, actor, part, offset=(0, 0, 0)): self.actor, self.part, self.offset = actor, part, tuple(offset)

class Act:
    def __init__(self, kind, **kw):
        self.kind = _check_name('act', kind, ACTS); self.kw = kw; self.at = float(kw.get('at', 0.5))
    def __repr__(self): return f'act.{self.kind}({self.kw})'

class act:
    """Body actions.  `at` = local shot time of the key moment.  They add head/body motion, the face, sounds and spray.
    Use inside KW.pose(..., act=KW.act.sneeze(at=1.2)) or a list act=[...]."""
    @staticmethod
    def sneeze(at=1.0, big=1.0, spray=True): return Act('sneeze', at=at, big=big, spray=spray)
    @staticmethod
    def cough(at=0.5, n=3, gap=0.45, spray=False): return Act('cough', at=at, n=n, gap=gap, spray=spray)
    @staticmethod
    def blow_nose(at=0.4, dur=1.4, hard=1.0): return Act('blow_nose', at=at, dur=dur, hard=hard)
    @staticmethod
    def swallow(at=0.5): return Act('swallow', at=at)
    @staticmethod
    def eat(at=0.3, bites=2, beats=None, chew=None, drop=None, nod=None, trunk=None, gaze=None):
        """beats=(lift, in, out, down) frames per bite (humgen spoon); chew=(start, end) frames after `at` (one chew); drop: m the spoon goes below the mouth"""
        kw = dict(at=at, bites=bites)
        if drop is not None: kw['drop'] = float(drop)
        if nod is not None: kw['nod'] = float(nod)
        if trunk is not None: kw['trunk'] = float(trunk)
        if gaze is not None: kw['gaze'] = gaze
        if beats is not None: kw['beats'] = tuple(beats)
        if chew is not None: kw['chew'] = tuple(chew)
        return Act('eat', **kw)
    @staticmethod
    def chew(at=0.5, until=3.0, rate=1.5, gap=7.0, side=1.0, bulge=0.35, swallow=None):
        """closed-lip chewing (humgen): `rate` chews a second from local `at` to `until`; jaw opens `gap` mm (front teeth)
        with the lips sealed, chin to his left on each close (side 0..1), cheek bulge (first six chews, then 60 %).
        swallow = local time: 10-frame pause in the chew with a 1 deg chin dip."""
        return Act('chew', at=at, until=until, rate=rate, gap=gap, side=side, bulge=bulge, swallow=swallow)
    @staticmethod
    def drink(at=0.3, dur=1.2): return Act('drink', at=at, dur=dur)
    @staticmethod
    def wince(at=0.5, hard=1.0): return Act('wince', at=at, hard=hard)
    @staticmethod
    def nod(at=0.3, n=2): return Act('nod', at=at, n=n)
    @staticmethod
    def shake_head(at=0.3, n=2): return Act('shake_head', at=at, n=n)
    @staticmethod
    def gasp(at=0.4): return Act('gasp', at=at)
    @staticmethod
    def breathe_hard(at=0.0, rate=1.6): return Act('breathe_hard', at=at, rate=rate)
    @staticmethod
    def look_around(at=0.2): return Act('look_around', at=at)
    @staticmethod
    def flinch(at=0.4): return Act('flinch', at=at)
    @staticmethod
    def yawn(at=0.3): return Act('yawn', at=at)
    @staticmethod
    def sniff(at=0.4): return Act('sniff', at=at)
    @staticmethod
    def scratch(at=0.2): return Act('scratch', at=at)

class Hand:
    """What one hand does.  Strings are shortcuts: 'rest', 'wheel', 'pinch_nose', 'touch_neck_l', 'clutch_chest' ...
    Objects give more control: KW.hand.touch(doc_target_person, 'neck_l', shape='press2', pulses=[0.4, 0.9])."""
    def __init__(self, kind, owner=None, part=None, shape=None, pulses=(), prop=None, at=None, rub=0.0, pad=None):
        self.kind, self.owner, self.part, self.shape, self.pulses, self.prop, self.at, self.rub, self.pad = kind, owner, part, shape, tuple(pulses), prop, at, rub, pad
    def key(self): return (self.kind, self.owner.name if isinstance(self.owner, Actor) else None, self.part, self.shape, self.prop, self.pad)
    def __repr__(self): return f'hand.{self.kind}({self.part}, {self.shape})'

class hand:
    @staticmethod
    def touch(person, part, shape='press2', pulses=(), rub=0.0):
        """fingertips (or palm for shape='open'/'cup') on a part of `person` (yourself or someone else). pulses = local
        times of short presses (the doctor pressing)."""
        _check_name('part', part, PARTS); _check_name('hand shape', shape, HAND_SHAPES)
        return Hand('touch', person, part, shape, pulses, rub=rub)
    @staticmethod
    def press(person, part, pulses=(0.4,)):
        """two fingers press on another person's part, with press pulses at local times."""
        return hand.touch(person, part, 'press2', pulses)
    @staticmethod
    def clutch(part):
        """open hand grabbing your own part (pain)."""
        return Hand('touch', None, _check_name('part', part, PARTS), 'claw')
    @staticmethod
    def point(at):
        """point the index finger at a person (Actor), Anchor (ned.part('neck_l')) or a world point (x, y, z)."""
        return Hand('point', None, None, 'point', at=at)
    @staticmethod
    def hold(prop, where='chest'):
        """hold a prop ('cup', 'apple', 'pill', 'phone', 'tissue' ...) in front of the chest, at the mouth or the nose."""
        _check_name('prop', prop, PROPS)
        if where not in ('chest', 'mouth', 'nose', 'ear', 'out'): raise ValueError("hold where: chest | mouth | nose | ear | out")
        return Hand('hold', None, {'mouth': 'mouth', 'nose': 'nose', 'ear': None}.get(where), 'hold', prop=prop, at=where)

GRIPS = {'grip_cup': ('cup',), 'grip_tool': ('tweezers', 'penlight'), 'grip_pinch': ('pea', 'paperclip'), 'grip_burger': ('burger',)}
def _grip(name, item=None, where='chest'):
    """cast v1.1 (KW_CAST=v1.1, HG cast): a hand grip on a kwprops item - grip_cup | grip_tool (penlight, tweezers) |
    grip_pinch (pea, paperclip) | grip_burger (two hands: give it to both hands; where='mouth' = bite).  The item follows the hand.
    (rest_belly was dropped in round 2: for a hand on the belly use KW.hand.clutch('belly') on a seated pose.)"""
    _check_name('grip', name, tuple(GRIPS))
    item = item or GRIPS[name][0]; _check_name(name + ' item', item, GRIPS[name])
    if where not in ('chest', 'mouth', 'out', 'track'): raise ValueError('grip where: chest | mouth | out | track')
    if where == 'track' and name != 'grip_burger': raise ValueError("grip where='track': grip_burger only (path in ep.burger_track)")
    part = {'mouth': 'mouth'}.get(where)
    # the cup rides on the solved HG can grip (the carrier mesh is hidden, the kwprops item is shown); tools, pinch and burger
    # are fixed hand-authored finger tables (heads_hg.AUTH) with the item put on the hand
    if name == 'grip_cup': return Hand('hold', None, part, 'hold', prop='can', at=where, pad='cup')
    return Hand('hold', None, part, 'hold', prop='g_' + item, at=where)
hand.grip = staticmethod(_grip)

def _hand_spec(h):
    if h is None or isinstance(h, Hand): return h
    if not isinstance(h, str): raise TypeError(f'hand must be a string or KW.hand.*(), got {h!r}')
    _check_name('hand', h, HANDS)
    if h.startswith('touch_'): return Hand('touch', None, h[6:], 'press2')
    if h.startswith('clutch_'):
        p = h[7:]; p = {'neck': 'neck_l', 'head': 'forehead'}.get(p, p)
        return Hand('touch', None, p, 'claw' if p in ('chest', 'belly') else 'open')
    if h == 'cover_mouth': return Hand('touch', None, 'mouth', 'open')
    if h == 'cover_nose': return Hand('touch', None, 'nose', 'cup')
    if h == 'tissue_nose': return Hand('touch', None, 'nose', 'cup', prop='tissue')
    if h == 'to_mouth': return Hand('touch', None, 'mouth', 'pinch')
    if h == 'phone_ear': return Hand('touch', None, 'ear_r', 'hold', prop='phone')
    return Hand(h)

class Pose:
    """One body pose.  base: stand | sit | drive | lie | walk.  at: spot name of the shot's set (see SPOTS), or 'set.spot'.
    left/right: hand (see HANDS / KW.hand).  face: name, 'a+b' or {'pain': 0.6, 'worry': 0.4}.
    head=(nod, turn, tilt) degrees (+nod looks down, +turn looks to their left).  look: Actor / Anchor / (x,y,z).
    lean: degrees forward.  act: KW.act.* or list.  flush: 0..1 red skin.  swell: {'eye_l': 1.0, 'neck': 0.8} (SWELL).
    walk_speed: m/s forward for base='walk'.  Pose.then(t, **changes) blends into a changed pose at local time t."""
    def __init__(self, base='stand', at=None, left=None, right=None, face='neutral', head=(0, 0, 0), look=None, lean=0.0,
                 act=None, flush=0.0, swell=None, walk_speed=0.0, blink=True, blend=0.35, xray=False, hold=None):
        self.base = _check_name('base pose', base, BASES)
        self.at = at; self.left = _hand_spec(left); self.right = _hand_spec(right)
        self.face = _face_dict(face); self.head = tuple(head) if head is not None else (0, 0, 0); self.look = look; self.lean = float(lean)
        acts = act if isinstance(act, (list, tuple)) else ([act] if act else [])
        for a in acts:
            if not isinstance(a, Act): raise TypeError(f'act must be KW.act.*(...), got {a!r}')
        self.acts = list(acts); self.flush = flush; self.swell = dict(swell or {})
        for k in self.swell: _check_name('swell', k, tuple(SWELL))
        self.walk_speed = walk_speed; self.blink = blink; self.blend = blend
        self.keys = [(0.0, self)]
    def copy(self, **kw):
        q = Pose.__new__(Pose); q.__dict__.update(self.__dict__)
        for k, v in kw.items():
            if k in ('left', 'right'): v = _hand_spec(v)
            elif k == 'face': v = _face_dict(v)
            elif k == 'act': v = list(v) if isinstance(v, (list, tuple)) else ([v] if v else []); k = 'acts'
            elif k == 'base': _check_name('base pose', v, BASES)
            elif k == 'swell': v = dict(v)
            elif k not in q.__dict__: raise TypeError(f'unknown pose field {k!r}')
            setattr(q, k, v)
        q.keys = None; return q
    def then(self, t, **changes):
        """at local time t, blend (over `blend` s, default 0.35) into this pose with `changes`."""
        last = self.keys[-1][1]; q = last.copy(**changes); out = Pose.__new__(Pose); out.__dict__.update(self.__dict__)
        out.keys = list(self.keys) + [(float(t), q)]; return out
    def at_time(self, u):
        """-> (pose_a, pose_b, w): blend weight w from a to b at local time u"""
        ks = self.keys
        for i in range(len(ks) - 1, 0, -1):
            t, q = ks[i]
            if u >= t:
                w = ease((u - t) / max(1e-3, q.blend)); return ks[i - 1][1], q, w
        return ks[0][1], ks[0][1], 0.0

def pose(base='stand', **kw):
    """KW.pose('sit', right='clutch_chest', face='pain', act=KW.act.cough(at=0.4)) - see class Pose."""
    return Pose(base, **kw)

def _face_dict(face):
    if face is None: return {}
    if isinstance(face, dict):
        for k in face: _check_name('face', k, tuple(FACES))
        return dict(face)
    out = {}
    for nm in str(face).split('+'):
        nm = nm.strip(); _check_name('face', nm, tuple(FACES)); out[nm] = 1.0
    return out

# ===================================================================================== cameras
def glide_eval(keys, t):
    """ONE continuous camera move: keys = [(t, value), ...]; monotone cubic (Fritsch-Carlson) in log space, so the move
    eases through the keys without stopping dead (flat only at the first / last key and at turning points)."""
    ks = sorted(keys)
    if t <= ks[0][0]: return ks[0][1]
    if t >= ks[-1][0]: return ks[-1][1]
    xs = [k[0] for k in ks]; ys = [math.log(max(k[1], 1e-6)) for k in ks]; n = len(xs)
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    m = [0.0] * n
    for i in range(1, n - 1): m[i] = (d[i - 1] + d[i]) / 2 if d[i - 1] * d[i] > 0 else 0.0
    for i in range(n - 1):
        if d[i] == 0: m[i] = m[i + 1] = 0.0
        else:
            al, be = m[i] / d[i], m[i + 1] / d[i]; q = al * al + be * be
            if q > 9: tau = 3 / math.sqrt(q); m[i] = tau * al * d[i]; m[i + 1] = tau * be * d[i]
    i = max(j for j in range(n - 1) if xs[j] <= t); h = xs[i + 1] - xs[i]; u = (t - xs[i]) / h
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
    return math.exp(h00 * ys[i] + h10 * h * m[i] + h01 * ys[i + 1] + h11 * h * m[i + 1])

class Cam:
    def __init__(self, kind, subj=None, **o):
        self.kind, self.subj, self.o = kind, subj, o
    def __repr__(self): return f'cam.{self.kind}'

class cam:
    """Camera presets (relative to a person, a prop/fx, an organ or a macro set).  Common options:
    lens (mm), push (0..1 fraction of the distance to dolly in over the shot; negative pulls out), orbit (degrees over the
    shot), side (degrees around the subject, + = toward their left), height (m up/down), shake (0..1 handheld), hits
    (local times of impact shakes), fstop, dist (m), follow (0..1 how much the camera follows the live head)."""
    @staticmethod
    def face(p, **o): return Cam('face', p, **o)
    @staticmethod
    def medium(p, **o): return Cam('medium', p, **o)
    @staticmethod
    def wide(p, **o): return Cam('wide', p, **o)
    @staticmethod
    def two_shot(a, b, **o): return Cam('two_shot', a, other=b, **o)
    @staticmethod
    def over_shoulder(a, b, **o):
        """behind a's shoulder, looking at b's face"""
        return Cam('over_shoulder', a, other=b, **o)
    @staticmethod
    def profile(p, part='face', **o):
        """pure side view (their left side unless side=-90); part = face | neck | chest | belly"""
        return Cam('profile', p, part=part, **o)
    @staticmethod
    def low_hero(p, **o): return Cam('low_hero', p, **o)
    @staticmethod
    def top_down(p, part='chest', **o):
        """straight down (best for a lying person); the head is at the top of the frame"""
        return Cam('top_down', p, part=part, **o)
    @staticmethod
    def part(p, part, **o):
        """close-up of one body part (neck_l, eye_l, belly, wrist_r ...), seen from outside the body"""
        _check_name('part', part, PARTS + ('calf_r', 'calf_l')); return Cam('part', p, part=part, **o)
    @staticmethod
    def plunge(p, into='nose', **o):
        """fly into the nose / mouth / ear_l / ear_r / eye_l / eye_r: the transition into the body (next shot = xray/macro)"""
        if into not in ('nose', 'mouth', 'ear_l', 'ear_r', 'eye_l', 'eye_r', 'neck_l', 'neck_r', 'chest', 'belly'): raise ValueError('plunge into: nose | mouth | ear_l | ear_r | eye_l | eye_r | neck_l | neck_r | chest | belly')
        return Cam('plunge', p, part=into, **o)
    @staticmethod
    def xray(p, organ, view='34', **o):
        """x-ray glass body view centred on an organ (see ORGANS); view = profile | front | 34 | back34"""
        _check_name('organ', organ, ORGANS); return Cam('xray', p, organ=organ, view=view, **o)
    @staticmethod
    def macro(m, view='hole', **o):
        """macro tube set: view = hole (outside, on the hole/tear) | wide (outside, long view) | inside (fly through the lumen) | object"""
        if view not in ('hole', 'wide', 'inside', 'object'): raise ValueError('macro view: hole | wide | inside | object')
        return Cam('macro', m, view=view, **o)
    @staticmethod
    def prop(fx_item=None, **o):
        """frames a graphic prop (calendar, skin_block, scan, gauge on its own station). Default: the shot's first prop."""
        return Cam('prop', fx_item, **o)
    @staticmethod
    def at(pos, look, lens=40, **o):
        """escape hatch: fixed world position looking at a world point"""
        return Cam('at', None, pos=tuple(pos), look=tuple(look), lens=lens, **o)
    @staticmethod
    def path(keys, fstop=4.0, **o):
        """one continuous camera move through world keys [(local_t, pos, look, lens), ...]: each segment eases
        (smoothstep) from key to key, holding before the first and after the last key"""
        ks = []
        for k in keys:      # (t, pos, look, lens) or (t, KW.cam.*(...)): a preset evaluated live at that key (e.g. the frame-0 face view)
            if len(k) == 2 and isinstance(k[1], Cam): ks.append((float(k[0]), k[1], None, None))
            else: t, p, l, ln = k; ks.append((float(t), tuple(p), tuple(l), float(ln)))
        ks.sort(key=lambda x: x[0])
        if len(ks) < 1: raise ValueError('cam.path: at least one key')
        return Cam('path', None, keys=ks, fstop=fstop, **o)
    @staticmethod
    def bench(which='wide', at=(63.0, 0.0), top=0.9, lens=None, look=(0.0, 0.0), h=None, width=None, **o):
        """table-top presets on an fx.item('bench') whose top centre is at (at, top).  'wide' frames the whole 120 cm top
        from in front and above (lens 35); 'close' frames about 30 cm of the top (lens 50).  look = (dx, dy) shift of the
        aim point on the top; h = camera height above the top (default wide 0.55 m / close 0.2 m, scaled with width);
        width = framed width in metres (overrides the preset's 1.25 / 0.30)."""
        if which not in ('wide', 'close'): raise ValueError("cam.bench which: 'wide' | 'close'")
        lens = lens or (35 if which == 'wide' else 50); w0 = 1.25 if which == 'wide' else 0.30; width = width or w0
        d = width * lens / 20.25; hh = h if h is not None else (0.55 if which == 'wide' else 0.2) * width / w0
        tgt = (at[0] + look[0], at[1] + look[1], top); dy = math.sqrt(max(1e-4, d * d - hh * hh))
        return Cam('at', None, pos=(tgt[0], tgt[1] - dy, top + hh), look=tgt, lens=lens, **o)
    @staticmethod
    def loop(**o):
        """LAST SHOT ONLY: ends exactly on the first shot's camera so the Short loops."""
        return Cam('loop', None, **o)

# ===================================================================================== effects (declarative; built by kwbody / gfx)
class FX:
    def __init__(self, _kind, **o): self.kind, self.o = _kind, o; self.obj = None; self.shot = None
    def __repr__(self): return f'fx.{self.kind}'
    def sounds(self):
        """auto sound cues (local time, name, gain)"""
        o = self.o; k = self.kind
        if k == 'gauge': return [(o.get('at', 0.2) + o.get('dur', 1.2), 'thud', 0.8)] if o.get('slam', True) else []
        if k == 'tear': return [(o.get('at', 0.5), 'rip', 1.0), (o.get('at', 0.5) + 0.05, 'thud', 0.7)]
        if k == 'crack': return [(o.get('at', 0.5), 'rip', 0.8), (o.get('at', 0.5) + 0.03, 'thud', 0.9)]
        if k == 'leak': return [(o.get('at', 0.2), 'bubbles', 0.7)]
        if k == 'flow' and o.get('sound', True): return [(o.get('at', 0.0), 'rush', 0.7)]
        if k == 'flow_path' and o.get('sound'): return [(o.get('at', 0.0), 'rush', 0.6)]
        if k == 'counter': return [(o.get('at', 0.2) + o.get('dur', 1.0), 'tick', 0.6)]
        if k == 'pressure': return [(o.get('at', 0.0), 'pressure', 0.8)]
        if k == 'calendar': return [(o.get('at', 0.1) + 0.3 * i, 'pinch', 0.5) for i in range(max(1, int(o.get('weeks', 5)) - 1))]
        if k == 'scan': return [(o.get('heal_at', 0.6), 'heal', 0.7)] if o.get('heal', True) else []
        if k == 'skin_block': return [(o.get('at', 0.2), 'bubbles', 0.6)]
        if k == 'crackle': return [(t, 'crackle', 1.0) for t in o.get('times', (0.4,))]
        if k == 'swell_air': return [(o.get('at', 0.2), 'bubbles', 0.6)]
        return []
    def is_prop(self): return self.kind in ('calendar', 'scan', 'skin_block', 'earth') or (self.kind == 'gauge' and self.o.get('place') == 'station')

class fx:
    """Effects attached to a shot (all times local).  Graphics: gauge, label, arrow, bracket, calendar, scan, skin_block, crackle.
    Body: flow (particles along an organ path), pressure (organ glows/pulses/swells), seal (red X over nose/mouth),
    swell_air (air bubbles collecting under skin/around an eye), glow (an organ lights up).  Macro: tear, crack, leak, block, particles."""
    @staticmethod
    def gauge(to=1.0, at=0.2, dur=1.2, label=None, low='NORMAL', high=None, title='PRESSURE', place='screen', pos=(0.72, 0.6), size=1.0, slam=True):
        """pressure dial: needle rises 0.1 -> `to` (0..1) from local `at` over `dur`; `label` (e.g. '20x') pops beside it."""
        return FX('gauge', to=to, at=at, dur=dur, label=label, low=low, high=high, title=title, place=place, pos=pos, size=size, slam=slam)
    @staticmethod
    def label(text, at=0.2, pos=(0.5, 0.72), near=None, size=1.0, color='red', dur=None, keys=None):
        """3D word that pops in (keep to 1-3 words or a number). pos = screen position (0..1, 0..1 from bottom-left) or near=Anchor.
        A pos label is printed on the screen: same size and place whatever the camera does, never wider than 960 px (a long word
        is scaled down to fit). dur = seconds on screen, then it is gone (like a cut); a label may be given to several shots
        (at < 0 in the later ones) to stay on through a segment change of one continuous camera move.
        keys = [(local_t, {'pos': (x, y), 'width': px}), ...] (pos labels only): the label eases (smoothstep) to each key's
        screen place / width cap; with no keys a label behaves exactly as before."""
        if color not in ('red', 'yellow', 'white', 'green', 'blue'): raise ValueError('label color: red | yellow | white | green | blue')
        if keys:
            if near is not None: raise ValueError('label keys: pos labels only')
            for _, v in keys:
                for kk in v:
                    if kk not in ('pos', 'width'): raise ValueError(f"label key {kk!r}: 'pos' | 'width'")
            return FX('label', text=str(text), at=at, pos=pos, near=near, size=size, color=color, dur=dur, keys=[(float(t), dict(v)) for t, v in keys])
        return FX('label', text=str(text), at=at, pos=pos, near=near, size=size, color=color, dur=dur)
    @staticmethod
    def arrow(points=None, at=0.2, dur=0.6, color='yellow', width=0.012, path=None, person=None):
        """growing curved arrow along world points, or along a named organ path of a person (see flow paths)"""
        return FX('arrow', points=points, at=at, dur=dur, color=color, width=width, path=path, person=person)
    @staticmethod
    def bracket(p0, p1, text, at=0.2, macro=None):
        """measuring bracket between two world points (or on a macro set's hole when macro= given and p0/p1 None)"""
        return FX('bracket', p0=p0, p1=p1, text=text, at=at, macro=macro)
    @staticmethod
    def earth(mode='wrap2', at=0.1, dur=1.2, spin=8.0, lon=10.0, lat=15.0, pulse_at=None, cam_raise=0.0):
        """NASA Blue Marble globe with a growing red vessel line (own station: set='graphic', cam=KW.cam.prop()).
        mode 'wrap2': two laps from the front-centre (2nd lap 6 deg beside the 1st); 'half': left limb -> 0.22 lap solid ->
        0.47 lap pale, white tick at 0.50 on the right limb.  spin deg/s eastward (0 = still).  lon/lat = centre of the view.
        cam_raise: camera elevation (deg) used by cam.prop for this station."""
        if mode not in ('wrap2', 'half'): raise ValueError("earth mode: 'wrap2' | 'half'")
        return FX('earth', mode=mode, at=at, dur=dur, spin=spin, lon=lon, lat=lat, pulse_at=pulse_at, cam_raise=cam_raise)
    @staticmethod
    def item(kind, pos=(0.0, 0.0, 0.0), rz=0.0, tilt=0.0, keys=(), on=None, point=None, light=None, **params):
        """table-top prop (kwprops) standing at world pos (or pos offset from an earlier fx.item `on`, at its named point:
        'floor' for trays, 'top' for the bench).  rz = turn in degrees.  keys = [(local_t, {control: v}), ...] eased like
        wound keys; controls: burger/fries/salmon/wedges/salad eaten, penlight on, pea sprout, ball squash (all 0..1).
        params go to the prop (e.g. style='clinic', liner='paper', top=(1.2, 0.6), h=0.9, color=(r, g, b)).
        light = scale of the 3-light prop rig around the shot's items when no person is in the shot (default 0.45)."""
        _check_name('item', kind, ITEMS)
        for _, v in keys:
            for kk in v:
                if kk not in ITEM_CONTROLS.get(kind, ()): raise ValueError(f'item {kind} control {kk!r}: one of {ITEM_CONTROLS.get(kind, ())}')
        return FX('item', item=kind, pos=tuple(pos), rz=rz, tilt=tilt, keys=[(float(t), dict(v)) for t, v in keys], on=on, point=point, light=light, params=params)
    @staticmethod
    def counter(v0, v1, unit='', at=0.2, dur=1.0, pos=(0.5, 0.78), size=1.0, color='yellow', decimals=0, sign=False):
        """number label that counts v0 -> v1 (eased) from local `at` over `dur`, with a unit ('kcal', '%', 'x').
        sign=True prints '+'.  Yellow / white label style; size 1.0 = digits about 5 % of frame height (keep >= 0.8)."""
        if color not in ('yellow', 'white', 'red', 'green', 'blue'): raise ValueError('counter color: yellow | white | red | green | blue')
        return FX('counter', v0=float(v0), v1=float(v1), unit=str(unit), at=at, dur=dur, pos=pos, size=size, color=color, decimals=int(decimals), sign=sign)
    @staticmethod
    def beam(origin, target, at=0.0, fade=0.3, width=0.04, color=(1.0, 0.95, 0.8), strength=1.0, sweep=None):
        """light beam: spot light + soft emissive cone (no volume).  origin/target = world points or (fx.item, 'point')
        e.g. origin=(pen, 'tip').  width = beam diameter at the target (m).  fades in over `fade` s from `at`.
        sweep = (target2, t0, t1): the aim slides to target2 between local t0 and t1."""
        return FX('beam', origin=origin, target=target, at=at, fade=fade, width=width, color=tuple(color), strength=strength, sweep=sweep)
    @staticmethod
    def flow_path(points, at=0.0, dur=None, color='green', size=0.004, count=40, speed=1.0, spread=0.003, sound=False):
        """glowing particles streaming along any world curve (points smoothed); size = particle radius (m), speed = laps
        per ~1.1 s, count = density, spread = sideways jitter (m)."""
        if color not in ('green', 'red', 'blue', 'yellow', 'white', 'orange'): raise ValueError('flow color: green | red | blue | yellow | white | orange')
        return FX('flow_path', points=[tuple(p) for p in points], at=at, dur=dur, color=color, size=size, count=count, speed=speed, spread=spread, sound=sound)
    @staticmethod
    def wound(person, keys, side='R'):
        """a healing cut on the person's own calf skin (kwwound).  keys = [(local_t, {open, stitches, out, red, collagen, vessels, line, scar}), ...]
        values ease (smoothstep) from key to key; missing names keep the previous key's value.  Camera: KW.cam.part(p, 'calf_r')."""
        return FX('wound', person=person, keys=[(float(t), dict(v)) for t, v in keys], side=side)
    @staticmethod
    def calendar(weeks=3, at=0.1, dur=1.0):
        """wall calendar flips from WEEK 1 to WEEK `weeks` (1..5). Own station: use set='graphic', cam=KW.cam.prop()"""
        if not 1 <= int(weeks) <= 5: raise ValueError('calendar weeks 1..5')
        return FX('calendar', weeks=int(weeks), at=at, dur=dur)
    @staticmethod
    def scan(kind='head', heal=True, heal_at=0.6, title=None):
        """CT monitor. kind: neck (airway with a break) | head (skull + eye sockets, crack, air pockets) | chest | belly.
        heal=True animates the problem healing at local heal_at; heal=False keeps it 'found'."""
        if kind not in ('neck', 'head', 'chest', 'belly'): raise ValueError('scan kind: neck | head | chest | belly')
        return FX('scan', kind=kind, heal=heal, heal_at=heal_at, title=title)
    @staticmethod
    def skin_block(at=0.2, press_at=None):
        """cut block of skin: air bubbles grow under it from `at`; a finger presses at press_at"""
        return FX('skin_block', at=at, press_at=press_at)
    @staticmethod
    def crackle(near, times=(0.4,)):
        """yellow crackle ticks at an Anchor (ned.part('neck_l')) at local times (with the crackle sound)"""
        return FX('crackle', near=near, times=tuple(times))
    @staticmethod
    def flow(person, path, at=0.0, dur=None, color='green', count=70, speed=1.0, heat=0.0, sound=True, stop=1.0):
        """particles stream along an organ path of `person` (x-ray shots). paths: see kwbody.PATHS
        (e.g. 'air_out_nose', 'air_out_mouth', 'air_in', 'nose_to_sinus', 'sinus_to_eye', 'food_down', 'blood_heart', 'brain_blood').
        stop<1 makes particles bunch up at that fraction of the path (blocked flow)."""
        if color not in ('green', 'red', 'blue', 'yellow', 'white', 'orange'): raise ValueError('flow color: green | red | blue | yellow | white | orange')
        return FX('flow', person=person, path=path, at=at, dur=dur, color=color, count=count, speed=speed, heat=heat, sound=sound, stop=stop)
    @staticmethod
    def pressure(person, organ, at=0.0, dur=2.0, swell=0.45):
        """an organ heats up, pulses and swells (x-ray shots)"""
        _check_name('organ', organ, ORGANS); return FX('pressure', person=person, organ=organ, at=at, dur=dur, swell=swell)
    @staticmethod
    def glow(person, organ, at=0.0, dur=0.6, color='red'):
        """an organ lights up (to show where something happens)"""
        _check_name('organ', organ, ORGANS); return FX('glow', person=person, organ=organ, at=at, dur=dur, color=color)
    @staticmethod
    def seal(person, where=('nose', 'mouth'), at=0.4):
        """red rings with an X pop over the nose and/or mouth (x-ray shots): 'the air has no way out'"""
        return FX('seal', person=person, where=tuple(where) if not isinstance(where, str) else (where,), at=at)
    @staticmethod
    def swell_air(person, where='eye_l', at=0.2, dur=1.6, shrink_at=None):
        """glowing air pockets collect at a place (eye_l, eye_r, neck_l, neck_r, chest) in x-ray shots; shrink_at = heal"""
        if where not in ('eye_l', 'eye_r', 'neck_l', 'neck_r', 'chest', 'cheek_l', 'cheek_r'): raise ValueError('swell_air where: eye_l | eye_r | neck_l | neck_r | chest | cheek_l | cheek_r')
        return FX('swell_air', person=person, where=where, at=at, dur=dur, shrink_at=shrink_at)
    @staticmethod
    def crack_line(person, where='eye_l', at=0.3):
        """a glowing red crack appears on a bone in an x-ray shot (eye_l / eye_r socket wall, skull, rib_l, rib_r)"""
        return FX('crack_line', person=person, where=where, at=at)
    # ---- macro set effects (the shot must have set='macro', macro=<handle from ep.macro()>)
    @staticmethod
    def tear(at=0.5, size=1.0):
        """the wall strains, then rips open (hole) at local `at`, with a flash and a jet of particles"""
        return FX('tear', at=at, size=size)
    @staticmethod
    def crack(at=0.5, size=1.0):
        """bone version of tear: a thin wall cracks like an eggshell"""
        return FX('crack', at=at, size=size)
    @staticmethod
    def leak(at=0.2, rate=1.0, kind='bubbles'):
        """bubbles (or 'blood' / 'fluid') stream out through the existing hole"""
        return FX('leak', at=at, rate=rate, kind=kind)
    @staticmethod
    def particles(kind='air', at=0.0, speed=1.0, count=60):
        """stream inside the tube: air | blood | food | acid | bubbles"""
        return FX('particles', kind=kind, at=at, speed=speed, count=count)
    @staticmethod
    def block(obj='bolus', at=0.0, move=0.0):
        """a foreign object / blockage inside the tube: bolus | bone | coin | pill | earbud | stone | clot | worm | denture"""
        return FX('block', obj=obj, at=at, move=move)
    @staticmethod
    def heal(at=0.3, dur=1.0):
        """the hole / crack closes over (recovery shots)"""
        return FX('heal', at=at, dur=dur)

class MacroSet:
    """handle returned by ep.macro(); built far away from everything else (no set collides)."""
    def __init__(self, ep, kind, hole, idx, label):
        self.ep, self.kind, self.hole, self.idx, self.label = ep, kind, hole, idx, label; self.obj = None
    def __repr__(self): return f'<macro {self.kind}>'

class Shot:
    def __init__(self, ep, t, name, set, cast, cam_, fx_, sounds, world, xray, macro, organs, note):
        self.ep, self.t, self.name, self.set, self.cast, self.cam, self.fx, self.sounds = ep, float(t), name, set, cast, cam_, list(fx_ or []), list(sounds or [])
        self.world, self.xray, self.macro, self.organs, self.note = world, xray, macro, organs, note
        self.end = None
    @property
    def length(self): return self.end - self.t

# ===================================================================================== the episode
CAP_Y = 0.78            # caption centre, fraction from the top; Zack D. Films measured 0.78 (match audit 2026-11-22)
MAX_HOLD = 2.2          # longest shot (hook spec mid-video rule)
HOOK_FILLER = ('so today', 'did you know', 'have you ever', 'this is the story', 'meet ', 'while he was', 'while she was', 'one day', 'once upon')
HOOK_TRANSIENTS = {'thud', 'pinch', 'bounce', 'rip', 'sneeze', 'crackle'}

class Episode:
    """ep = KW.Episode('ep_xxx', voice_lines=[...], music='sneaky_snitch')
    voice_lines: 5-6 sentences (80-90 words total).  Timing per sentence comes from <ep>.vo.json (made by
    `python3 kwvo.py ep_xxx.py`, real TTS durations) or else from a words-per-second estimate.  ep.line(i) = start of
    sentence i (0-based), ep.line_end(i) = its end; use them to place shots on the words."""
    def __init__(self, name, voice_lines, injury=None, music='sneaky_snitch', duration=None, voice='en-US-ChristopherNeural', rate='+6%', music_gain=0.42, gap=0.32):
        """injury: the words of sentence 1 that name the injury, e.g. 'tore a hole' (hook gate: within the first 12 words)."""
        self.name = name; self.voice, self.rate, self.music_gain = voice, rate, music_gain; self.injury = injury
        if music != 'sneaky_snitch': raise ValueError("music must be 'sneaky_snitch' (the workflow uses assets/music/sneaky_snitch.mp3, Kevin MacLeod, CC BY 4.0)")
        self.music = music
        lines = [l if isinstance(l, (list, tuple)) else (None, l) for l in voice_lines]
        self.lines_text = [str(l[1]).strip() for l in lines]
        self.vo_words = None; self.vo_dur = self._vo_durations()
        t = 0.0; self.vo = []          # vo_trim: line 1 is audible from frame 0 (hook rule: voice onset <= 60 ms)
        for (t0, txt), d in zip(lines, self.vo_dur):
            t = float(t0) if t0 is not None else t
            self.vo.append((round(t, 2), txt)); t = t + d + gap
        self.duration = float(duration) if duration else round(self.vo[-1][0] + self.vo_dur[-1] + 0.15, 2)   # hook rule: cut <= 200 ms after the last word
        self.people = []; self.shots = []; self.extra_sounds = []; self.macros = []; self.errors = []; self.warnings = []
        self._built = False
    def _vo_durations(self):
        f = os.path.join(HERE, self.name + '.vo.json')
        if os.path.exists(f):
            try:
                d = json.load(open(f))
                if d.get('voice') == self.voice and d.get('rate') == self.rate and d.get('lines') == self.lines_text and d.get('trim'):
                    self.vo_words = d.get('words'); return [float(x) for x in d['durations']]
                print('kwkit: vo.json is stale (script changed or old format) - run python3 kwvo.py', self.name + '.py')
            except Exception as e: print('kwkit: bad vo.json', e)
        out = []
        for s in self.lines_text:
            w = len(s.split()); out.append(w / 3.25 + 0.12 * s.count(',') + 0.15)
        return out
    def line(self, i): return self.vo[i][0]
    def words(self):
        """[(start, end, word)] absolute times of every spoken word (real timings from vo.json, else an estimate)"""
        out = []
        for i, (t0, txt) in enumerate(self.vo):
            if self.vo_words: out += [(t0 + a, t0 + b, w) for a, b, w in self.vo_words[i]]
            else:
                ws = txt.split(); r = self.vo_dur[i] / max(1, len(ws)); out += [(t0 + k * r, t0 + (k + 0.9) * r, w) for k, w in enumerate(ws)]
        return out
    def word(self, i, w):
        """start time of word w (text, or index) in sentence i, e.g. ep.word(2, 'cracked') - put a cut or a crack exactly on it"""
        ws = [x for x in self.words() if x[0] >= self.vo[i][0] - 1e-6][:len(self.lines_text[i].split())]
        if isinstance(w, int): return round(ws[w][0], 2)
        key = re.sub(r'[^a-z0-9]', '', w.lower())
        for a, b, x in ws:
            if re.sub(r'[^a-z0-9]', '', x.lower()) == key: return round(a, 2)
        raise ValueError(f'word {w!r} not in sentence {i + 1}')
    def line_end(self, i): return round(self.vo[i][0] + self.vo_dur[i], 2)
    def person(self, name, job, seed, **role):
        """ep.person('Ned', 'civilian', 'ep2-ned', gender='m', age='middle', race='caucasian', build='avg', hair='short02', tee='red')
        jobs: doctor nurse surgeon police paramedic firefighter patient chef 'construction worker' business pilot scientist civilian.
        Extra: tan=0.3 (warmer skin 0..0.6), clipboard=True, mask=True, gloves=True.  The same seed with another job = same face."""
        jobs = ['doctor', 'nurse', 'surgeon', 'police', 'paramedic', 'firefighter', 'patient', 'chef', 'construction worker', 'business', 'pilot', 'scientist', 'civilian']
        _check_name('job', job, jobs)
        a = Actor(self, name, job, seed, role); self.people.append(a); return a
    def macro(self, kind='windpipe', hole=True, label=None):
        """a big close-up tube of tissue: windpipe esophagus artery vein intestine stomach bone nerve sinus.
        hole=True puts a (closed until fx.tear/crack) hole on the camera side."""
        _check_name('macro kind', kind, MACRO_KINDS)
        m = MacroSet(self, kind, hole, len(self.macros), label); self.macros.append(m); return m
    def shot(self, t, name, set, cast=None, cam=None, fx=None, sounds=None, world=None, xray=None, macro=None, organs=None, note=''):
        """t: start second.  set: car | hospital | room | street | studio | xray | macro | graphic.
        cast: {actor: KW.pose(...)} - everyone visible MUST have a pose; people not listed are hidden.
        xray: actor shown as a glass body (set='xray').  organs: organs shown in that x-ray, e.g. ['airway', 'lungs'].
        macro: handle from ep.macro() (set='macro').  sounds: [(local_t, 'name', gain)].  world: override the set's world."""
        _check_name('set', set, SETS)
        if world is not None: _check_name('world', world, WORLDS)
        s = Shot(self, t, name, set, dict(cast or {}), cam, fx, sounds, world, xray, macro, list(organs or []), note)
        for f in s.fx:
            if not isinstance(f, FX): raise TypeError(f'shot {name}: fx items must be KW.fx.*(...), got {f!r}')
            f.shot = s
        self.shots.append(s); self.shots.sort(key=lambda x: x.t)
        for i, x in enumerate(self.shots): x.end = self.shots[i + 1].t if i + 1 < len(self.shots) else self.duration
        return s
    def sound(self, t, name, gain=0.7):
        """an extra foley cue at absolute time t"""
        self.extra_sounds.append((float(t), name, float(gain)))

    # ------------------------------------------------------------------ timeline
    def shot_at(self, t):
        cur = self.shots[0]
        for s in self.shots:
            if t >= s.t: cur = s
        return cur
    def cues_list(self):
        out = []
        for s in self.shots:
            for (lt, nm, g) in s.sounds: out.append((s.t + lt, nm, g))
            for f in s.fx:
                for (lt, nm, g) in f.sounds(): out.append((s.t + lt, nm, g))
            for a, ps in s.cast.items():
                if not isinstance(ps, Pose): continue
                for _, q in ps.keys:
                    for ac in q.acts: out += [(s.t + lt, nm, g) for lt, nm, g in _act_sounds(ac)]
            if s.set == 'car': out.append((s.t, 'engine', 0.5))
        out += self.extra_sounds
        out = sorted(set((round(t, 3), n, round(g, 3)) for t, n, g in out if -0.01 <= t < self.duration))
        return [list(c) for c in out]
    def cues(self):
        return dict(duration=self.duration, fps=FPS, vo=[list(v) for v in self.vo], voice=self.voice, rate=self.rate, cues=self.cues_list(),
                    shots=[[s.t, s.name, s.set] for s in self.shots], music_gain=self.music_gain,
                    vo_trim=True, cap_lead0=True, cap_y=CAP_Y,
                    hook=dict(injury=self.injury or '', inside=[s.name for s in self.shots if s.set in ('xray', 'macro')], loop=self.shots[-1].name if self.shots else None))

    # ------------------------------------------------------------------ guard rails
    def check(self, strict=True):
        """script/timeline guard rails.  Raises SystemExit with every problem listed (strict) or returns the list."""
        E = []; W = []
        words = sum(len(re.findall(r"[A-Za-z0-9']+(?:-[A-Za-z0-9']+)*", l)) for l in self.lines_text)
        if not 68 <= words <= 92: E.append(f'script has {words} words; must be 68-92 (Zack: 69-92)')
        if not 3 <= len(self.lines_text) <= 7: E.append(f'script has {len(self.lines_text)} sentences; must be 3-7 (Zack: 3-6; one per voice line)')
        for i, l in enumerate(self.lines_text):
            if len(re.findall(r'[.!?](\s|$)', l)) != 1 or l[-1:] not in '.!?': E.append(f'voice line {i + 1} must be exactly one sentence ending in . ! or ?: {l!r}')
        for i in range(len(self.vo) - 1):
            if self.vo[i][0] + self.vo_dur[i] > self.vo[i + 1][0] - 0.1: E.append(f'voice line {i + 1} runs into line {i + 2} (start {self.vo[i + 1][0]} too early)')
        n = len(self.shots)
        if not 10 <= n <= 19: E.append(f'{n} shots; need 10-19 for a 22-36 s Short (Zack cuts every 1.5-2.5 s)')
        if self.shots and self.shots[0].t != 0: E.append('first shot must start at 0.0')
        names = [s.name for s in self.shots]
        if len(set(names)) != len(names): E.append('shot names must be unique')
        for s in self.shots:
            L = s.length
            if L > MAX_HOLD + 1e-6: E.append(f'shot {s.name} holds {L:.2f} s (> {MAX_HOLD} s): split it or add a cut')
            if L < 0.6: E.append(f'shot {s.name} is only {L:.2f} s (< 0.6 s)')
            if s.cam is None and not (s.set == 'graphic'): E.append(f'shot {s.name}: no camera (cam=KW.cam.*)')
            if s.cam is not None and not isinstance(s.cam, Cam): E.append(f'shot {s.name}: cam must be KW.cam.*(...)')
            if s.set == 'xray' and not isinstance(s.xray, Actor): E.append(f'shot {s.name}: set=xray needs xray=<person>')
            if s.set == 'xray' and not s.organs: E.append(f'shot {s.name}: set=xray needs organs=[...] (see ORGANS)')
            if s.xray is not None and s.set != 'xray': E.append(f'shot {s.name}: xray= only with set=xray')
            if s.set == 'macro' and not isinstance(s.macro, MacroSet): E.append(f'shot {s.name}: set=macro needs macro=ep.macro(...)')
            for o in s.organs:
                if o not in ORGANS: E.append(f'shot {s.name}: unknown organ {o!r} (valid: {", ".join(ORGANS)})')
            if s.set == 'graphic' and not any(f.is_prop() for f in s.fx): E.append(f'shot {s.name}: set=graphic needs a prop fx (calendar / scan / skin_block / gauge place=station)')
            if s.set in ('xray',) and s.xray is not None and s.xray not in s.cast: E.append(f'shot {s.name}: put the x-ray person in cast with a pose')
            for a, ps in s.cast.items():
                if not isinstance(a, Actor): E.append(f'shot {s.name}: cast keys must be people from ep.person()')
                if not isinstance(ps, Pose): E.append(f'shot {s.name}: {getattr(a, "name", a)} is visible but has no pose (use KW.pose(...))'); continue
                for _, q in ps.keys:
                    try: self.spot_of(s, q)
                    except Exception as e: E.append(f'shot {s.name}: {a.name}: {e}')
                    for side, h in (('left', q.left), ('right', q.right)):
                        if h is None: continue
                        if h.kind == 'wheel' and s.set != 'car': E.append(f'shot {s.name}: {a.name} {side} hand on the wheel outside the car')
                        if h.kind in ('touch',) and isinstance(h.owner, Actor) and h.owner not in s.cast: E.append(f'shot {s.name}: {a.name} touches {h.owner.name}, who is not in the shot')
                        if h.kind == 'clipboard' and not a.role.get('clipboard'): E.append(f'shot {s.name}: {a.name} has no clipboard (ep.person(..., clipboard=True))')
                    if q.base == 'drive' and s.set != 'car': E.append(f'shot {s.name}: base drive only in the car')
                    if q.base == 'lie' and s.set in ('car',): E.append(f'shot {s.name}: nobody lies in the car')
                    for ac in q.acts:
                        if ac.at > s.length + 0.5: W.append(f'shot {s.name}: act {ac.kind} at {ac.at} is after the shot ends ({s.length:.2f})')
            if s.cam is not None and isinstance(s.cam, Cam) and s.cam.subj is not None and isinstance(s.cam.subj, Actor) and s.cam.subj not in s.cast:
                E.append(f'shot {s.name}: camera points at {s.cam.subj.name}, who is not in the cast of this shot')
            for f in s.fx:
                for lt in (f.o.get('at', 0),):
                    if isinstance(lt, (int, float)) and lt > s.length: W.append(f'shot {s.name}: {f} starts after the shot ends')
                if f.kind in ('tear', 'crack', 'leak', 'particles', 'block', 'heal') and s.set != 'macro': E.append(f'shot {s.name}: fx.{f.kind} needs set=macro')
                if f.kind in ('flow', 'pressure', 'glow', 'seal', 'swell_air', 'crack_line') and s.set != 'xray': E.append(f'shot {s.name}: fx.{f.kind} needs set=xray')
        valid = _sound_names()
        for t, nm, g in self.cues_list():
            if any(b in nm.lower() for b in BANNED_SOUNDS): E.append(f'sound {nm!r} at {t}: whoosh-type sounds are banned')
            elif nm not in valid: E.append(f'unknown sound {nm!r} at {t} (valid: {", ".join(sorted(valid))})')
            if not 0 < g <= 1.2: E.append(f'sound {nm} gain {g} out of range')
        if self.shots:
            last, first = self.shots[-1], self.shots[0]
            if not (isinstance(last.cam, Cam) and last.cam.kind == 'loop'): E.append('last shot must use cam=KW.cam.loop() so the Short loops')
            if last.set != first.set: E.append(f'last shot set {last.set!r} must match the first shot set {first.set!r} (loop)')
            if set(a.name for a in last.cast) != set(a.name for a in first.cast): W.append('last shot cast differs from the first shot (loop will jump)')
        if not 22 <= self.duration <= 36: E.append(f'duration {self.duration:.1f} s; must be 22-36 s (Zack: 24-30 s; add words or gap=0.4)')
        for name, ok, why in self.hook_gate():
            if not ok: E.append(f'HOOK {name}: {why}')
        if os.environ.get('KW_HEADS') == 'humgen':   # 4.11 fail loudly: every cast slot needs its HG file (never mix old and new people)
            lib = os.environ.get('KW_HG_LIB', '/tmp/kw-assets/humgen/cast')
            for a in sorted({a for s in self.shots for a in s.cast if isinstance(a, Actor)}, key=lambda a: a.name):
                sl = hg_slot(a.role)
                if not os.path.isfile(os.path.join(lib, sl + '.blend')): E.append(f'KW_HEADS=humgen: {a.name} needs cast slot {sl}.blend, missing in {lib}')
        wv = getattr(self, 'waive', None) or {}     # ep.waive = {'error text start': 'who ruled it and why'} (lead rulings only)
        for e in list(E):
            k = next((k for k in wv if e.startswith(k)), None)
            if k is not None: E.remove(e); W.append(f'WAIVED ({wv[k]}): {e}')
        for e in E: print('CHECK ERROR:', e)
        for w in W: print('check warning:', w)
        self.errors, self.warnings = E, W
        if E and strict: raise SystemExit(f'ep.check() failed with {len(E)} problem(s) - fix them (see CHECK ERROR lines)')
        if not E: print(f'ep.check() OK: {words} words, {len(self.lines_text)} sentences, {n} shots, {self.duration:.1f} s')
        return E

    def hook_gate(self):
        """the automatable part of the 10-point hook gate (research/hook_spec.md) -> [(item, ok, detail)].
        The picture items are checked on rendered frames by `python3 kwhook.py gate ep_x.py <frames>`."""
        R = []; s1 = self.lines_text[0]; toks = [re.sub(r'[^a-z0-9]', '', w.lower()) for w in s1.split()]
        inj = [re.sub(r'[^a-z0-9]', '', w.lower()) for w in (self.injury or '').split()]
        at = next((i for i in range(len(toks)) if inj and toks[i:i + len(inj)] == inj), None)
        R.append(('injury named in sentence 1 within 12 words', at is not None and at + len(inj) <= 12,
                  'give KW.Episode(..., injury="<words of sentence 1 naming the injury>")' if not inj else f'{self.injury!r} ends at word {None if at is None else at + len(inj)}'))
        bad = [f for f in HOOK_FILLER if f in s1.lower()]
        R.append(('no filler in sentence 1', not bad, f'remove {bad} (context such as "while driving" goes in sentence 2)'))
        R.append(('sentence 1 is 8-24 words', 8 <= len(toks) <= 24, f'{len(toks)} words (Zack opens with a 20+ word run-on; time its shots with ep.word(0, ...))'))
        W = self.words(); n03 = sum(1 for a, b, w in W if a < 3.0)
        R.append(('8-11 words spoken in 0-3 s', 8 <= n03 <= 11, f'{n03} words start before 3.0 s (sentence 1 must end by about 3 s; start sentence 2 after 3.0 s)'))
        st = [s.t for s in self.shots]
        if len(st) > 2:
            ins = [s.t for s in self.shots if s.set in ('xray', 'macro')]
            R.append(('first shot <= 1.1 s', st[1] <= 1.1 + 1e-6, f'first cut at {st[1]:.2f} s'))
            R.append(('>= 2 cuts before 3.0 s', sum(1 for t in st[1:] if t < 3.0) >= 2, f'cuts at {[t for t in st[1:] if t < 3.0]}'))
            R.append(('inside the body (xray/macro) by 1.2 s', bool(ins) and min(ins) <= 1.2 + 1e-6, f'first xray/macro shot at {min(ins) if ins else None}'))
            R.append(('3rd shot (consequence) starts by 2.4 s', st[2] <= 2.4 + 1e-6, f'third shot at {st[2]:.2f} s'))
            R.append(('frame-0 shot shows a person (not xray/macro/graphic)', self.shots[0].set not in ('xray', 'macro', 'graphic') and bool(self.shots[0].cast), self.shots[0].set))
        cs = self.cues_list(); tr = [(t, n) for t, n, g in cs if t <= 0.08 and n in HOOK_TRANSIENTS]
        R.append(('foley transient at 0-80 ms', bool(tr), 'add ep.sound(0.0, "thud", 1.0) (or pinch/rip/crackle/bounce)' if not tr else str(tr)))
        last = max(b for a, b, w in W) if W else 0; tail = self.duration - last
        R.append(('cut <= 200 ms after the last word', -0.01 <= tail <= 0.2 + 1e-6, f'last word ends {last:.2f} s, video {self.duration:.2f} s (leave duration=None)'))
        return R

    def spot_of(self, shot, q):
        """-> (set, spot name, spot tuple)"""
        at = q.at
        if at is None:
            dflt = {'car': 'driver', 'hospital': 'bed_sit', 'room': 'desk' if q.base == 'sit' else 'stand', 'street': 'bench' if q.base == 'sit' else 'walk',
                    'studio': 'centre_sit' if q.base == 'sit' else 'centre', 'xray': None, 'macro': None, 'graphic': None}[shot.set]
            if dflt is None: raise ValueError(f'pose needs at="set.spot" in an {shot.set} shot (e.g. at="studio.centre" or "car.driver")')
            at = dflt
        if '.' in at: st, sp = at.split('.', 1)
        else:
            st = shot.set if shot.set in SPOTS else None; sp = at
            if st is None: raise ValueError(f'in {shot.set} shots give at as "set.spot", e.g. "studio.centre"')
        if st not in SPOTS: raise ValueError(f'unknown set {st!r} in at={at!r}')
        if sp not in SPOTS[st]: raise ValueError(f'unknown spot {sp!r} for set {st}; valid: {", ".join(SPOTS[st])}')
        kind = SPOTS[st][sp][0]
        if q.base in ('sit', 'drive') and kind != 'seat': raise ValueError(f'base {q.base} needs a seat spot; {st}.{sp} is {kind}')
        if q.base in ('stand', 'walk') and kind not in ('stand', 'stand_near'): raise ValueError(f'base {q.base} needs a standing spot; {st}.{sp} is {kind}')
        if q.base == 'lie' and kind != 'lie': raise ValueError(f'base lie needs a lying spot (hospital.bed_lie, street.ground); got {st}.{sp}')
        return st, sp, SPOTS[st][sp]

    # ------------------------------------------------------------------ entry point
    def run(self):
        argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
        strict = not os.environ.get('KW_NOCHECK')
        if '--cues' in argv:
            self.check(strict=strict); json.dump(self.cues(), open(argv[-1], 'w'), indent=1); print('cues written', argv[-1]); sys.exit(0)
        if bpy is None:
            self.check(strict=False); return
        self.check(strict=strict)
        import kwrun
        kwrun.Runtime(self).main(argv)

def _act_sounds(ac):
    k, a = ac.kind, ac.at
    if k == 'sneeze': return [(a - 0.55, 'inhale', 0.8), (a, 'sneeze', 1.0)]
    if k == 'cough': return [(a + i * ac.kw.get('gap', 0.45), 'puff', 0.8) for i in range(int(ac.kw.get('n', 3)))]
    if k == 'blow_nose': return [(a, 'inhale', 0.5), (a + 0.35, 'puff', 0.9), (a + 0.4, 'rush', 0.6)]
    if k == 'sniff': return [(a, 'sniff', 0.8)]
    if k == 'gasp': return [(a, 'inhale', 0.7)]
    if k == 'flinch': return [(a, 'thud', 0.4)]
    return []

# ===================================================================================== plain-python check:  python3 kwkit.py --check ep_x.py
if __name__ == '__main__' and bpy is None:
    if len(sys.argv) >= 3 and sys.argv[1] == '--check':
        sys.argv = [sys.argv[2]]
        src = open(sys.argv[0]).read(); g = {'__name__': '__main__', '__file__': os.path.abspath(sys.argv[0])}
        exec(compile(src, sys.argv[0], 'exec'), g)
    else: print(__doc__)
