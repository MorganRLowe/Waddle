"""
split_gif.py — cut a single GIF into labelled sections
Usage:  python split_gif.py

Edit SECTIONS below to define how to split your recording.
Each entry:  ("output_filename.gif", start_frame, end_frame)
Use end_frame=None to mean "until the end".
Run with no args — reads 'full.gif' and writes each section next to it.
"""

from PIL import Image
import os

INPUT  = r"C:\Users\Lenovo\OneDrive\Desktop\fullone.gif"
RESIZE = None   # keep original resolution

SECTIONS = [
    ("animation.gif", 3,    277),
    ("Dodge.gif",     279,  649),
    ("code.gif",      680,  1012),
    ("weather.gif",   1046, 1209),
]
# ─────────────────────────────────────────────────────────────────────────────

def load_frames(path):
    img = Image.open(path)
    frames = []
    durations = []
    try:
        while True:
            frames.append(img.copy().convert("RGBA"))
            durations.append(img.info.get("duration", 80))
            img.seek(img.tell() + 1)
    except EOFError:
        pass
    return frames, durations

def save_gif(frames, durations, path, resize=None):
    out = []
    for f, d in zip(frames, durations):
        if resize:
            f = f.resize(resize, Image.LANCZOS)
        out.append(f.convert("RGBA"))
    out[0].save(
        path,
        save_all=True,
        append_images=out[1:],
        duration=durations[:len(out)],
        loop=0,
        format="GIF",
        optimize=False,
    )
    print(f"  saved {path}  ({len(out)} frames)")

def main():
    if not os.path.exists(INPUT):
        print(f"ERROR: '{INPUT}' not found. Drop your full recording here and rename it full.gif")
        return

    print(f"Loading {INPUT} ...")
    frames, durations = load_frames(INPUT)
    print(f"  {len(frames)} frames total")

    for name, start, end in SECTIONS:
        end = end if end is not None else len(frames)
        chunk_frames    = frames[start:end]
        chunk_durations = durations[start:end]
        if not chunk_frames:
            print(f"  SKIP {name} — empty range [{start}:{end}]")
            continue
        print(f"Saving {name}  frames [{start}:{end}] ...")
        save_gif(chunk_frames, chunk_durations, name, resize=RESIZE)

    print("Done!")

if __name__ == "__main__":
    main()
