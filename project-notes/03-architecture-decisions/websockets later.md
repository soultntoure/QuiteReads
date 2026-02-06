┌─────────────┐     POST /start      ┌─────────────┐
│   Frontend  │ ──────────────────►  │   FastAPI   │
└─────────────┘                      └──────┬──────┘
       ▲                                    │
       │ WebSocket                          │ asyncio.create_task()
       │ (real-time updates)                ▼
       │                            ┌──────────────┐
       └─────────────────────────── │ Background   │
         emit("epoch_complete",     │ Training     │
              {rmse: 0.85, ...})    │ Task         │
                                    └──────────────┘
How It Would Work:
Start training → spawns background task
Training task → after each epoch, broadcasts metrics via WebSocket
Frontend → receives real-time updates, updates charts live
python
# Future WebSocket integration example
@app.websocket("/ws/experiments/{experiment_id}")
async def experiment_ws(websocket: WebSocket, experiment_id: str):
    await websocket.accept()
    # Client receives live updates from training task
FastAPI has built-in WebSocket support, so adding this later is straightforward. For now, the frontend can poll /experiments/{id}/metrics every few seconds as a simpler approach.

Quick note about your diff: I see you changed the API path from /experiments${query} to /experiments/${query}. This adds an extra / which might cause 404 errors (path becomes /experiments/?status=... instead of /experiments?status=...). Was this intentional?

Would you like me to implement the background task solution now so your experiments actually run?