# Odd Loop Studio

Render code for the Odd Loop 3D cartoon Shorts. Blender (Cycles, CPU) renders each episode in parallel GitHub Actions shards; a finishing job adds impact words, cartoon foley and music.

- `loop/b3d/toon.py`: materials and shape helpers
- `loop/b3d/humans.py`, `cast.py`: characters, posed every frame by code
- `loop/b3d/set_*.py`: sets
- `loop/b3d/ep_*.py`: episodes (pushing one renders it)
- `loop/b3d/post.py`: frames + sound effects + music to the final MP4

## Credits
- Music: "Sneaky Snitch" Kevin MacLeod (incompetech.com), CC BY 4.0, http://creativecommons.org/licenses/by/4.0/
- Fonts: Luckiest Guy and Fredoka, SIL Open Font License 1.1
