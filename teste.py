import tkinter as tk
import pyttsx3
import pygame
import time
import threading

# Inicializa Pygame
pygame.init()
pygame.mixer.init()
largura, altura = 640, 480
screen = pygame.display.set_mode((largura, altura))
pygame.display.set_caption("Papagaio Virtual Offline")

# Cores e imagens
branco = (255, 255, 255)
boca_fechada = pygame.Surface((200, 200))
boca_fechada.fill((0, 128, 0))
boca_aberta = pygame.Surface((200, 200))
boca_aberta.fill((0, 255, 0))

# Inicializa o sintetizador de voz offline
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # velocidade da fala

# Função para gerar resposta e animar o papagaio
def responder(texto):
    resposta = f"Você perguntou: {texto}. Isso é muito interessante!"

    # Salva como WAV diretamente
    engine.save_to_file(resposta, "resposta.wav")
    engine.runAndWait()

    # Reproduz o áudio
    pygame.mixer.music.load("resposta.wav")
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
janela.title("Papagaio Offline")
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
