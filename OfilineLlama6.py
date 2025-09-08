import tkinter as tk
import threading
import queue
import time
import os
import pygame
import pyttsx3
from queue import Empty

# ===== CONFIGS =====
LARGURA, ALTURA = 640, 480
COR_FUNDO = (135, 206, 235)
COR_BOCA_FECHADA = (0, 0, 0)
COR_BOCA_ABERTA = (255, 0, 0)

# ===== ENGINE TTS =====
engine = pyttsx3.init()
engine.setProperty("rate", 150)

# ===== FILAS =====
anim_queue = queue.Queue()
ocupado = False
worker_running = True

# ===== GERAR RESPOSTA (simples p/ testes) =====
def gerar_resposta_com_memoria(texto):
    return f"Você perguntou: {texto}. Esta é a resposta do papagaio."

# ===== ANIMAÇÃO (janela única) =====
def anim_worker():
    pygame.init()
    pygame.display.init()
    pygame.mixer.init()

    screen = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption("Papagaio Virtual")

    boca_fechada = pygame.Surface((200, 200))
    boca_fechada.fill(COR_BOCA_FECHADA)
    boca_aberta = pygame.Surface((200, 200))
    boca_aberta.fill(COR_BOCA_ABERTA)

    clock = pygame.time.Clock()
    estado_boca = False
    ultimo_tempo = time.time()
    rodando = True
    tocando = False

    while worker_running and rodando:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                rodando = False

        screen.fill(COR_FUNDO)

        # Se chegou áudio novo
        try:
            caminho_audio = anim_queue.get_nowait()
            if caminho_audio:
                try:
                    pygame.mixer.music.load(caminho_audio)
                    pygame.mixer.music.play()
                    tocando = True
                except Exception as e:
                    print(f"[ERRO] Não consegui tocar áudio: {e}")
        except Empty:
            pass

        # Atualiza boca só se tiver áudio tocando
        if tocando:
            if pygame.mixer.music.get_busy():
                if time.time() - ultimo_tempo > 0.3:
                    estado_boca = not estado_boca
                    ultimo_tempo = time.time()
            else:
                tocando = False
                estado_boca = False
                print("[INFO] Áudio terminou.")
        else:
            estado_boca = False

        boca = boca_aberta if estado_boca else boca_fechada
        screen.blit(boca, (220, 140))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()

# ===== FUNÇÃO RESPOSTA =====
def responder(texto: str):
    global ocupado
    if ocupado:
        return
    ocupado = True
    try:
        resposta = gerar_resposta_com_memoria(texto)

        janela.after(0, lambda: rotulo_resposta.config(text=resposta))

        if resposta.startswith("Erro ao gerar resposta:"):
            return

        nome_arquivo = f"resposta_{int(time.time()*1000)}.wav"
        engine.save_to_file(resposta, nome_arquivo)
        engine.runAndWait()

        anim_queue.put(nome_arquivo)

    finally:
        janela.after(0, lambda: (btn_perguntar.config(state=tk.NORMAL),
                                 entrada.config(state=tk.NORMAL)))
        ocupado = False

# ===== THREADS =====
anim_thread = threading.Thread(target=anim_worker, daemon=True)
anim_thread.start()

# ===== TKINTER =====
janela = tk.Tk()
janela.title("Papagaio Virtual")

entrada = tk.Entry(janela, width=40)
entrada.pack(pady=10)

rotulo_resposta = tk.Label(janela, text="", wraplength=400, justify="left")
rotulo_resposta.pack(pady=10)

def on_click():
    global ocupado
    if not ocupado:
        texto = entrada.get()
        if texto.strip():
            btn_perguntar.config(state=tk.DISABLED)
            entrada.config(state=tk.DISABLED)
            threading.Thread(target=responder, args=(texto,), daemon=True).start()

btn_perguntar = tk.Button(janela, text="Perguntar", command=on_click)
btn_perguntar.pack(pady=10)

janela.protocol("WM_DELETE_WINDOW", janela.quit)
janela.mainloop()

worker_running = False
anim_thread.join()
