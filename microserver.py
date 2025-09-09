import asyncio
import websockets

clients = set()

async def handler(websocket):
    clients.add(websocket)
    try:
        async for message in websocket:
            print(f"Recebido do cliente: {message}")
            # Aqui você pode receber comandos do front-end se quiser
    finally:
        clients.remove(websocket)

async def send_command(command):
    if clients:
        await asyncio.wait([client.send(command) for client in clients])

async def main():
    async with websockets.serve(handler, "localhost", 6789):
        print("Servidor WebSocket rodando em ws://localhost:6789")
        while True:
            cmd = input("Digite comando (show/hide): ").strip()
            if cmd == "show":
                await send_command("show_cylinders")
            elif cmd == "hide":
                await send_command("hide_cylinders")
            else:
                print("Comando desconhecido")

asyncio.run(main())
