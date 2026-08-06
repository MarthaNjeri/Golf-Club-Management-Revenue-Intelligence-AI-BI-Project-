from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from core.database import sync_pwa_scorecard_payload

app = FastAPI(title="FairwayIQ PWA Sync Engine")

# Enable CORS so JavaScript fetch calls from Streamlit can reach the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/sync_scorecard")
async def handle_pwa_sync(request: Request):
    """
    Receives local scorecards from PWA clients and passes them 
    to core.database.sync_pwa_scorecard_payload for Last-Write-Wins resolution.
    """
    try:
        data = await request.json()
        player_id = data.get("player_id")
        scores = data.get("scores", {})

        if not player_id or not scores:
            raise HTTPException(status_code=400, detail="Missing player_id or scores payload.")

        # Execute conflict resolution against SQLite WAL database
        result = sync_pwa_scorecard_payload(player_id, scores)

        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message"))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
