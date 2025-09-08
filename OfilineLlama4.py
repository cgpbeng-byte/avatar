import os
import time
import threading
import tkinter as tk
import requests
import pyttsx3
import pygame  # importado, inicializado apenas quando for animar

# === CONFIGURAÇÕES ===
LARGURA, ALTURA = 640, 480
COR_FUNDO = (255, 255, 255)
COR_BOCA_FECHADA = (0, 128, 0)
COR_BOCA_ABERTA = (0, 255, 0)
VELOCIDADE_FALA = 150

OLLAMA_URL_CHAT = "http://localhost:11434/api/chat"  # usa /api/chat para manter histórico
MODELO = "mistral"  # ajuste conforme seu modelo no Ollama

# === ESTADO GLOBAL ===
historico = [
    {"role": "system", "content": "Responda em português do Brasil. Em uma única frase, direto e objetivo."}
]
ocupado = False  # evita concorrência entre perguntas

# === INICIALIZAÇÃO DO TTS (somente) ===
engine = pyttsx3.init()
engine.setProperty('rate', VELOCIDADE_FALA)


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


# === JANELA/ANIMAÇÃO **SÓ DURANTE O ÁUDIO** ===
def animar_boca_durante_audio(caminho_audio: str):
    """
    Abre a janela do Pygame apenas enquanto o áudio estiver sendo reproduzido.
    Fecha a janela e libera tudo ao término.
    """
    # Inicializa apenas os módulos necessários, e só agora
    pygame.display.init()
    pygame.mixer.init()

    try:
        screen = pygame.display.set_mode((LARGURA, ALTURA))
        pygame.display.set_caption("Papagaio Virtual - Falando")

        # Cria as superfícies (boca) localmente
        boca_fechada = pygame.Surface((200, 200))
        boca_fechada.fill(COR_BOCA_FECHADA)
        boca_aberta = pygame.Surface((200, 200))
        boca_aberta.fill(COR_BOCA_ABERTA)

        # Carrega e toca o áudio
        # Pequeno atraso pode evitar 'file busy' em alguns SOs
        time.sleep(0.05)
        pygame.mixer.music.load(caminho_audio)
        pygame.mixer.music.play()

        clock = pygame.time.Clock()
        estado_boca = True
        ultimo_tempo = time.time()
        rodando = True

        while rodando:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    # Se fechar a janela, interrompe o áudio e sai
                    pygame.mixer.music.stop()
                    rodando = False

            screen.fill(COR_FUNDO)

            # Alterna a boca a cada 0,3s enquanto houver áudio tocando
            if pygame.mixer.music.get_busy() and (time.time() - ultimo_tempo > 0.3):
                estado_boca = not estado_boca
                ultimo_tempo = time.time()

            # Se não estiver tocando, mantém fechada
            boca = boca_aberta if (estado_boca and pygame.mixer.music.get_busy()) else boca_fechada
            screen.blit(boca, (220, 140))

            pygame.display.flip()
            clock.tick(30)

            # Fecha automaticamente quando o áudio terminar
            if not pygame.mixer.music.get_busy():
                rodando = False

    finally:
        # Encerra módulos do pygame desta janela
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.quit()
        except Exception:
            pass

        try:
            if pygame.display.get_init():
                pygame.display.quit()
        except Exception:
            pass

        # pygame.quit() encerra todos os módulos se ainda restar algo
        try:
            pygame.quit()
        except Exception:
            pass

        # Remove o arquivo de áudio após encerrar o mixer
        try:
            if os.path.exists(caminho_audio):
                os.remove(caminho_audio)
        except Exception:
            pass


# === EXECUÇÃO COMPLETA DE UMA PERGUNTA ===
def responder(texto: str):
    global ocupado

    try:
        # 1) Pede resposta ao Ollama
        resposta = gerar_resposta_com_memoria(texto)

        # 2) Atualiza a UI principal (thread-safe via .after)
        def atualizar_ui_com_resposta():
            rotulo_resposta.config(text=resposta)
        janela.after(0, atualizar_ui_com_resposta)

        # Se houve erro, não abre animação
        if resposta.startswith("Erro ao gerar resposta:"):
            return

        # 3) Gera arquivo de áudio único para esta resposta
        nome_arquivo = f"resposta_{int(time.time()*1000)}.wav"
        engine.save_to_file(resposta, nome_arquivo)
        engine.runAndWait()

        # 4) (ATENDE AO PEDIDO) Abre a janela de animação AO CHEGAR a resposta
        # Aqui a resposta já chegou, e o áudio está pronto.
        t = threading.Thread(target=animar_boca_durante_audio, args=(nome_arquivo,), daemon=True)
        t.start()

    finally:
        # Reabilita a UI (via .after para thread-safety)
        def reabilitar_ui():
            btn_perguntar.config(state=tk.NORMAL)
            entrada.config(state=tk.NORMAL)
        janela.after(0, reabilitar_ui)
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
    # Apenas fecha a janela principal (as animações/áudios rodam em threads isoladas e finalizam sozinhas)
    try:
        janela.destroy()
    except Exception:
        pass


# === TK SETUP ===
janela = tk.Tk()
janela.title("Papagaio Offline com IA (Ollama + TTS)")
janela.geometry("520x280")

# (ATENDE AO PEDIDO) Este label PERMANECE na janela principal
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
