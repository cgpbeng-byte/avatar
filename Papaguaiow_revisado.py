import os
import time
import threading
import tkinter as tk
from queue import Queue, Empty
import requests
import pyttsx3
import pygame  # será inicializado e mantido numa thread dedicada

# === CONFIGURAÇÕES ===
LARGURA, ALTURA = 640, 480
COR_FUNDO = (255, 255, 255)
COR_BOCA_FECHADA = (0, 128, 0)
COR_BOCA_ABERTA = (0, 255, 0)
VELOCIDADE_FALA = 150

OLLAMA_URL_CHAT = "http://localhost:11434/api/chat"  # mantém histórico
MODELO = "mistral"

# === ESTADO GLOBAL ===
historico = [
    {"role": "system", "content": "Responda em português do Brasil. Em uma única frase, direto e objetivo."}
]
ocupado = False

# Fila para enviar caminhos de áudio ao worker de animação
anim_queue: "Queue[str|None]" = Queue()
anim_worker_thread = None
worker_running = True  # controla vida do worker

# === INICIALIZAÇÃO DO TTS (somente) ===


# === FUNÇÃO DE RESPOSTA COM IA (com memória) ===
def gerar_resposta_com_memoria(texto_usuario: str) -> str:
    global historico
    historico.append({"role": "user", "content": texto_usuario})
    try:
        resp = requests.post(
            OLLAMA_URL_CHAT,
            json={"model": MODELO, "messages": historico, "stream": False},
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        resposta = data.get("message", {}).get("content", "").strip()
        if not resposta:
            resposta = "Não consegui gerar uma resposta agora."
        historico.append({"role": "assistant", "content": resposta})
        return resposta
    except Exception as e:
        return f"Erro ao gerar resposta: {e}"


# === WORKER DE ANIMAÇÃO (janela do Pygame permanece aberta) ===
def anim_worker():
    """
    Mantém UMA janela Pygame sempre aberta.
    - Quando recebe um caminho de áudio na fila, toca e anima a boca.
    - Quando não há áudio, mostra a boca fechada (ocioso).
    - Fecha tudo com segurança ao encerrar o aplicativo.
    """
    # Inicializa Pygame (display + mixer) uma única vez, nesta thread
    pygame.display.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption("Papagaio Virtual - Falando")

    # Superfícies (bocas)
    boca_fechada = pygame.Surface((200, 200))
    boca_fechada.fill(COR_BOCA_FECHADA)
    boca_aberta = pygame.Surface((200, 200))
    boca_aberta.fill(COR_BOCA_ABERTA)

    clock = pygame.time.Clock()

    # Estado de reprodução
    tocando = False
    caminho_atual = None
    estado_boca = False
    ultimo_toggle = time.time()

    try:
        while worker_running:
            # Processa eventos da janela (mantém a janela viva)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # Ignora o fechar da janela para mantê-la sempre aberta
                    pass

            # Se não está tocando, tenta pegar um novo áudio na fila (não bloqueia)
            if not tocando:
                try:
                    item = anim_queue.get_nowait()
                except Empty:
                    item = None

                if item is None:
                    # Nada novo para tocar → estado ocioso (boca fechada)
                    screen.fill(COR_FUNDO)
                    screen.blit(boca_fechada, (220, 140))
                    pygame.display.flip()
                    clock.tick(30)
                    continue
                else:
                    # Recebeu um caminho de áudio
                    caminho_atual = item
                    # Garante que o arquivo existe (em alguns SOs pode demorar milissegundos)
                    t0 = time.time()
                    while not os.path.exists(caminho_atual) and (time.time() - t0 < 5):
                        time.sleep(0.01)

                    if not os.path.exists(caminho_atual):
                        # Se não existe mesmo assim, volta ao ocioso
                        caminho_atual = None
                        continue

                    # Inicia reprodução
                    try:
                        pygame.mixer.music.load(caminho_atual)
                        pygame.mixer.music.play()
                        tocando = True
                        estado_boca = True
                        ultimo_toggle = time.time()
                    except Exception:
                        # Se por algum motivo falhar, descarta e volta ao ocioso
                        tocando = False
                        caminho_atual = None

            # Se está tocando, anima
            if tocando:
                # Alterna a boca a cada 0,3s enquanto houver áudio tocando
                if time.time() - ultimo_toggle > 0.3:
                    estado_boca = not estado_boca
                    ultimo_toggle = time.time()

                # Desenha cena
                screen.fill(COR_FUNDO)
                boca = boca_aberta if estado_boca else boca_fechada
                screen.blit(boca, (220, 140))
                pygame.display.flip()
                clock.tick(30)

                # Checa término do áudio
                if not pygame.mixer.music.get_busy():
                    tocando = False
                    # Fecha a boca após terminar
                    screen.fill(COR_FUNDO)
                    screen.blit(boca_fechada, (220, 140))
                    pygame.display.flip()

                    # Remove o arquivo de áudio usado
                    if caminho_atual and os.path.exists(caminho_atual):
                        try:
                            os.remove(caminho_atual)
                        except Exception:
                            pass
                    caminho_atual = None

    finally:
        # Limpeza robusta ao sair
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        try:
            if pygame.mixer.get_init():
                pygame.mixer.quit()
        except Exception:
            pass
        try:
            if pygame.display.get_init():
                pygame.display.quit()
        except Exception:
            pass
        try:
            pygame.quit()
        except Exception:
            pass


# === EXECUÇÃO DE UMA PERGUNTA ===
def responder(texto: str):
    global ocupado
    try:
        # 1) Pede resposta ao Ollama
        resposta = gerar_resposta_com_memoria(texto)

        # 2) Atualiza a UI principal (thread-safe via .after)
        janela.after(0, lambda: rotulo_resposta.config(text=resposta))

        # Se houve erro, não enfileira animação
        if resposta.startswith("Erro ao gerar resposta:"):
            return

        # 3) Gera arquivo de áudio único para esta resposta
        nome_arquivo = f"resposta_{int(time.time()*1000)}.wav"
        engine.save_to_file(resposta, nome_arquivo)
        engine.runAndWait()

        # 4) Enfileira para o worker (a janela já está aberta; ele começará a animar quando tocar)
        anim_queue.put(nome_arquivo)

    finally:
        janela.after(0, lambda: (btn_perguntar.config(state=tk.NORMAL),
                                 entrada.config(state=tk.NORMAL)))
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
    # Sinaliza término ao worker e fecha a janela principal
    global worker_running
    worker_running = False
    try:
        anim_queue.put(None)  # não toca nada; só para garantir que o worker não fique bloqueado
    except Exception:
        pass
    try:
        janela.destroy()
    except Exception:
        pass


# === TK SETUP ===
janela = tk.Tk()
janela.title("Papagaio Offline com IA (Ollama + TTS)")
janela.geometry("520x280")

# Esta label permanece na janela principal (como você pediu)
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

# Inicia o worker de animação UMA vez (janela do Pygame ficará sempre aberta)
anim_worker_thread = threading.Thread(target=anim_worker, daemon=True)
anim_worker_thread.start()

janela.mainloop()
