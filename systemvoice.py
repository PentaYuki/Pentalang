#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from voicevox.voicevox_engine import VoicevoxEngine, SynthParams

SYSTEM_LINES = [
    "ねえねえ、ちょっと不思議な質問があるんだけど...",
    "ねえ、ちょっとミステリアスなこと聞いてもいい？",
    "ね、秘密の質問があるよ！",
    "ちょっと気になることあるんだけど、いいかな？",
]


def build_system_wavs(app_root: Path, force: bool = True) -> int:
    voicevox_root = app_root / "voicevox"
    out_dir = app_root / "voice" / "system"
    out_dir.mkdir(parents=True, exist_ok=True)

    engine = VoicevoxEngine(str(voicevox_root))
    models = engine.scan_models()
    if not models:
        raise RuntimeError("VoiceVox model list is empty. Check voicevox_core and model files.")

    vvm = models[0]["vvm"]
    name = models[0].get("name", "unknown")
    print(f"Using model: {name} ({vvm})")

    params = SynthParams(speed=1.0, pitch=0.0, intonation=1.05, volume=1.0, style_idx=0)

    written = 0
    for i, text in enumerate(SYSTEM_LINES, start=1):
        out_path = out_dir / f"system_ai_q_{i}.wav"
        if out_path.exists() and not force:
            print(f"Skip existing: {out_path}")
            continue

        wav = engine.get_audio(text, vvm, params)
        if not wav:
            raise RuntimeError(f"VoiceVox returned empty wav for line {i}: {text}")

        out_path.write_bytes(wav)
        print(f"Wrote: {out_path}")
        written += 1

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Japanese system voice wav files with VoiceVox.")
    parser.add_argument("--no-force", action="store_true", help="Do not overwrite existing wav files")
    parser.add_argument("--app-root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()

    count = build_system_wavs(args.app_root, force=not args.no_force)
    print(f"Done. Files written: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
