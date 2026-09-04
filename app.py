import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import os
from core.database import init_db, get_db_connection, get_course_pars_and_si

# ============================================================
# 1. PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="FairwayIQ Master Hub",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================
# 2. PWA + OFFLINE ENGINE
# ============================================================
def enable_pwa_with_offline_cache(player_id="1", current_hole=1, current_scores=None):
    if current_scores is None:
        current_scores = {}
    scores_json = json.dumps(current_scores)

    pwa_offline_html = f"""
    <div id="pwa-install-banner" style="display: none; background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); color: #fff; padding: 12px 16px; border-radius: 12px; margin-bottom: 12px; border: 1px solid #334155; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; align-items: center; justify-content: space-between; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        <div>
            <h5 style="margin: 0 0 2px 0; color: #4ade80; font-size: 13px; font-weight: 700;">📲 Install FairwayIQ App</h5>
            <p style="margin: 0; font-size: 11px; color: #94a3b8;">Add to home screen for off-grid course scoring.</p>
        </div>
        <button id="pwa-install-btn" style="padding: 8px 14px; background: #16a34a; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 12px; cursor: pointer;">
            Install
        </button>
    </div>

    <div id="pwa-score-card" style="background: #0f172a; color: #f8fafc; padding: 16px; border-radius: 12px; margin: 10px 0; border: 1px solid #1e293b;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h4 style="margin: 0; color: #4ade80; font-size: 16px;">⛳ Mobile Offline Scorecard</h4>
            <span id="pwa-sync-pill" style="font-size: 10px; padding: 2px 8px; border-radius: 12px; background: #334155; color: #94a3b8; font-weight: bold;">READY</span>
        </div>
        
        <div style="display: flex; gap: 12px; margin-bottom: 14px;">
            <div style="flex: 1;">
                <label style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 4px;">Hole</label>
                <input type="number" id="pwa-hole-num" value="{current_hole}" min="1" max="18" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid #334155; background: #1e293b; color: #fff;">
            </div>
            <div style="flex: 1;">
                <label style="font-size: 11px; color: #94a3b8; display: block; margin-bottom: 4px;">Strokes</label>
                <input type="number" id="pwa-score-val" value="4" min="1" max="15" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid #334155; background: #1e293b; color: #fff;">
            </div>
        </div>
        
        <button onclick="saveScoreOffline()" style="width: 100%; padding: 12px; background: linear-gradient(135deg, #16a34a 0%, #15803d 100%); color: white; border: none; border-radius: 8px; font-weight: 700; cursor: pointer;">
            💾 Save Score (Offline Guaranteed)
        </button>
        <p id="pwa-status-msg" style="font-size: 12px; color: #94a3b8; margin: 10px 0 0 0; text-align: center;"></p>
    </div>

    <script>
    const currentHost = window.parent.location.hostname || window.location.hostname || 'localhost';
    const API_ENDPOINT = `http://${{currentHost}}:8000/api/sync_scorecard`;
    const PLAYER_ID = "{player_id}";
    const STORAGE_KEY = `fairwayiq_scores_${{PLAYER_ID}}`;

    const targetDoc = window.parent.document || document;
    if (!targetDoc.querySelector('link[rel="manifest"]')) {{
        const manifestLink = targetDoc.createElement('link');
        manifestLink.rel = 'manifest';
        manifestLink.href = 'data:application/json;base64,eyJzaG9ydF9uYW1lIjoiRmFpcndheUlRIiwibmFtZSI6IkZhaXJ3YXlJUSBHb2xmIFJldmVudWUgJiBPcGVyYXRpb25zIiwiaWNvbnMiOlt7InNyYyI6Imh0dHBzOi8vY2RuLWljb25zLXBuZy5mbGF0aWNvbi5jb20vNTEyLzMwNzYvMzA3NjQxMy5wbmciLCJ0eXBlIjoiaW1hZ2UvcG5nIiwic2l6ZXMiOiIxOTJ4MTkyIn0seyJzcmMiOiJodHRwczovL2Nkbi1pY29ucy1wbmcuZmxhdGljb24uY29tLzUxMi8zMDc2LzMwNzY0MTMucG5nIiwidHlwZSI6ImltYWdlL3BuZyIsInNpemVzIjo1MTJ4NTEyfV0sInN0YXJ0X3VybCI6Ii8iLCJiYWNrZ3JvdW5kX2NvbG9yIjoiI2ZmZmZmZiIsInRoZW1lX2NvbG9yIjoiIzBiM2QyZSIsImRpc3BsYXkiOiJzdGFuZGFsb25lIn0=';
        targetDoc.head.appendChild(manifestLink);
    }}

    let deferredPrompt;
    window.addEventListener('beforeinstallprompt', (e) => {{
        e.preventDefault();
        deferredPrompt = e;
        const banner = document.getElementById('pwa-install-banner');
        if (banner) banner.style.display = 'flex';
    }});

    document.addEventListener('DOMContentLoaded', () => {{
        const installBtn = document.getElementById('pwa-install-btn');
        if (installBtn) {{
            installBtn.addEventListener('click', async () => {{
                if (!deferredPrompt) return;
                deferredPrompt.prompt();
                await deferredPrompt.userChoice;
                deferredPrompt = null;
                document.getElementById('pwa-install-banner').style.display = 'none';
            }});
        }}
    }});

    function saveScoreOffline() {{
        const holeNum = document.getElementById('pwa-hole-num').value;
        const scoreVal = document.getElementById('pwa-score-val').value;
        const statusMsg = document.getElementById('pwa-status-msg');
        const pill = document.getElementById('pwa-sync-pill');

        try {{
            const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{{ "scores": {{}}, "unsynced": false }}');
            data.scores[holeNum] = {{ score: parseInt(scoreVal), ts: new Date().toISOString() }};
            data.unsynced = true;
            localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
            
            statusMsg.style.color = '#4ade80';
            statusMsg.innerText = `Saved Hole ${{holeNum}} (${{scoreVal}} strokes) locally!`;
            pill.style.background = '#d97706';
            pill.style.color = '#fff';
            pill.innerText = 'QUEUED';
        }} catch (e) {{
            statusMsg.style.color = '#f87171';
            statusMsg.innerText = 'Error saving locally.';
        }}
    }}
    </script>
    """
    components.html(pwa_offline_html, height=270)


# ============================================================
# 3. DATABASE & COURSE SETUP
# ============================================================
init_db()
conn = get_db_connection()

DB_FILE = "data/live_leaderboard.csv"
POS_FILE = "data/pos_transactions.csv"

try:
    dynamic_course_map = get_course_pars_and_si("Limuru Country Club", "White")
    ACTIVE_PARS = {hole: values[0] for hole, values in dynamic_course_map.items()}
except Exception:
    ACTIVE_PARS = {
        1: 4, 2: 4, 3: 3, 4: 5, 5: 4, 6: 4, 7: 3, 8: 4, 9: 5,
        10: 4, 11: 4, 12: 3, 13: 5, 14: 4, 15: 4, 16: 3, 17: 4, 18: 5
    }


# ============================================================
# 4. SESSION STATE
# ============================================================
defaults = {
    "authorized": False,
    "auth_type": None,
    "player_name": "",
    "player_id": 1,
    "player_hcp": 10,
    "home_club": "Thika Sports Club",
    "competition": "Casual Round",
    "current_hole": 1,
    "hole_scores": {h: ACTIVE_PARS[h] for h in range(1, 19)},
    "admin_authenticated": False,
    "staff_authenticated": False,
    "suspense_mode": True,
    "enable_overrides": False,
    "enable_podium": False,
    "enable_shootout": False,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# 5. ROLE-BASED ACCESS CONTROL
# ============================================================
def require_role(allowed_roles: list):
    current_role = st.session_state.get("auth_type")
    if current_role not in allowed_roles:
        st.error("⛔ Access Denied")
        st.warning(f"Required role(s): {', '.join(allowed_roles)}")
        st.info(f"Your current role: **{current_role or 'Not logged in'}**")
        st.stop()


# ============================================================
# 6. GATEWAY / LOGIN (Centered Professional Design)
# ============================================================
app_mode = None

# Show login gateway only if user is not authenticated
if not (st.session_state.get("authorized") or 
        st.session_state.get("staff_authenticated") or 
        st.session_state.get("admin_authenticated")):

    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        st.markdown("""
            <div style="text-align: center; margin-top: 40px; margin-bottom: 20px;">
                <h1 style="color: #4ade80; font-size: 2.4rem; font-weight: 700; margin-bottom: 6px;">
                    ⛳ FairwayIQ
                </h1>
                <p style="color: #94a3b8; font-size: 1.05rem;">
                    Golf Revenue & Operations Intelligence
                </p>
            </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### 🏁 FairwayIQ Gateway")
            st.caption("Select Portal Role to continue")

            user_role = st.selectbox(
                "Select Portal Role:",
                [
                    "🏌️ Golfer / Caddie Terminal",
                    "🍔 Clubhouse F&B Terminal",
                    "🛡️ Tournament Administration"
                ],
                label_visibility="collapsed"
            )

            st.markdown("---")

            # GOLFER
            if user_role == "🏌️ Golfer / Caddie Terminal":
                from views.gate_checkin import render_gate_checkin
                render_gate_checkin()

            # F&B STAFF
            elif user_role == "🍔 Clubhouse F&B Terminal":
                staff_pin = st.text_input("Enter F&B Staff PIN", type="password", placeholder="Enter PIN")

                try:
                    target_staff_pin = st.secrets["staff"]["pin"]
                except Exception:
                    target_staff_pin = "2026"

                if st.button("Login to F&B Terminal", type="primary", use_container_width=True):
                    if staff_pin == target_staff_pin:
                        st.session_state.staff_authenticated = True
                        st.session_state.auth_type = "staff"
                        st.rerun()
                    else:
                        st.error("Invalid Staff PIN")

            # ADMIN
            else:
                admin_pin = st.text_input("Enter Admin Operational PIN", type="password", placeholder="Enter PIN")

                try:
                    target_pin = st.secrets["admin"]["pin"]
                except Exception:
                    target_pin = "1800"

                if st.button("Login to Admin Console", type="primary", use_container_width=True):
                    if admin_pin == target_pin:
                        st.session_state.admin_authenticated = True
                        st.session_state.auth_type = "admin"
                        st.rerun()
                    else:
                        st.error("Invalid Administrative PIN")

        st.markdown("""
            <div style="text-align: center; margin-top: 25px; color: #64748b; font-size: 0.85rem;">
                © 2026 FairwayIQ · Designed & Developed by Martha Ngaithe
            </div>
        """, unsafe_allow_html=True)

    st.stop()   # Critical: stop here until user logs in


# ============================================================
# 7. AFTER LOGIN - SHOW SIDEBAR + CONTENT
# ============================================================

# Activate PWA only after login
enable_pwa_with_offline_cache(
    player_id=st.session_state.player_id,
    current_hole=st.session_state.current_hole,
    current_scores=st.session_state.hole_scores
)

# Sidebar after login
st.sidebar.title("⛳ FairwayIQ")
st.sidebar.success(f"Logged in as: **{st.session_state.auth_type.upper()}**")

if st.sidebar.button("🚪 Logout"):
    for key in ["authorized", "staff_authenticated", "admin_authenticated", "auth_type"]:
        st.session_state[key] = False if key != "auth_type" else None
    st.rerun()

st.sidebar.markdown("---")

# Determine app_mode based on role
if st.session_state.auth_type == "player":
    app_mode = "🏌️ Player Scorecard Portal"

elif st.session_state.auth_type == "staff":
    app_mode = "🍔 Clubhouse F&B Terminal"

elif st.session_state.auth_type == "admin":
    st.sidebar.subheader("🎛️ Live Field Controls")

    st.session_state.suspense_mode = st.sidebar.toggle(
        "🔒 Enable Suspense Mode", value=st.session_state.suspense_mode
    )
    st.session_state.enable_overrides = st.sidebar.toggle(
        "🛠️ Captain's Desk Overrides", value=st.session_state.enable_overrides
    )
    st.session_state.enable_podium = st.sidebar.toggle(
        "🏆 Review Podium Winners", value=st.session_state.enable_podium
    )
    st.session_state.enable_shootout = st.sidebar.toggle(
        "🏁 Final 3-Hole Playoff", value=st.session_state.enable_shootout
    )

    st.sidebar.markdown("---")

    app_mode = st.sidebar.selectbox(
        "Select Admin Console:",
        [
            "🏆 Tournament Leaderboard Monitor",
            "👥 Society Roster Manager",
            "⚙️ Tournament Match Play Control",
            "⚙️ Course Directory Setup"
        ]
    )
else:
    app_mode = None


# ============================================================
# 8. MODULE ROUTER + ROLE PROTECTION
# ============================================================
if app_mode == "🏌️ Player Scorecard Portal":
    require_role(["player", "admin"])
    from views.scorecard_terminal import render_scorecard_input
    render_scorecard_input(DB_FILE, ACTIVE_PARS)

elif app_mode == "🍔 Clubhouse F&B Terminal":
    require_role(["staff", "admin"])
    from views.fandb_terminal import render_fb_pos
    render_fb_pos(POS_FILE, DB_FILE)

elif app_mode == "🏆 Tournament Leaderboard Monitor":
    require_role(["admin"])
    from views.leaderboard import render_league_leaderboard
    render_league_leaderboard(season_id="2026_S1", conn=conn)

elif app_mode == "👥 Society Roster Manager":
    require_role(["admin"])
    from views.roster_manager import render_roster_uploader
    render_roster_uploader(season_id="2026_S1", conn=conn)

elif app_mode == "⚙️ Tournament Match Play Control":
    require_role(["admin"])
    from views.admin_panel import render_admin_panel
    render_admin_panel(admin_mode=None, DB_FILE=DB_FILE)

elif app_mode == "⚙️ Course Directory Setup":
    require_role(["admin"])
    from views.course_manager import render_course_manager
    render_course_manager()


# ============================================================
# 9. ADMIN OVERLAYS
# ============================================================
if st.session_state.get("admin_authenticated"):
    if st.session_state.get("enable_overrides"):
        from views.admin_panel import render_admin_panel
        st.markdown("---")
        render_admin_panel(admin_mode="🛠️ Captain's Desk Overrides", DB_FILE=DB_FILE)

    if st.session_state.get("enable_podium"):
        from views.admin_panel import render_admin_panel
        st.markdown("---")
        render_admin_panel(admin_mode="Review podium winners", DB_FILE=DB_FILE)

    if st.session_state.get("enable_shootout"):
        from views.admin_panel import render_admin_panel
        st.markdown("---")
        render_admin_panel(admin_mode="enable final 3hole", DB_FILE=DB_FILE)


# ============================================================
# 10. FOOTER
# ============================================================
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