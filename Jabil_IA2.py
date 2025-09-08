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
COR_BOCA_ABERTA  = (0, 255, 0)
VELOCIDADE_FALA = 150

# ---- LOGO (box + imagem) ----  << voltou ao padrão >>
LOGO_IMAGEM = "logo.png"      # se não existir, procuramos outra imagem na pasta
LOGO_BOX_W, LOGO_BOX_H = 300, 80
LOGO_BOX_Y = 20
LOGO_BOX_X = (LARGURA - LOGO_BOX_W) // 2
LOGO_BG     = (245, 245, 245)  # fundo do box
LOGO_BORDER = (100, 100, 100)  # cor da borda

OLLAMA_URL_CHAT = "http://localhost:11434/api/chat"  # mantém histórico
MODELO = "mistral"

# === ESTADO GLOBAL ===
historico = [
    {"role": "system", "content": "Responda em português do Brasil. Em uma única frase, direto e objetivo."}
]
ocupado = False

# Fila para enviar caminhos de áudio ao worker de animação
anim_queue = Queue()
anim_worker_thread = None
worker_running = True  # controla vida do worker


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
    pygame.font.init()

    screen = pygame.display.set_mode((LARGURA, ALTURA))
    pygame.display.set_caption("MEiviS - JABIL")

    # Superfícies (bocas)
    boca_fechada = pygame.Surface((200, 200))
    boca_fechada.fill(COR_BOCA_FECHADA)
    boca_aberta = pygame.Surface((200, 200))
    boca_aberta.fill(COR_BOCA_ABERTA)

    clock = pygame.time.Clock()
    font_logo = pygame.font.SysFont(None, 28)

    # --- Carregamento do logo (com fallback) ---
    def encontrar_logo_na_pasta():
        try:
            exts = (".png", ".jpg", ".jpeg", ".bmp", ".gif")
            arquivos = os.listdir(".")
            # Prioriza nomes que começam com "logo."
            for f in arquivos:
                lf = f.lower()
                if lf.startswith("logo.") and lf.endswith(exts):
                    return f
            for f in arquivos:
                if f.lower().endswith(exts):
                    return f
        except Exception:
            pass
        return None

    logo_path = LOGO_IMAGEM if os.path.exists(LOGO_IMAGEM) else encontrar_logo_na_pasta()

    logo_surf = None
    if logo_path:
        try:
            raw_logo = pygame.image.load(logo_path).convert_alpha()
            # Ajusta para caber no box com padding mantendo proporção
            pad = 8
            max_w = LOGO_BOX_W - 2 * pad
            max_h = LOGO_BOX_H - 2 * pad
            lw, lh = raw_logo.get_width(), raw_logo.get_height()
            escala = min(max_w / lw, max_h / lh)
            new_size = (max(1, int(lw * escala)), max(1, int(lh * escala)))
            logo_surf = pygame.transform.smoothscale(raw_logo, new_size)
        except Exception:
            logo_surf = None

    # --- Função para desenhar o logo BOX (fundo + borda + imagem ou placeholder) ---
    def desenhar_logo_box():
        box_rect = pygame.Rect(LOGO_BOX_X, LOGO_BOX_Y, LOGO_BOX_W, LOGO_BOX_H)
        pygame.draw.rect(screen, LOGO_BG, box_rect, border_radius=8)
        pygame.draw.rect(screen, LOGO_BORDER, box_rect, width=2, border_radius=8)
        if logo_surf is not None:
            lx = LOGO_BOX_X + (LOGO_BOX_W - logo_surf.get_width()) // 2
            ly = LOGO_BOX_Y + (LOGO_BOX_H - logo_surf.get_height()) // 2
            screen.blit(logo_surf, (lx, ly))
        else:
            # Placeholder "LOGO"
            txt = font_logo.render("LOGO", True, (120, 120, 120))
            tx = LOGO_BOX_X + (LOGO_BOX_W - txt.get_width()) // 2
            ty = LOGO_BOX_Y + (LOGO_BOX_H - txt.get_height()) // 2
            screen.blit(txt, (tx, ty))

    # --- Função para desenhar um frame completo ---
    def desenhar_frame(boca_surface):
        screen.fill(COR_FUNDO)
        desenhar_logo_box()  # << voltou a desenhar o box com borda >>
        # Boca centralizada na região inferior
        screen.blit(boca_surface, (220, 140))
        pygame.display.flip()

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
                    # Nada novo para tocar → estado ocioso (boca fechada) + logo
                    desenhar_frame(boca_fechada)
                    clock.tick(30)
                    continue
                else:
                    # Recebeu um caminho de áudio
                    caminho_atual = item
                    # Garante que o arquivo existe (pode demorar milissegundos)
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

                # Desenha cena (logo + boca)
                boca = boca_aberta if estado_boca else boca_fechada
                desenhar_frame(boca)
                clock.tick(30)

                # Checa término do áudio
                if not pygame.mixer.music.get_busy():
                    tocando = False
                    # Fecha a boca após terminar (mostra um frame final com boca fechada)
                    desenhar_frame(boca_fechada)
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


# === SELEÇÃO DE VOZ FEMININA (helper) ===
def get_voice_id_feminina_ptbr(engine):
    """
    Tenta encontrar uma voz feminina pt-BR (ex.: 'Microsoft Maria Desktop').
    Fallback: qualquer voz feminina; por fim, None (usa a padrão).
    """
    try:
        voces = engine.getProperty('voices')
    except Exception:
        return None

    # 1) Prioriza pt-BR feminina por nome/idioma
    preferidas_por_nome = ['maria', 'heloisa', 'heloísa', 'francisca']
    for v in voces:
        name = (getattr(v, 'name', '') or '').lower()
        lang_tags = [str(l).lower() for l in getattr(v, 'languages', [])]
        gender = (getattr(v, 'gender', '') or '').lower()
        if ('pt' in ''.join(lang_tags) or 'pt-br' in ''.join(lang_tags)
            or 'portuguese' in name or 'português' in name
            or 'brazil' in name or 'brasil' in name):
            if any(p in name for p in preferidas_por_nome) or gender == 'female':
                return v.id

    # 2) Se não achou pt-BR, pega qualquer feminina
    for v in voces:
        gender = (getattr(v, 'gender', '') or '').lower()
        if gender == 'female':
            return v.id

    # 3) Sem voz feminina disponível
    return None


# === EXECUÇÃO DE UMA PERGUNTA ===
def responder(texto: str):
    global ocupado
    eng = None  # para garantir stop() no finally
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

        # Engine de TTS criado por chamada/thread (Opção A)
        eng = pyttsx3.init(driverName='sapi5')  # Windows: usa SAPI5
        eng.setProperty('rate', VELOCIDADE_FALA)

        # Seleciona voz feminina (prioriza pt-BR)
        voice_id = get_voice_id_feminina_ptbr(eng)
        if voice_id:
            eng.setProperty('voice', voice_id)
        else:
            print("Aviso: não encontrei voz feminina instalada; usando a voz padrão do sistema.")

        eng.save_to_file(resposta, nome_arquivo)
        eng.runAndWait()

        # 4) Enfileira para o worker (a janela já está aberta; ele vai tocar e animar)
        anim_queue.put(nome_arquivo)

    finally:
        # Para segurança: encerra engine local, se criado
        if eng is not None:
            try:
                eng.stop()
            except Exception:
                pass

        # Reabilita UI
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
        anim_queue.put(None)  # evita bloqueio do worker
    except Exception:
        pass
    try:
        janela.destroy()
    except Exception:
        pass


# === TK SETUP ===
janela = tk.Tk()
janela.title("Caixa de pergunta")
janela.geometry("520x280")

# Esta label permanece na janela principal
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
