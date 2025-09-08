import os
import time
import threading
import tkinter as tk
import requests
import pyttsx3
import pygame

# === CONFIGURAÇÕES ===
LARGURA, ALTURA = 640, 480
COR_FUNDO = (255, 255, 255)
COR_BOCA_FECHADA = (0, 128, 0)
COR_BOCA_ABERTA = (0, 255, 0)
VELOCIDADE_FALA = 150

OLLAMA_URL_CHAT = "http://localhost:11434/api/chat"  # usa /api/chat para manter histórico
MODELO = "mistral"  # ajuste se estiver usando outro modelo no Ollama

# === ESTADO GLOBAL ===
historico = [
    {"role": "system", "content": "Responda em português do Brasil. Em uma única frase, direto e objetivo."}
]
ocupado = False  # evita concorrência entre perguntas

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


# === FUNÇÃO DE RESPOSTA COM IA (com memória) ===
def gerar_resposta_com_memoria(texto_usuario: str) -> str:
    """
    Usa /api/chat do Ollama, mantendo 'historico' (lista de mensagens).
    """
    global historico
    historico.append({"role": "user", "content": texto_usuario})

    try:
        resp = requests.post(
            OLLAMA_URL_CHAT,
            json={
                "model": MODELO,
                "messages": historico,
                "stream": False
            },
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()

        # Estrutura típica do /api/chat do Ollama: data["message"]["content"]
        resposta = data.get("message", {}).get("content", "").strip()
        if not resposta:
            resposta = "Não consegui gerar uma resposta agora."

        # Anexa resposta ao histórico para manter contexto
        historico.append({"role": "assistant", "content": resposta})
        return resposta

    except Exception as e:
        return f"Erro ao gerar resposta: {e}"


# === FUNÇÃO DE ANIMAÇÃO ===
def animar_boca():
    """
    Anima a boca alternando aberta/fechada enquanto o áudio estiver tocando.
    Sai quando a música terminar.
    """
    clock = pygame.time.Clock()
    animando = True
    estado_boca = True
    ultimo_tempo = time.time()

    while animando:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                animando = False

        screen.fill(COR_FUNDO)

        # alterna a cada 0,3s para simular fala
        if time.time() - ultimo_tempo > 0.3:
            estado_boca = not estado_boca
            ultimo_tempo = time.time()

        boca = boca_aberta if estado_boca else boca_fechada
        screen.blit(boca, (220, 140))

        pygame.display.flip()
        clock.tick(30)

        # encerra quando terminar o áudio
        if not pygame.mixer.music.get_busy():
            animando = False


# === EXECUÇÃO COMPLETA DE UMA PERGUNTA ===
def responder(texto: str):
    global ocupado
    try:
        resposta = gerar_resposta_com_memoria(texto)
        print("Resposta:", resposta)
        rotulo_resposta.config(text=resposta)

        # Gera um nome de arquivo único para evitar conflito
        nome_arquivo = f"resposta_{int(time.time()*1000)}.wav"

        # Gera áudio da resposta
        engine.save_to_file(resposta, nome_arquivo)
        engine.runAndWait()

        # Reproduz áudio e anima boca em paralelo
        def reproduzir_e_animar(caminho):
            try:
                # aguarda um pouco caso o SO ainda esteja liberando o arquivo
                time.sleep(0.05)
                pygame.mixer.music.load(caminho)
                pygame.mixer.music.play()
                animar_boca()
            finally:
                # garante que a música pare e remove o arquivo temporário
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass
                try:
                    if os.path.exists(caminho):
                        os.remove(caminho)
                except Exception:
                    pass

        threading.Thread(target=reproduzir_e_animar, args=(nome_arquivo,), daemon=True).start()

    finally:
        # reabilita a UI ao final da resposta (sem depender de sucesso/erro)
        btn_perguntar.config(state=tk.NORMAL)
        entrada.config(state=tk.NORMAL)
        ocupado = False


# === INTERFACE TKINTER ===
def iniciar_resposta():
    global ocupado
    if ocupado:
        return  # evita cliques repetidos

    texto = entrada.get().strip()
    if not texto:
        rotulo_resposta.config(text="Digite uma pergunta.")
        return

    ocupado = True
    rotulo_resposta.config(text="Gerando resposta...")
    btn_perguntar.config(state=tk.DISABLED)
    entrada.config(state=tk.DISABLED)

    t = threading.Thread(target=responder, args=(texto,), daemon=True)
    t.start()


def ao_teclar_enter(event):
    iniciar_resposta()


def finalizar():
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass
    pygame.quit()
    janela.destroy()


# === TK SETUP ===
janela = tk.Tk()
janela.title("Papagaio Offline com IA (Ollama + TTS)")
janela.geometry("520x280")

tk.Label(janela, text="Digite sua pergunta:").pack(pady=10)

entrada = tk.Entry(janela, width=60)
entrada.pack(pady=5)
entrada.bind("<Return>", ao_teclar_enter)

btn_perguntar = tk.Button(janela, text="Perguntar", command=iniciar_resposta)
btn_perguntar.pack(pady=6)

rotulo_resposta = tk.Label(janela, text="", wraplength=500, justify="left")
rotulo_resposta.pack(pady=10)

btn_sair = tk.Button(janela, text="Sair", command=finalizar)
btn_sair.pack(pady=6)

janela.protocol("WM_DELETE_WINDOW", finalizar)
janela.mainloop()
