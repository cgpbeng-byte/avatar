import tkinter as tk
# import pyttsx3  # Comentado: usado para gerar áudio
# import pygame  # Comentado: usado para animação e reprodução de áudio
# import time
# import threading

# === CONFIGURAÇÕES ===
# LARGURA, ALTURA = 640, 480
# COR_FUNDO = (255, 255, 255)
# COR_BOCA_FECHADA = (0, 128, 0)
# COR_BOCA_ABERTA = (0, 255, 0)
# VELOCIDADE_FALA = 150
# ARQUIVO_AUDIO = "resposta.wav"

# === INICIALIZAÇÕES ===
# pygame.init()
# pygame.mixer.init()
# screen = pygame.display.set_mode((LARGURA, ALTURA))
# pygame.display.set_caption("Papagaio Virtual Offline")

# engine = pyttsx3.init()
# engine.setProperty('rate', VELOCIDADE_FALA)

# === ELEMENTOS VISUAIS ===
# boca_fechada = pygame.Surface((200, 200))
# boca_fechada.fill(COR_BOCA_FECHADA)

# boca_aberta = pygame.Surface((200, 200))
# boca_aberta.fill(COR_BOCA_ABERTA)

# === FUNÇÃO DE RESPOSTA ===
def responder(texto):
    resposta = f"Você perguntou: {texto}. Isso é muito interessante!"
    print(resposta)
    
    # engine.save_to_file(resposta, ARQUIVO_AUDIO)
    # engine.runAndWait()

    # pygame.mixer.music.load(ARQUIVO_AUDIO)
    # pygame.mixer.music.play()

    # animar_boca()

# === INTERFACE TKINTER ===
def iniciar_resposta():
    texto = entrada.get()
    # thread = threading.Thread(target=responder, args=(texto,))
    # thread.start()
    responder(texto)  # Chamada direta sem thread
janela = tk.Tk()
janela.title("Papagaio Offline")
janela.geometry("400x150")

tk.Label(janela, text="Digite sua pergunta:").pack(pady=10)
entrada = tk.Entry(janela, width=50)
entrada.pack(pady=5)

tk.Button(janela, text="Perguntar", command=iniciar_resposta).pack(pady=10)

janela.mainloop()
