import asyncio
import os
import uuid
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from queue_manager import TaskQueueManager

app = FastAPI(title="QUREO & SPX Multi-Platform Solver")
queue_manager = TaskQueueManager()

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE_PATH = os.path.join(CURRENT_DIR, "index.html")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(queue_manager.worker())

class JoinQueueRequest(BaseModel):
    grade: str
    subject: str
    student_id: str
    password: str

@app.get("/", response_class=HTMLResponse)
async def home():
    if os.path.exists(INDEX_FILE_PATH):
        return FileResponse(INDEX_FILE_PATH)
    return HTMLResponse("<h2>ملف index.html غير موجود في نفس المجلد!</h2>", status_code=404)

@app.post("/api/queue/join")
async def join_queue(req: JoinQueueRequest):
    task_id = str(uuid.uuid4())
    pos = await queue_manager.add_task(task_id, req.dict())
    ahead = max(0, pos - 1)
    return {
        "task_id": task_id,
        "position": pos,
        "ahead": ahead,
        "message": f"انت دورك رقم: {pos} — هيبدأ الحل بعد {ahead} طلبات قبلك."
    }

@app.websocket("/ws/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str):
    await websocket.accept()
    await queue_manager.register_socket(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        queue_manager.unregister_socket(task_id)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 1111))
    print(f"Starting Solver Engine on port {port}...")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
