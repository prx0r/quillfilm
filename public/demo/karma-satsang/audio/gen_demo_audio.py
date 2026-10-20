#!/usr/bin/env python3
"""Generate demo satsang audio via Fish Audio (free tier s2.1-pro-free).
Usage: FISH_API_KEY=... python3 gen_demo_audio.py   (writes mp3s next to script)
Lines are short to respect the free tier. Rerun is idempotent (skips existing)."""
import json
import os
import time
import urllib.request

API = "https://api.fish.audio/v1/tts"
MODEL = "s2.1-pro-free"
HERE = os.path.dirname(os.path.abspath(__file__))

VOICES = {
    "narrator": "fb015415ebf141999fc882baa0e0834c",   # louis
    "skeptic": "dbeb1d68566245e2b857617b830e8031",    # ari
    "wonderer": "9c36c951cee84457a5cc9f94387e9a42",    # casey
}

LINES = [
    ("narr1", "narrator", "Same act. Opposite payoffs. One man garlanded like a king for killing. Another marched to the drum for the same deed. If karma is true, the books balance somewhere you cannot see."),
    ("skep1", "skeptic", "[curious] So you're saying I was Hitler? And the dog that saved my life was my mother?"),
    ("narr2", "narrator", "Every role has been occupied. No one is essentially anything. That is not an insult. It is the mechanism."),
    ("wond1", "wonderer", "[soft] But I don't remember being anyone's mother. How is this useful now?"),
    ("narr3", "narrator", "You don't remember being an infant either. Memory is not the criterion. The affection is the work."),
    ("skep2", "skeptic", "[provocative] And if everyone is my mother — what about sex?"),
    ("narr4", "narrator", "Relate to people as they are. The mother-view generates care; it makes no claims about your relationships. The tradition never asked you to stop seeing what is in front of you."),
]


def synth(name, voice, text, key):
    out = os.path.join(HERE, f"{name}.mp3")
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        print(f"skip {name} (exists)")
        return
    body = {"text": text, "format": "mp3", "reference_id": VOICES[voice]}
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "model": MODEL})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    with open(out, "wb") as f:
        f.write(data)
    print(f"wrote {name}.mp3 ({len(data)} bytes)")


def main():
    key = os.environ.get("FISH_API_KEY", "")
    if not key:
        raise SystemExit("FISH_API_KEY missing")
    for name, voice, text in LINES:
        synth(name, voice, text, key)
        time.sleep(2)


if __name__ == "__main__":
    main()
