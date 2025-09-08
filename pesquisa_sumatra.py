import os
import time
import subprocess

# Caminho da pasta onde está o script
pasta_pdf = os.path.dirname(os.path.abspath(__file__))

# Caminho para o executável do SumatraPDF
sumatra_path = r'C:\Users\4122799\AppData\Local\SumatraPDF\SumatraPDF.exe'

# Tempo para manter o PDF aberto
tempo_espera = 5

# Percorre os PDFs na pasta
for arquivo in os.listdir(pasta_pdf):
    if arquivo.lower().endswith('.pdf'):
        caminho_completo = os.path.join(pasta_pdf, arquivo)
        
        # Abre o PDF em tela cheia com SumatraPDF
        processo = subprocess.Popen([sumatra_path, '-fullscreen', caminho_completo])
        
        print(f"Abrindo em tela cheia: {arquivo}")
        time.sleep(tempo_espera)
        
        # Fecha o SumatraPDF
        processo.terminate()
        print(f"Fechado: {arquivo}")
