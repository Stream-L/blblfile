import asyncio
import websockets
from aiohttp import web
import json

# WebSocket配置
# WS_URI = "ws://10.12.59.33:23333/"
WS_URI = "ws://127.0.0.1:23333/"
# TOKEN = "danmu"

target_group_id = 697375450 # 目标群ID

# 存储最新消息
latest_message = None
ws_clients = set()

async def ws_client():
    global latest_message
    while True:
        try:
            async with websockets.connect(WS_URI) as ws:  # 移除 extra_headers
                print("WebSocket已连接")
                async for msg in ws:
                    latest_message = msg
        except Exception as e:
            print(f"WebSocket连接失败: {e}")
            await asyncio.sleep(3)  # 3秒后重连

def build_json():
    if latest_message is None:
        return {
            "text": "",
            "time": 0
        }
    try:
        data = json.loads(latest_message)
        # 判断 post_type
        if data.get("post_type") != "message":
            return {"text": "", "time": data.get("time", 0)}
        # 判断 message_type
        if data.get("message_type") != "group":
            return {"text": "", "time": data.get("time", 0)}
        # 判断 group_id
        if data.get("group_id") != target_group_id:
            return {"text": "", "time": data.get("time", 0)}
        # 提取 message 数组中的 text 内容
        msg_list = data.get("message", [])
        texts = []
        for item in msg_list:
            if item.get("type") == "text":
                text = item.get("data", {}).get("text", "")
                texts.append(text)
        return {
            "text": "".join(texts),
            "time": data.get("time", 0)
        }
    except Exception:
        return {
            "text": str(latest_message),
            "time": 0
        }

async def handle_http(request):
    return web.json_response(build_json())

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    ws_clients.add(ws)
    try:
        # 首次连接立即推送一次
        await ws.send_str(json.dumps(build_json(), ensure_ascii=False))
        async for msg in ws:
            pass  # 不处理客户端消息
    finally:
        ws_clients.remove(ws)
    return ws

async def broadcast_loop():
    last = None
    while True:
        await asyncio.sleep(0.5)
        data = build_json()
        text = json.dumps(data, ensure_ascii=False)
        if data["text"] and text != last:
            last = text
            for ws in list(ws_clients):
                try:
                    await ws.send_str(text)
                except Exception:
                    ws_clients.discard(ws)

async def main():
    # 启动WebSocket客户端
    asyncio.create_task(ws_client())
    asyncio.create_task(broadcast_loop())
    # 启动HTTP服务器
    app = web.Application()
    app.router.add_get('/', handle_http)
    app.router.add_get('/ws', ws_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site1 = web.TCPSite(runner, '0.0.0.0', 2334)
    site2 = web.TCPSite(runner, '0.0.0.0', 233)
    await site1.start()
    await site2.start()
    print("HTTP server running at http://127.0.0.1:2334/")
    print("WebSocket server running at ws://127.0.0.1:233/ws")
    # 保持运行
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
