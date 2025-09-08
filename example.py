import tkinter as tk
from transformers import pipeline
from gtts import gTTS
import pygame
import time
import threading
import ssl
import urllib.request

ssl._create_default_https_context = ssl._create_unverified_context

from transformers import pipeline
generator = pipeline("text-generation", model="distilgpt2")



# Inicializa o modelo leve
gerador = pipeline("text-generation", model="distilgpt2")

# Inicializa Pygame
pygame.init()
pygame.mixer.init()
largura, altura = 640, 480
screen = pygame.display.set_mode((largura, altura))
pygame.display.set_caption("Papagaio Virtual com Tkinter")

# Cores e imagens
branco = (255, 255, 255)
boca_fechada = pygame.Surface((200, 200))
boca_fechada.fill((0, 128, 0))
boca_aberta = pygame.Surface((200, 200))
boca_aberta.fill((0, 255, 0))

# Função para gerar resposta e animar o papagaio
def responder(texto):
    resposta = gerador(texto, max_length=50)[0]['generated_text']
    tts = gTTS(text=resposta, lang='pt')
    tts.save("resposta.mp3")
    pygame.mixer.music.load("resposta.mp3")
    pygame.mixer.music.play()

    clock = pygame.time.Clock()
    animando = True
    estado_boca = True
    ultimo_tempo = time.time()

    while animando:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                animando = False

        screen.fill(branco)

        if time.time() - ultimo_tempo > 0.3:
            estado_boca = not estado_boca
            ultimo_tempo = time.time()

        if estado_boca:
            screen.blit(boca_fechada, (220, 140))
        else:
            screen.blit(boca_aberta, (220, 140))

        pygame.display.flip()
        clock.tick(30)

        if not pygame.mixer.music.get_busy():
            animando = False

# Interface Tkinter
janela = tk.Tk()
janela.title("Pergunte ao Papagaio")
janela.geometry("400x150")

label = tk.Label(janela, text="Digite sua pergunta:")
label.pack(pady=10)

entrada = tk.Entry(janela, width=50)
entrada.pack(pady=5)

# Função para iniciar resposta em thread
def iniciar_resposta():
    texto = entrada.get()
    thread = threading.Thread(target=responder, args=(texto,))
    thread.start()

botao = tk.Button(janela, text="Perguntar", command=iniciar_resposta)
botao.pack(pady=10)

janela.mainloop()
