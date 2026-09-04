import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from core.database import get_db_connection, get_course_pars_and_si

# ============================================================
# KENYAN CLUBS & COMPETITIONS
# ============================================================
KENYAN_GOLF_CLUBS = {
    "Nairobi Region": [
        "Golf Park", "Karen Country Club", "Kenya Airforce Golf Club", "Kenya Railway Golf Course",
        "Kiambu Golf Club", "Limuru Country Club", "Machakos Golf Club", "Muthaiga Golf Club",
        "Ndumberi Golf Club", "Royal Nairobi Golf Club", "Ruiru Sports Club", "Sigona Golf Club",
        "Thika Barracks Golf Club", "Thika Greens Golf Resort", "Thika Sports Club", "VetLab Sports Club",
        "Windsor Golf Hotel & Country Club", "Migaa Golf Club"
    ],
    "Mt. Kenya Region": ["Nanyuki Sports Club", "Nyahururu Country Club", "Nyeri Golf Club"],
    "Central Rift": [
        "Gilgil Country Club", "Great Rift Valley Golf Resort", "Naivasha Sports Club",
        "Nakuru Golf Club", "Njoro Country Club", "Mt. Kipipiri Golf Resort"
    ],
    "Coast": [
        "Leisure Lodge Golf Club", "Malindi Golf Club", "Mombasa Golf Club",
        "Nyali Golf & Country Club Ltd", "Vipingo Ridge"
    ],
    "Western": ["Kakamega Golf Club", "Kisii Golf Club", "Mumias Golf Club", "Nyanza Golf Club"],
    "North Rift": ["Eldoret Golf Club", "Kericho Golf Course", "Kitale Club", "Nandi Bears Golf Club"]
}

ALL_KENYAN_CLUBS_FLAT = sorted([club for region in KENYAN_GOLF_CLUBS.values() for club in region])

KENYAN_COMPETITIONS = [
    "Club Nite (Stableford)", "Club Monthly Mug",
    "NCBA Golf Series", "KCB Golf Series", "ABSA Golf Day", "ICEA Lion Golf Tournament",
    "Britam Golf Series", "CIC Golf Day", "Safaricom Golf Day",
    "Sigona Open (KAGC)", "Muthaiga Open (KAGC)", "Karen Open (KAGC)",
    "Nakuru Open (KAGC)", "Limuru Open (KAGC)", "Nyali Open (KAGC)",
    "Magical Kenya Open (DP World Tour)", "Casual Round"
]


# ============================================================
# MASTER SCORECARD (Paper-style)
# ============================================================
def render_master_scorecard(player_name, handicap, course, tee, competition,
                            hole_scores, active_pars, round_variant="Full 18 Holes"):
    """Professional paper-style Master Scorecard"""

    active_limit = 9 if round_variant == "Front 9 Only" else 18
    holes = list(range(1, active_limit + 1))

    front_holes = list(range(1, 10))
    back_holes = list(range(10, 19)) if active_limit == 18 else []

    front_score = sum(hole_scores.get(h, active_pars.get(h, 4)) for h in front_holes)
    back_score = sum(hole_scores.get(h, active_pars.get(h, 4)) for h in back_holes) if back_holes else 0
    total_score = front_score + back_score

    front_par = sum(active_pars.get(h, 4) for h in front_holes)
    back_par = sum(active_pars.get(h, 4) for h in back_holes) if back_holes else 0
    total_par = front_par + back_par

    # Header
    st.markdown(f"""
    <div style="background:#0f172a; color:white; padding:16px 20px; border-radius:12px 12px 0 0;">
        <h3 style="margin:0 0 6px 0; color:#4ade80;">⛳ FairwayIQ Official Scorecard</h3>
        <p style="margin:0; font-size:0.95rem; color:#cbd5e1;">
            <strong>{player_name}</strong> &nbsp;|&nbsp; HCP: {handicap} &nbsp;|&nbsp;
            {course} ({tee}) &nbsp;|&nbsp; {competition}<br>
            Date: {datetime.now().strftime('%d %b %Y')}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Build data
    data = {"Hole": [], "Par": [], "Score": [], "+/-": []}

    for h in holes:
        par = active_pars.get(h, 4)
        score = hole_scores.get(h, par)
        diff = score - par
        data["Hole"].append(h)
        data["Par"].append(par)
        data["Score"].append(score)
        data["+/-"].append(f"+{diff}" if diff > 0 else ("E" if diff == 0 else str(diff)))

    # OUT / IN / TOTAL
    if active_limit == 18:
        data["Hole"].extend(["OUT", "IN", "TOTAL"])
        data["Par"].extend([front_par, back_par, total_par])
        data["Score"].extend([front_score, back_score, total_score])
        front_diff = front_score - front_par
        back_diff = back_score - back_par
        total_diff = total_score - total_par
        data["+/-"].extend([
            f"+{front_diff}" if front_diff > 0 else ("E" if front_diff == 0 else str(front_diff)),
            f"+{back_diff}" if back_diff > 0 else ("E" if back_diff == 0 else str(back_diff)),
            f"+{total_diff}" if total_diff > 0 else ("E" if total_diff == 0 else str(total_diff))
        ])
    else:
        data["Hole"].extend(["OUT", "TOTAL"])
        data["Par"].extend([front_par, total_par])
        data["Score"].extend([front_score, total_score])
        front_diff = front_score - front_par
        total_diff = total_score - total_par
        data["+/-"].extend([
            f"+{front_diff}" if front_diff > 0 else ("E" if front_diff == 0 else str(front_diff)),
            f"+{total_diff}" if total_diff > 0 else ("E" if total_diff == 0 else str(total_diff))
        ])

    df = pd.DataFrame(data)

    def style_row(row):
        styles = [""] * len(row)
        if str(row["Hole"]) in ["OUT", "IN", "TOTAL"]:
            styles = ["background-color:#1e293b; color:white; font-weight:700;"] * len(row)
        else:
            try:
                hole_num = int(row["Hole"])
                par = active_pars.get(hole_num, 4)
                score = int(row["Score"])
                diff = score - par
                if diff <= -1:
                    styles[2] = "background-color:#bbf7d0; color:#166534; font-weight:600;"
                elif diff == 0:
                    styles[2] = "background-color:#f8fafc; color:#1e293b;"
                elif diff == 1:
                    styles[2] = "background-color:#fef9c3; color:#854d0e;"
                else:
                    styles[2] = "background-color:#fecaca; color:#991b1b; font-weight:600;"
            except:
                pass
        return styles

    styled = df.style.apply(style_row, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True, height=420)

    # Summary metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gross Score", total_score)
    c2.metric("vs Par", f"+{total_diff}" if total_diff > 0 else total_diff)
    c3.metric("Net Score", int(total_score - handicap))
    c4.metric("Holes Played", active_limit)


# ============================================================
# MAIN SCORECARD FUNCTION
# ============================================================
def render_scorecard_input(DB_FILE, FALLBACK_PARS):
    st.title("⛳ FairwayIQ Digital Scorecard & Live Database")
    st.caption("Welcome to the Scoring Portal")

    conn = get_db_connection()

    try:
        courses_df = pd.read_sql_query("SELECT DISTINCT course_name FROM golf_courses", conn)
        course_options = courses_df['course_name'].tolist() if not courses_df.empty else ["Limuru Country Club"]
    except Exception:
        course_options = ["Limuru Country Club"]

    # Session defaults
    defaults = {
        "authorized": False,
        "auth_type": None,
        "player_name": "",
        "player_id": 1,
        "player_hcp": 10,
        "selected_course": course_options[0],
        "selected_tee": "White",
        "competition": "Casual Round",
        "current_hole": 1,
        "round_variant": "Full 18 Holes",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Dynamic pars
    try:
        raw_map = get_course_pars_and_si(st.session_state.selected_course, st.session_state.selected_tee)
        if raw_map:
            ACTIVE_PARS = {h: v[0] for h, v in raw_map.items()}
            ACTIVE_SI = {h: v[1] for h, v in raw_map.items()}
        else:
            ACTIVE_PARS = FALLBACK_PARS
            ACTIVE_SI = {h: h for h in range(1, 19)}
    except Exception:
        ACTIVE_PARS = FALLBACK_PARS
        ACTIVE_SI = {h: h for h in range(1, 19)}

    if 'hole_scores' not in st.session_state or len(st.session_state.hole_scores) != 18:
        st.session_state.hole_scores = {h: ACTIVE_PARS.get(h, 4) for h in range(1, 19)}

    # ============================================================
    # PHASE 1: GATE CHECK-IN
    # ============================================================
    if not st.session_state.authorized:
        st.markdown("---")
        st.subheader("🔒 Tournament Gate Check-in")
        st.write("Please select your registration type to unlock your portal view.")

        player_type = st.radio(
            "Select Registration Type:",
            ["Club Member", "Visiting Player", "Sponsor / Guest (Non-Playing)", "Club Management / Admin"],
            horizontal=True
        )

        if player_type == "Club Member":
            input_id = st.number_input("Enter your Club Member ID:", min_value=1, max_value=9999, step=1)
            input_name = st.text_input("Enter Registered Full Name:")
            input_hcp = st.number_input("Verified Club Handicap:", min_value=0, max_value=54, value=12, step=1)

            c1, c2 = st.columns(2)
            with c1:
                region = st.selectbox("Select Club Region:", list(KENYAN_GOLF_CLUBS.keys()))
            with c2:
                reg_course = st.selectbox("Select Golf Club Playing Today:", KENYAN_GOLF_CLUBS[region])

            reg_tee = st.selectbox("Select Tee Set Played:", ["White", "Yellow", "Red", "Blue"])
            comp_type = st.selectbox("Select Active Competition / Event:", KENYAN_COMPETITIONS)
            variant = st.selectbox("Select Planned Round Format:", ["Full 18 Holes", "Front 9 Only"])

            if st.button("Verify & Unlock Scorecard", type="primary"):
                if input_name.strip():
                    st.session_state.authorized = True
                    st.session_state.auth_type = "Member"
                    st.session_state.player_id = input_id
                    st.session_state.player_name = input_name
                    st.session_state.player_hcp = input_hcp
                    st.session_state.selected_course = reg_course
                    st.session_state.selected_tee = reg_tee
                    st.session_state.competition = comp_type
                    st.session_state.round_variant = variant
                    st.session_state.hole_scores = {h: ACTIVE_PARS.get(h, 4) for h in range(1, 19)}
                    st.rerun()
                else:
                    st.error("Please enter your full name.")

        elif player_type == "Visiting Player":
            input_name = st.text_input("Visitor Full Name:")
            visitor_home = st.selectbox("Select Your Official Home Club:", ALL_KENYAN_CLUBS_FLAT)

            c1, c2 = st.columns(2)
            with c1:
                region = st.selectbox("Select Playing Club Region:", list(KENYAN_GOLF_CLUBS.keys()))
            with c2:
                reg_course = st.selectbox("Select Venue Playing Today:", KENYAN_GOLF_CLUBS[region])

            reg_tee = st.selectbox("Select Tee Set Played:", ["White", "Yellow", "Red", "Blue"])
            visitor_hcp = st.number_input("Official Handicap Index:", min_value=0, max_value=54, step=1)
            comp_type = st.selectbox("Select Active Competition / Event:", KENYAN_COMPETITIONS)
            variant = st.selectbox("Select Planned Round Format:", ["Full 18 Holes", "Front 9 Only"])

            if st.button("Register Guest Competitor", type="primary"):
                if input_name.strip():
                    st.session_state.authorized = True
                    st.session_state.auth_type = "Visitor"
                    st.session_state.player_id = 9000 + visitor_hcp
                    st.session_state.player_name = f"{input_name} ({visitor_home})"
                    st.session_state.player_hcp = visitor_hcp
                    st.session_state.selected_course = reg_course
                    st.session_state.selected_tee = reg_tee
                    st.session_state.competition = comp_type
                    st.session_state.round_variant = variant
                    st.session_state.hole_scores = {h: ACTIVE_PARS.get(h, 4) for h in range(1, 19)}
                    st.rerun()
                else:
                    st.error("Please enter your name.")

        elif player_type == "Sponsor / Guest (Non-Playing)":
            st.info("👋 Welcome! Scorecard access is restricted to playing competitors. Please view the live leaderboard at the club lounge.")

        elif player_type == "Club Management / Admin":
            st.subheader("🔑 Executive Portal Verification")
            admin_pin = st.text_input("Enter Management Credentials / PIN:", type="password")

            if st.button("Authenticate Admin Console", type="primary"):
                try:
                    target_pin = st.secrets["admin"]["pin"]
                except Exception:
                    target_pin = "1800"

                if admin_pin == target_pin:
                    st.session_state.authorized = True
                    st.session_state.auth_type = "Admin"
                    st.session_state.player_id = 0
                    st.session_state.player_name = "System Administrator"
                    st.rerun()
                else:
                    st.error("Invalid PIN")

    # ============================================================
    # PHASE 2: AUTHORIZED PLAYER / ADMIN
    # ============================================================
    else:
        if st.button("🔄 Logout / Reset"):
            st.session_state.authorized = False
            st.session_state.auth_type = None
            st.session_state.current_hole = 1
            st.rerun()

        if st.session_state.auth_type == "Admin":
            st.header("📊 FairwayIQ Executive Dashboard")
            st.info("Use the main Admin Console for full tools.")
        else:
            # Player Header
            st.markdown(f"""
            <div style="background:#f0fdf4; border:1px solid #86efac; border-radius:12px; padding:16px 20px; margin-bottom:20px;">
                <h3 style="margin:0 0 6px 0; color:#166534;">⛳ {st.session_state.player_name}</h3>
                <p style="margin:0; color:#374151;">
                    <strong>HCP:</strong> {st.session_state.player_hcp} &nbsp;|&nbsp;
                    <strong>Playing:</strong> {st.session_state.selected_course} ({st.session_state.selected_tee}) &nbsp;|&nbsp;
                    <strong>Event:</strong> {st.session_state.competition}
                </p>
            </div>
            """, unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["📝 Live Scorecard", "🍔 Pre-Order to the Turn"])

            with tab1:
                current_h = st.session_state.current_hole
                active_limit = 9 if st.session_state.round_variant == "Front 9 Only" else 18
                relevant = list(range(1, active_limit + 1))

                front_total = sum(st.session_state.hole_scores[h] for h in range(1, 10))
                back_total = sum(st.session_state.hole_scores[h] for h in range(10, 19))
                gross = front_total + back_total

                front_par = sum(ACTIVE_PARS.get(h, 4) for h in range(1, 10))
                back_par = sum(ACTIVE_PARS.get(h, 4) for h in range(10, 19))
                total_par = front_par + back_par

                front_vs = front_total - front_par
                back_vs = back_total - back_par
                total_vs = gross - total_par

                hcp = st.session_state.player_hcp / 2 if st.session_state.round_variant == "Front 9 Only" else st.session_state.player_hcp
                net = gross - hcp

                # Front / Back cards
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"""
                    <div style="background:#eff6ff; border:1px solid #93c5fd; border-radius:10px; padding:16px; text-align:center;">
                        <h4 style="margin:0 0 6px 0; color:#1e40af;">FRONT 9</h4>
                        <p style="font-size:1.7rem; font-weight:700; margin:0;">{front_total}</p>
                        <p style="margin:4px 0;">vs Par: {"+" if front_vs > 0 else ""}{front_vs}</p>
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                    <div style="background:#fef3c7; border:1px solid #fcd34d; border-radius:10px; padding:16px; text-align:center;">
                        <h4 style="margin:0 0 6px 0; color:#92400e;">BACK 9</h4>
                        <p style="font-size:1.7rem; font-weight:700; margin:0;">{back_total}</p>
                        <p style="margin:4px 0;">vs Par: {"+" if back_vs > 0 else ""}{back_vs}</p>
                    </div>
                    """, unsafe_allow_html=True)

                st.write("")

                # How did I do?
                birdies = sum(1 for h in relevant if st.session_state.hole_scores[h] == ACTIVE_PARS.get(h, 4) - 1)
                pars = sum(1 for h in relevant if st.session_state.hole_scores[h] == ACTIVE_PARS.get(h, 4))
                bogeys = sum(1 for h in relevant if st.session_state.hole_scores[h] == ACTIVE_PARS.get(h, 4) + 1)
                doubles = sum(1 for h in relevant if st.session_state.hole_scores[h] >= ACTIVE_PARS.get(h, 4) + 2)

                st.markdown(f"""
                <div style="background:#f0fdf4; border:1px solid #86efac; border-radius:12px; padding:18px; margin-bottom:20px;">
                    <h4 style="margin:0 0 10px 0; color:#166534;">📊 How did I do?</h4>
                    <p style="margin:4px 0;"><strong>Gross:</strong> {gross} &nbsp;|&nbsp; <strong>Net:</strong> {int(net)} &nbsp;|&nbsp; <strong>vs Par:</strong> {"+" if total_vs > 0 else ""}{total_vs}</p>
                    <p style="margin:8px 0 0 0;">🐦 Birdies: <strong>{birdies}</strong> &nbsp;&nbsp; ⬜ Pars: <strong>{pars}</strong> &nbsp;&nbsp; ⬛ Bogeys: <strong>{bogeys}</strong> &nbsp;&nbsp; 🔴 Double+: <strong>{doubles}</strong></p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("---")

                # Hole entry
                if current_h <= active_limit:
                    st.subheader(f"🏌️ Hole {current_h}")

                    c1, c2, c3 = st.columns(3)
                    c1.info(f"**Par {ACTIVE_PARS.get(current_h, 4)}** | SI {ACTIVE_SI.get(current_h, current_h)}")
                    c2.metric("Your Score", st.session_state.hole_scores[current_h])
                    c3.caption(st.session_state.competition)

                    score = st.number_input(
                        "Enter Gross Strokes:",
                        min_value=1, max_value=15,
                        value=int(st.session_state.hole_scores[current_h]),
                        key=f"score_{current_h}"
                    )
                    st.session_state.hole_scores[current_h] = score

                    b1, b2 = st.columns(2)
                    with b1:
                        if current_h > 1 and st.button("⬅️ Previous", use_container_width=True):
                            st.session_state.current_hole -= 1
                            st.rerun()
                    with b2:
                        if current_h < active_limit:
                            if st.button("Save & Next ➡️", type="primary", use_container_width=True):
                                st.session_state.current_hole += 1
                                st.rerun()
                        else:
                            if st.button("🏁 Finish Round", type="primary", use_container_width=True):
                                st.session_state.current_hole = 19
                                st.rerun()

                # Final Review + Master Scorecard
                else:
                    st.success(f"🎉 Round Complete! ({st.session_state.round_variant})")

                    render_master_scorecard(
                        player_name=st.session_state.player_name,
                        handicap=st.session_state.player_hcp,
                        course=st.session_state.selected_course,
                        tee=st.session_state.selected_tee,
                        competition=st.session_state.competition,
                        hole_scores=st.session_state.hole_scores,
                        active_pars=ACTIVE_PARS,
                        round_variant=st.session_state.round_variant
                    )

                    with st.form("submit_form"):
                        marker = st.selectbox(
                            "Select Official Marker:",
                            ["Choose marker...", "John Mwangi", "Alice Koech", "David Ochieng", "Martha Njeri", "Peter Kamau"]
                        )
                        if st.form_submit_button("🚀 Submit to Live Leaderboard", type="primary", use_container_width=True):
                            if marker == "Choose marker...":
                                st.error("Please select a marker.")
                            else:
                                new_row = pd.DataFrame([{
                                    "MemberID": st.session_state.player_id,
                                    "PlayerName": st.session_state.player_name,
                                    "Course": st.session_state.selected_course,
                                    "Handicap": hcp,
                                    "Score": gross,
                                    "Competition": st.session_state.competition,
                                    "MarkerVerification": marker,
                                    "PlayDate": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                }])
                                os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
                                if os.path.exists(DB_FILE):
                                    new_row.to_csv(DB_FILE, mode='a', header=False, index=False)
                                else:
                                    new_row.to_csv(DB_FILE, mode='w', header=True, index=False)
                                st.success("✅ Scorecard submitted successfully!")
                                st.session_state.current_hole = 1
                                st.session_state.hole_scores = {h: ACTIVE_PARS.get(h, 4) for h in range(1, 19)}
                                st.rerun()

            with tab2:
                st.subheader("🍔 Pre-Order to the Turn")
                st.info("Order food while playing. It will be ready at the Halfway House.")

    conn.close()