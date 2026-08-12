from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.progress_hub import manager

router = APIRouter()


@router.websocket("/ws/inspections/{inspection_id}")
async def inspection_progress_ws(websocket: WebSocket, inspection_id: int):
    await manager.connect(inspection_id, websocket)
    try:
        while True:
            # Client doesn't need to send anything; keep the socket open and
            # drain any pings/keepalives it sends.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(inspection_id, websocket)
