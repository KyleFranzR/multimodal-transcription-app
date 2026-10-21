import sounddevice as sd
import numpy as np

print("Default input:", sd.default.device[0])
print("Magsalita nang tuloy-tuloy habang tumatakbo ito...\n")
for i, d in enumerate(sd.query_devices()):
    if d["max_input_channels"] < 1:
        continue
    try:
        rate = int(d["default_samplerate"])
        rec = sd.rec(int(rate * 2), samplerate=rate, channels=1, dtype="int16", device=i)
        sd.wait()
        print(f"[{i}] peak={int(np.abs(rec).max()):6d}  {d['name']}")
    except Exception as exc:
        print(f"[{i}] ERROR {exc}  {d['name']}")