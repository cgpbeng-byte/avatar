import os
import time
import subprocess
import tkinter as tk
from tkinter import messagebox

def verificar_e_abrir():
    texto = entrada.get()
    if "sensor" in texto.lower():
        pasta_pdf = os.path.dirname(os.path.abspath(__file__))
        tempo_espera = 5
        encontrados = False

        # Caminho do Chrome (ajuste se o seu estiver em outro local)
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

        for arquivo in os.listdir(pasta_pdf):
            if arquivo.lower().endswith('.pdf') and "sensor" in arquivo.lower():
                caminho_completo = os.path.join(pasta_pdf, arquivo)
                # Abre no Chrome
                processo = subprocess.Popen([chrome_path, caminho_completo])
                print(f"Abrindo no Chrome: {arquivo}")
                time.sleep(tempo_espera)
                processo.terminate()  # Fecha o Chrome (mata o processo)
                print(f"Fechado: {arquivo}")
                encontrados = True

        if not encontrados:
            messagebox.showinfo("Resultado", "Nenhum arquivo PDF com 'sensor' no nome foi encontrado.")
    else:
        messagebox.showinfo("Resultado", "A palavra 'sensor' não foi encontrada no texto.")

# Interface gráfica
janela = tk.Tk()
janela.title("Abrir PDFs com 'sensor'")

tk.Label(janela, text="Digite uma frase:").pack(pady=5)
entrada = tk.Entry(janela, width=50)
entrada.pack(pady=5)

botao = tk.Button(janela, text="Verificar e Abrir PDFs", command=verificar_e_abrir)
botao.pack(pady=10)

janela.mainloop()
