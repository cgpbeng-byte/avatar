import tkinter as tk
import requests
import pyttsx3
import pygame
import time
import threading

# === CONFIGURAÇÕES ===
LARGURA, ALTURA = 640, 480
COR_FUNDO = (255, 255, 255)
COR_BOCA_FECHADA = (0, 128, 0)
COR_BOCA_ABERTA = (0, 255, 0)
VELOCIDADE_FALA = 150
ARQUIVO_AUDIO = "resposta.wav"

# === INICIALIZAÇÕES ===
pygame.init()
pygame.mixer.init()
screen = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Papagaio Virtual Offline")

engine = pyttsx3.init()
engine.setProperty('rate', VELOCIDADE_FALA)

boca_fechada = pygame.Surface((200, 200))
boca_fechada.fill(COR_BOCA_FECHADA)

boca_aberta = pygame.Surface((200, 200))
boca_aberta.fill(COR_BOCA_ABERTA)

# === FUNÇÃO DE RESPOSTA COM IA LOCAL ===
def gerar_resposta(texto):
    prompt = f"Responda em uma só frase, seja direto e objetivo: {texto}"
    try:
        resposta = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False
            }
        )
        return resposta.json()["response"].strip()
    except Exception as e:
        return f"Erro ao gerar resposta: {e}"

# === FUNÇÃO DE ANIMAÇÃO ===
def animar_boca():
    clock = pygame.time.Clock()
    animando = True
    estado_boca = True
    ultimo_tempo = time.time()

    while animando:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                animando = False

        screen.fill(COR_FUNDO)

        if time.time() - ultimo_tempo > 0.3:
            estado_boca = not estado_boca
            ultimo_tempo = time.time()

        boca = boca_aberta if estado_boca else boca_fechada
        screen.blit(boca, (220, 140))

        pygame.display.flip()
        clock.tick(30)

        if not pygame.mixer.music.get_busy():
            animando = False

# === FUNÇÃO DE RESPOSTA COMPLETA ===
def responder(texto):
    resposta = gerar_resposta(texto)
    print("Resposta:", resposta)
    rotulo_resposta.config(text=resposta)

    # Gera áudio da resposta
    engine.save_to_file(resposta, ARQUIVO_AUDIO)
    engine.runAndWait()

    # Reproduz áudio e anima boca em paralelo
    def reproduzir_e_animar():
        pygame.mixer.music.load(ARQUIVO_AUDIO)
        pygame.mixer.music.play()
        animar_boca()

    threading.Thread(target=reproduzir_e_animar).start()

# === INTERFACE TKINTER ===
def iniciar_resposta():
    texto = entrada.get()
    rotulo_resposta.config(text="Gerando resposta...")
    threading.Thread(target=responder, args=(texto,)).start()

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
