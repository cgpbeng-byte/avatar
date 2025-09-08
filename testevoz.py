# teste_vosk_ptbr_big.py
import os, time, json
import sounddevice as sd
from vosk import Model, KaldiRecognizer

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = 'int16'
DURACAO = 8  # segundos

# >>> AJUSTE AQUI: caminho completo da pasta do modelo grande (descompactada)
MODEL_DIR = "vosk-model-small-pt-0.3"

if not os.path.isdir(MODEL_DIR):
    raise RuntimeError(f"Modelo não encontrado: {MODEL_DIR}")

print(f"[VOSK] Carregando modelo grande de: {MODEL_DIR}")
model = Model(MODEL_DIR)
rec = KaldiRecognizer(model, SAMPLE_RATE)
rec.SetWords(True)

print("🎤 Gravando; fale normalmente (8s).")
with sd.RawInputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype=DTYPE) as stream:
    t0 = time.time()
    while time.time() - t0 < DURACAO:
        frames = int(SAMPLE_RATE * 0.25)
        data, _ = stream.read(frames)
        if rec.AcceptWaveform(bytes(data)):
            r = json.loads(rec.Result())
            if r.get("text"):
                print("[resultado]:", r["text"])
        else:
            p = json.loads(rec.PartialResult()).get("partial") or ""
            if p:
                print("[parcial]:", p)

final = json.loads(rec.FinalResult())
texto = (final.get("text") or "").strip()
print("\n=== Final ===")
print(texto if texto else "(vazio)")
