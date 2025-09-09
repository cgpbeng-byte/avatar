import asyncio
import websockets

# Lista para armazenar clientes conectados
connected = set()

async def handler(websocket, path):
    # Adiciona o cliente na lista
    connected.add(websocket)
    print(f"Cliente conectado: {websocket.remote_address}")
    try:
        async for message in websocket:
            # Aqui você pode tratar mensagens do cliente, se quiser
            print(f"Mensagem recebida do cliente: {message}")
    except websockets.exceptions.ConnectionClosed:
        print(f"Cliente desconectado: {websocket.remote_address}")
    finally:
        connected.remove(websocket)

async def main():
    async with websockets.serve(handler, "localhost", 6790):
        print("Servidor WebSocket rodando em ws://localhost:6789")
        while True:
            cmd = input("Digite 'hide' para esconder cilindros ou 'show' para mostrar: ").strip().lower()
            if cmd in ("hide", "show"):
                if connected:
                    # Envia comando para todos os clientes conectados
                    await asyncio.wait([ws.send(cmd) for ws in connected])
                    print(f"Comando '{cmd}' enviado para {len(connected)} cliente(s).")
                else:
                    print("Nenhum cliente conectado.")
            else:
                print("Comando inválido. Use 'hide' ou 'show'.")

if __name__ == "__main__":
    asyncio.run(main())
