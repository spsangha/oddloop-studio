"""Casting for Kinda Wild Films: a new, story-fitting person every episode (Zack D. Films style).

cast(role, seed) -> kwargs for person.build_person. Same seed = same person (stable across render shards).
role: dict with any of gender ('m'|'f'), age ('kid'|'teen'|'young'|'middle'|'old'), race ('african'|'asian'|'caucasian'|'mixed'),
      build ('slim'|'avg'|'heavy'|'muscular'), hair, tee, outfit. Anything left out is picked from the seed.
"""
import os, random

MP_T = None  # set lazily from person.MP
FACE_GROUPS = {  # target folder -> (count to pick, max weight)
    'nose': (3, 0.7), 'chin': (2, 0.7), 'mouth': (2, 0.5), 'eyes': (3, 0.5), 'head': (2, 0.5),
    'cheek': (1, 0.5), 'ears': (1, 0.5), 'forehead': (1, 0.5), 'eyebrows': (1, 0.5)}
AGE = {'kid': 0.12, 'teen': 0.3, 'young': 0.5, 'middle': 0.68, 'old': 0.9}
SKIN_AGE = {'kid': 'young', 'teen': 'young', 'young': 'young', 'middle': 'middleage', 'old': 'old'}
RACE = {'african': (1.0, 0.0, 0.0), 'asian': (0.0, 1.0, 0.0), 'caucasian': (0.0, 0.0, 1.0)}
HAIR_M = ['short01', 'short02', 'short03', 'short04', 'afro01', None]
HAIR_F = ['bob01', 'bob02', 'long01', 'ponytail01', 'braid01', 'afro01']
TEES = ['teal', 'white', 'red', 'navy', 'mustard', 'grey', 'maroon', 'olive', 'orange', 'black', 'skyblue']
BUILD = {'slim': (0.3, 0.4), 'avg': (0.5, 0.5), 'heavy': (0.85, 0.45), 'muscular': (0.5, 0.85)}


def _targets(mp):
    out = {}
    for g in FACE_GROUPS:
        d = os.path.join(mp, 'targets', g)
        out[g] = sorted(f[:-10] for f in os.listdir(d) if f.endswith('.target.gz')) if os.path.isdir(d) else []
    return out


def cast(role=None, seed=0, mp=None):
    r = random.Random(f'kw-{seed}')
    role = dict(role or {})
    g = role.get('gender') or r.choice('mf')
    age = role.get('age') or r.choice(['young', 'young', 'middle', 'middle', 'old'])
    race = role.get('race') or r.choice(['african', 'asian', 'caucasian', 'caucasian', 'mixed'])
    if race == 'mixed':
        a, b = r.sample(list(RACE), 2); w = r.uniform(0.35, 0.65)
        rv = tuple(RACE[a][i] * w + RACE[b][i] * (1 - w) for i in range(3)); skin_r = a if w >= 0.5 else b
    else:
        rv = RACE[race]; skin_r = race
    wgt, mus = BUILD[role.get('build') or r.choice(['slim', 'avg', 'avg', 'heavy', 'muscular'])]
    sex = 'male' if g == 'm' else 'female'
    skin = f"{SKIN_AGE[age]}_{skin_r}_{sex}"
    if g == 'm':
        hair = role.get('hair', r.choice(HAIR_M if age != 'old' else ['short01', 'short02', None]))
        clothes = ('male_casualsuit04', 'shoes01')
    else:
        hair = role.get('hair', r.choice(HAIR_F))
        clothes = ('male_casualsuit04', 'shoes01')  # logo-free tee works on both bodies
    hv = {'african': 0.18, 'asian': 0.2}.get(skin_r, r.choice([0.2, 0.35, 0.55, 0.8]))
    if age == 'old': hv = r.choice([1.8, 2.2, 2.6])  # grey/white
    extra = []
    if mp:
        T = _targets(mp)
        for grp, (n, mx) in FACE_GROUPS.items():
            for t in r.sample(T[grp], min(n, len(T[grp]))):
                extra.append((f'{grp}/{t}', round(r.uniform(0.15, mx), 2)))
    return dict(gender=1.0 if g == 'm' else 0.0, age=AGE[age], weight=wgt, muscle=mus, height=r.uniform(0.4, 0.6) if age != 'kid' else 0.2,
                race=rv, skin=skin, eyes=r.choice(['brown', 'brown', 'blue', 'green', 'lightblue']) if skin_r == 'caucasian' else 'darkbrown',
                hair=hair, brows=f'eyebrow{r.randint(1, 12):03d}', clothes=role.get('outfit', clothes), tee=role.get('tee') or r.choice(TEES),
                hair_value=hv, extra_targets=tuple(extra))
