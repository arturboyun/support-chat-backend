import json
from math import log
from typing import Annotated
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

app = FastAPI()
fake_db = {
    "messages": [
        {"text": "Hello", "username": "John Doe"},
        {"text": "How are you?", "username": "Alice"},
        {"text": "Good morning!", "username": "Bob"},
        {"text": "What's up?", "username": "Charlie"},
        {"text": "Nice weather today!", "username": "Eve"},
        {"text": "Any plans for the weekend?", "username": "Frank"},
    ]
}


class MessageIn(BaseModel):
    text: str


class MessageOut(BaseModel):
    username: str
    text: str


class ConnectionManager:
    def __new__(cls):
        # Singleton pattern
        if not hasattr(cls, "instance"):
            cls.instance = super(ConnectionManager, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        for message in fake_db["messages"]:
            await websocket.send_json(message)

    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        await websocket.close()

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        fake_db["messages"].append(message)
        await websocket.send_text(message)

    async def broadcast(self, message: dict):
        fake_db["messages"].append(message)
        for connection in self.active_connections:
            print(f"Sending message to {connection} {message}")
            await connection.send_json(message)


manager = ConnectionManager()


@app.websocket("/ws/{username}")
async def websocket_endpoint(
    username: str,
    websocket: WebSocket,
):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                print(data)
                message = MessageIn.model_validate(json.loads(data))
            except ValidationError as e:
                print(e)
                await manager.send_personal_message("Invalid message", websocket)
                continue
            except json.JSONDecodeError:
                await manager.send_personal_message("Invalid message", websocket)
                continue

            await manager.broadcast(
                MessageOut(username=username, text=message.text).model_dump()
            )
            # await manager.send_personal_message("You wrote: " + data, websocket)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        await manager.broadcast(f"Client {username} left the chat")
