import tkinter as tk
import requests

# === FUNÇÃO DE RESPOSTA COM IA LOCAL ===
def gerar_resposta(texto):
    prompt = f"Responda em uma só frase, {texto}"
    try:
        resposta = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            }
        )
        return resposta.json()["response"]
    except Exception as e:
        return f"Erro ao gerar resposta: {e}"

# === FUNÇÃO DE RESPOSTA ===
def responder(texto):
    resposta = gerar_resposta(texto)
    print(resposta)
    rotulo_resposta.config(text=resposta)

# === INTERFACE TKINTER ===
def iniciar_resposta():
    texto = entrada.get()
    rotulo_resposta.config(text="Gerando resposta...")
    responder(texto)

janela = tk.Tk()
janela.title("Papagaio Offline com IA")
janela.geometry("500x250")

tk.Label(janela, text="Digite sua pergunta:").pack(pady=10)
entrada = tk.Entry(janela, width=60)
entrada.pack(pady=5)

tk.Button(janela, text="Perguntar", command=iniciar_resposta).pack(pady=10)

rotulo_resposta = tk.Label(janela, text="", wraplength=480, justify="left")
rotulo_resposta.pack(pady=10)

janela.mainloop()
