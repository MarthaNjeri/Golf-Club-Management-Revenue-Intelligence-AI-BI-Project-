import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import os
from core.database import init_db, get_db_connection, get_course_pars_and_si

# 1. CONFIGURE GLOBAL WORKSPACE
st.set_page_config(page_title="FairwayIQ Master Hub", page_icon="⛳", layout="wide")


# --- 📱 PWA ENGINE & OFFLINE STORAGE INJECTION (FASTAPI OPTION B INTEGRATION) ---
def enable_pwa_with_offline_cache(player_id="1", current_hole=1, current_scores=None):
    """
    Injects PWA web app manifest metadata, a Service Worker for static caching,
    a client-side offline scorecard widget that prevents Streamlit WebSocket freezes,
    and an dynamic-host sync engine targeting the FastAPI endpoint (Port 8000).
    """
    if current_scores is None:
        current_scores = {}

    scores_json = json.dumps(current_scores)

    pwa_offline_html = f"""
    <!-- 📱 Client-Side Offline Score Card (Prevents Streamlit WS disconnect freeze) -->
    <div id="pwa-score-card" style="background: #0f172a; color: #f8fafc; padding: 16px; border-radius: 12px; margin: 10px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; border: 1px solid #1e293b; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h4 style="margin: 0; color: #4ade80; font-size: 16px; display: flex; align-items: center; gap: 6px;">
                <span>⛳</span> Mobile Offline Scorecard
            </h4>
            <span id="pwa-sync-pill" style="font-size: 10px; padding: 2px 8px; border-radius: 12px; background: #334155; color: #94a3b8; font-weight: bold;">
                READY
            </span>
        </div>
        
        <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 14px;">
            <div style="flex: 1;">
                <label style="font-size: 11px; text-transform: uppercase; color: #94a3b8; display: block; margin-bottom: 4px; font-weight: 600;">Hole</label>
                <input type="number" id="pwa-hole-num" value="{current_hole}" min="1" max="18" style="width: 100%; padding: 8px 10px; border-radius: 6px; border: 1px solid #334155; background: #1e293b; color: #fff; font-size: 14px; box-sizing: border-box;">
            </div>
            
            <div style="flex: 1;">
                <label style="font-size: 11px; text-transform: uppercase; color: #94a3b8; display: block; margin-bottom: 4px; font-weight: 600;">Strokes</label>
                <input type="number" id="pwa-score-val" value="4" min="1" max="15" style="width: 100%; padding: 8px 10px; border-radius: 6px; border: 1px solid #334155; background: #1e293b; color: #fff; font-size: 14px; box-sizing: border-box;">
            </div>
        </div>
        
        <button onclick="saveScoreOffline()" style="width: 100%; padding: 12px; background: linear-gradient(135deg, #16a34a 0%, #15803d 100%); color: white; border: none; border-radius: 8px; font-weight: 700; font-size: 14px; cursor: pointer; transition: all 0.2s ease;">
            💾 Save Score (Offline Guaranteed)
        </button>
        
        <p id="pwa-status-msg" style="font-size: 12px; color: #94a3b8; margin: 10px 0 0 0; text-align: center; min-height: 16px;"></p>
    </div>

    <script>
    // Dynamically resolve server hostname (works for localhost or LAN IP)
    const currentHost = window.parent.location.hostname || window.location.hostname || 'localhost';
    const API_ENDPOINT = `http://${{currentHost}}:8000/api/sync_scorecard`;
    const PLAYER_ID = "{player_id}";
    const STORAGE_KEY = `fairwayiq_scores_${{PLAYER_ID}}`;
    const serverScores = {scores_json};

    // 1. PWA Manifest & App Mode Setup
    const targetDoc = window.parent.document || document;
    if (!targetDoc.querySelector('link[rel="manifest"]')) {{
        const manifestLink = targetDoc.createElement('link');
        manifestLink.rel = 'manifest';
        manifestLink.href = 'data:application/json;base64,eyJzaG9ydF9uYW1lIjoiRmFpcndheUlRIiwibmFtZSI6IkZhaXJ3YXlJUSBHb2xmIFJldmVudWUgJiBPcGVyYXRpb25zIiwiaWNvbnMiOlt7InNyYyI6Imh0dHBzOi8vY2RuLWljb25zLXBuZy5mbGF0aWNvbi5jb20vNTEyLzMwNzYvMzA3NjQxMy5wbmciLCJ0eXBlIjoiaW1hZ2UvcG5nIiwic2l6ZXMiOiIxOTJ4MTkyIn0seyJzcmMiOiJodHRwczovL2Nkbi1pY29ucy1wbmcuZmxhdGljb24uY29tLzUxMi8zMDc2LzMwNzY0MTMucG5nIiwidHlwZSI6ImltYWdlL3BuZyIsInNpemVzIjo1MTJ4NTEyfV0sInN0YXJ0X3VybCI6Ii8iLCJiYWNrZ3JvdW5kX2NvbG9yIjoiI2ZmZmZmZiIsInRoZW1lX2NvbG9yIjoiIzFiOGQzZSIsImRpc3BsYXkiOiJzdGFuZGFsb25lIiwib3JpZW50YXRpb24iOiJwb3J0cmFpdCJ9';
        targetDoc.head.appendChild(manifestLink);
    }}

    // 2. Service Worker Registration for Static Caching
    const targetNav = window.parent.navigator || navigator;
    if ('serviceWorker' in targetNav) {{
        const swCode = `
            const CACHE_NAME = 'fairwayiq-v1';
            const ASSETS_TO_CACHE = ['/'];
            
            self.addEventListener('install', (e) => {{
                e.waitUntil(
                    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
                );
                self.skipWaiting();
            }});

            self.addEventListener('activate', (e) => {{
                e.waitUntil(self.clients.claim());
            }});

            self.addEventListener('fetch', (e) => {{
                e.respondWith(
                    fetch(e.request).catch(() => caches.match(e.request))
                );
            }});
        `;
        const blob = new Blob([swCode], {{ type: 'application/javascript' }});
        const swUrl = URL.createObjectURL(blob);
        
        targetNav.serviceWorker.register(swUrl)
            .then(reg => console.log('⛳ ServiceWorker Active:', reg.scope))
            .catch(err => console.log('ServiceWorker Reg Failed:', err));
    }}

    // 3. Client-Side Offline Storage Action
    function saveScoreOffline() {{
        const holeNum = document.getElementById('pwa-hole-num').value;
        const scoreVal = document.getElementById('pwa-score-val').value;
        const statusMsg = document.getElementById('pwa-status-msg');
        const pill = document.getElementById('pwa-sync-pill');

        try {{
            const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{{ "scores": {{}}, "unsynced": false }}');
            
            data.scores[holeNum] = {{
                score: parseInt(scoreVal),
                ts: new Date().toISOString()
            }};
            data.unsynced = true;
            
            localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
            
            statusMsg.style.color = '#4ade80';
            statusMsg.innerText = `Saved Hole ${{holeNum}} (${{scoreVal}} strokes) locally!`;
            
            pill.style.background = '#d97706';
            pill.style.color = '#ffffff';
            pill.innerText = 'QUEUED';

            attemptSyncWithServer();
        }} catch (e) {{
            statusMsg.style.color = '#f87171';
            statusMsg.innerText = 'Error writing to device storage.';
        }}
    }}

    async function attemptSyncWithServer() {{
        const statusMsg = document.getElementById('pwa-status-msg');
        const pill = document.getElementById('pwa-sync-pill');
        const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{{ "scores": {{}}, "unsynced": false }}');
        
        if (!navigator.onLine || !data.unsynced || Object.keys(data.scores).length === 0) {{
            return;
        }}

        try {{
            const response = await fetch(API_ENDPOINT, {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{
                    player_id: PLAYER_ID,
                    scores: data.scores
                }})
            }});

            if (response.ok) {{
                data.unsynced = false;
                localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
                
                if (statusMsg) {{
                    statusMsg.style.color = '#38bdf8';
                    statusMsg.innerText = '🟢 Synced cached scores to server!';
                }}
                if (pill) {{
                    pill.style.background = '#16a34a';
                    pill.style.color = '#ffffff';
                    pill.innerText = 'SYNCED';
                }}
            }}
        }} catch (err) {{
            console.log("Sync queued for reconnect.");
        }}
    }}

    // 4. Live Network Badge & Listener
    function updateOnlineStatus() {{
        const isOnline = navigator.onLine;
        let badge = targetDoc.getElementById('fairwayiq-net-status');
        
        if (!badge) {{
            badge = targetDoc.createElement('div');
            badge.id = 'fairwayiq-net-status';
            badge.style.position = 'fixed';
            badge.style.bottom = '14px';
            badge.style.right = '14px';
            badge.style.padding = '8px 14px';
            badge.style.borderRadius = '20px';
            badge.style.fontSize = '12px';
            badge.style.fontWeight = 'bold';
            badge.style.zIndex = '999999';
            badge.style.boxShadow = '0 3px 8px rgba(0,0,0,0.25)';
            badge.style.transition = 'all 0.3s ease';
            targetDoc.body.appendChild(badge);
        }}

        if (isOnline) {{
            badge.style.backgroundColor = '#1b8d3e';
            badge.style.color = '#ffffff';
            badge.innerText = '🟢 Live Sync Active';
            attemptSyncWithServer();
        }} else {{
            badge.style.backgroundColor = '#d97706';
            badge.style.color = '#ffffff';
            badge.innerText = '🟠 Offline Mode (Caching Scores)';
        }}
    }}

    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    document.addEventListener('DOMContentLoaded', updateOnlineStatus);
    setTimeout(updateOnlineStatus, 800);
    </script>
    """
    components.html(pwa_offline_html, height=210)


# --- CENTRAL STORAGE CONTEXT ---
init_db()
conn = get_db_connection()

DB_FILE = "data/live_leaderboard.csv"
POS_FILE = "data/pos_transactions.csv"

# --- DYNAMIC COURSE SETUP ---
try:
    dynamic_course_map = get_course_pars_and_si("Limuru Country Club", "White")
    ACTIVE_PARS = {hole: values[0] for hole, values in dynamic_course_map.items()}
except Exception:
    ACTIVE_PARS = {
        1: 4, 2: 4, 3: 3, 4: 5, 5: 4, 6: 4, 7: 3, 8: 4, 9: 5,
        10: 4, 11: 4, 12: 3, 13: 5, 14: 4, 15: 4, 16: 3, 17: 4, 18: 5
    }

TOTAL_COURSE_PAR = sum(ACTIVE_PARS.values())

# --- IDENTITY STATE ENGINE ---
if 'authorized' not in st.session_state:
    st.session_state.authorized = False
if 'auth_type' not in st.session_state:
    st.session_state.auth_type = None
if 'player_name' not in st.session_state:
    st.session_state.player_name = ""
if 'player_id' not in st.session_state:
    st.session_state.player_id = 1
if 'player_hcp' not in st.session_state:
    st.session_state.player_hcp = 10
if 'home_club' not in st.session_state:
    st.session_state.home_club = "Thika Sports Club"
if 'competition' not in st.session_state:
    st.session_state.competition = "Casual Round"
if 'current_hole' not in st.session_state:
    st.session_state.current_hole = 1
if 'hole_scores' not in st.session_state:
    st.session_state.hole_scores = {h: ACTIVE_PARS[h] for h in range(1, 19)}

# Activate PWA + Offline Caching Engine using live session state
enable_pwa_with_offline_cache(
    player_id=st.session_state.player_id,
    current_hole=st.session_state.current_hole,
    current_scores=st.session_state.hole_scores
)

# Administrative & Waitstaff persistent authentication states
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False
if 'staff_authenticated' not in st.session_state:
    st.session_state.staff_authenticated = False
if 'suspense_mode' not in st.session_state:
    st.session_state.suspense_mode = True

# Initialize state variables for our three direct administrative toggles
if 'enable_overrides' not in st.session_state:
    st.session_state.enable_overrides = False
if 'enable_podium' not in st.session_state:
    st.session_state.enable_podium = False
if 'enable_shootout' not in st.session_state:
    st.session_state.enable_shootout = False

# --- LINK ROUTER & CENTRAL SELECTION HUB ---
query_params = st.query_params
app_mode = None

if "view" in query_params:
    url_view = query_params["view"]
    if url_view == "player":
        app_mode = "🏌️ Player Scorecard Portal"
    elif url_view == "pos":
        app_mode = "🍔 Clubhouse F&B Terminal"
    elif url_view == "monitor":
        app_mode = "🏆 Tournament Leaderboard Monitor"
    else:
        app_mode = "🏌️ Player Scorecard Portal"
else:
    st.sidebar.title("🏁 FairwayIQ Gateway")
    
    # Clubhouse F&B Terminal sits directly on the main role options
    user_role = st.sidebar.radio(
        "Select Portal Role:", 
        [
            "🏌️ Golfer / Caddie Terminal", 
            "🍔 Clubhouse F&B Terminal", 
            "🛡️ Tournament Administration"
        ]
    )
    st.sidebar.markdown("---")

    if user_role == "🏌️ Golfer / Caddie Terminal":
        app_mode = "🏌️ Player Scorecard Portal"
        st.sidebar.success("Player Mode Active")
        
    elif user_role == "🍔 Clubhouse F&B Terminal":
        # Secure the F&B portal from players with a lightweight staff PIN
        staff_pin = st.sidebar.text_input("Enter F&B Staff PIN:", type="password")
        
        # Pull or default the staff PIN
        try:
            target_staff_pin = st.secrets["staff"]["pin"]
        except Exception:
            target_staff_pin = "2026"  # Professional Year Fallback Staff PIN

        if staff_pin == target_staff_pin:
            st.session_state.staff_authenticated = True
            st.sidebar.success("🔑 Terminal Authenticated")
            app_mode = "🍔 Clubhouse F&B Terminal"
        elif staff_pin != "":
            st.sidebar.error("❌ Invalid Staff PIN.")
            app_mode = "🏌️ Player Scorecard Portal"
        else:
            st.sidebar.info("🔒 Enter PIN to unlock till.")
            app_mode = "🏌️ Player Scorecard Portal"

    else:
        # Secure the administrative side behind the master operational PIN
        admin_pin = st.sidebar.text_input("Enter Admin Operational PIN:", type="password")
        
        try:
            target_pin = st.secrets["admin"]["pin"]
        except Exception:
            target_pin = "1800"

        if admin_pin == target_pin:
            st.session_state.admin_authenticated = True
            
            # --- 🎛️ SIDEBAR TOGGLES (THE LIVE FIELD CONTROLS) ---
            st.sidebar.subheader("🎛️ Live Field Controls")
            
            st.session_state.suspense_mode = st.sidebar.toggle(
                "🔒 Enable Suspense Mode", 
                value=st.session_state.suspense_mode,
                help="When enabled, hides the top 3 podium names from players until the tournament finishes."
            )
            
            st.session_state.enable_overrides = st.sidebar.toggle(
                "🛠️ Captain's Desk Overrides",
                value=st.session_state.enable_overrides,
                help="Toggle on to adjust active player profiles, playing handicaps, and round configurations."
            )
            
            st.session_state.enable_podium = st.sidebar.toggle(
                "🏆 Review Podium Winners Now",
                value=st.session_state.enable_podium,
                help="Toggle on to auto-calculate Best Gross, Best Net, and Net Runner-Up."
            )
            
            st.session_state.enable_shootout = st.sidebar.toggle(
                "🏁 Enable Final 3-Hole Playoff",
                value=st.session_state.enable_shootout,
                help="Toggle on to run a sudden-death playoff scorecard tracker on Holes 16, 17, and 18."
            )
            
            st.sidebar.markdown("---")
            
            # Master Admin Selection Menu
            app_mode = st.sidebar.selectbox(
                "Select Admin Console:",
                [
                    "🏆 Tournament Leaderboard Monitor",
                    "👥 Society Roster Manager",
                    "⚙️ Tournament Match Play Control",
                    "⚙️ Course Directory Setup"
                ]
            )
        elif admin_pin != "":
            st.sidebar.error("❌ Invalid Administrative PIN.")
            app_mode = "🏌️ Player Scorecard Portal"

# 🚦 MODULE EXECUTION ROUTER via Imports
if app_mode == "🏌️ Player Scorecard Portal":
    from views.scorecard_terminal import render_scorecard_input
    render_scorecard_input(DB_FILE, ACTIVE_PARS)

elif app_mode == "🍔 Clubhouse F&B Terminal" and st.session_state.get("staff_authenticated", False):
    from views.fandb_terminal import render_fb_pos
    render_fb_pos(POS_FILE, DB_FILE)

elif app_mode == "🏆 Tournament Leaderboard Monitor":
    from views.leaderboard import render_league_leaderboard
    render_league_leaderboard(season_id="2026_S1", conn=conn)

elif app_mode == "👥 Society Roster Manager":
    from views.roster_manager import render_roster_uploader
    render_roster_uploader(season_id="2026_S1", conn=conn)

elif app_mode == "⚙️ Tournament Match Play Control":
    from views.admin_panel import render_admin_panel
    render_admin_panel(admin_mode=None, DB_FILE=DB_FILE)

elif app_mode == "⚙️ Course Directory Setup":
    from views.course_manager import render_course_manager
    render_course_manager()

# --- DYNAMIC PERSISTENT OVERLAYS ---
if st.session_state.get("admin_authenticated", False):
    if st.session_state.get("enable_overrides", False):
        from views.admin_panel import render_admin_panel
        st.markdown("---")
        render_admin_panel(admin_mode="🛠️ Captain's Desk Overrides", DB_FILE=DB_FILE)
        
    if st.session_state.get("enable_podium", False):
        from views.admin_panel import render_admin_panel
        st.markdown("---")
        render_admin_panel(admin_mode="Review podium winners", DB_FILE=DB_FILE)
        
    if st.session_state.get("enable_shootout", False):
        from views.admin_panel import render_admin_panel
        st.markdown("---")
        render_admin_panel(admin_mode="enable final 3hole", DB_FILE=DB_FILE)

# =====================================================================
# 🏁 GLOBAL FOOTER & COPYRIGHT (Place at the absolute end of app.py)
# =====================================================================
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888888; font-size: 0.85em; margin-top: 30px;">
        © 2026 <b>FairwayIQ</b>. All Rights Reserved.<br>
        <span style="font-size: 0.9em;">Designed & Developed by Martha Ngaithe</span>
    </div>
    """, 
    unsafe_allow_html=True
)