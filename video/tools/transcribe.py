"""Transcribe the recording's audio track with Whisper (local, CPU). Writes <wav>.transcript.json + .txt"""
import json, sys
import numpy as np, soundfile as sf, whisper
wav = sys.argv[1]
audio, sr = sf.read(wav, dtype="float32")
assert sr == 16000, sr
if audio.ndim > 1: audio = audio.mean(axis=1)
model = whisper.load_model(sys.argv[2] if len(sys.argv) > 2 else "small")
res = model.transcribe(audio, fp16=False, verbose=False)
out = wav.rsplit(".", 1)[0]
json.dump(res, open(out + ".transcript.json", "w"), ensure_ascii=False, indent=1)
with open(out + ".transcript.txt", "w") as f:
    for s in res["segments"]:
        f.write(f"[{s['start']:7.1f} - {s['end']:7.1f}] {s['text'].strip()}\n")
print("language:", res.get("language"), "| segments:", len(res["segments"]))
print(open(out + ".transcript.txt").read()[:4000])
