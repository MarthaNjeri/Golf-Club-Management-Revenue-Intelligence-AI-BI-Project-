import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import sqlite3
from core.database import get_db_connection, get_course_pars_and_si

# --- DICTIONARY OF OFFICIAL KGU-AFFILIATED CLUBS BY REGION ---
KENYAN_GOLF_CLUBS = {
    "Nairobi Region": [
        "Golf Park", "Karen Country Club", "Kenya Airforce Golf Club", "Kenya Railway Golf Course",
        "Kiambu Golf Club", "Limuru Country Club", "Machakos Golf Club", "Muthaiga Golf Club",
        "Ndumberi Golf Club", "Royal Nairobi Golf Club", "Ruiru Sports Club", "Sigona Golf Club",
        "Thika Barracks Golf Club", "Thika Greens Golf Resort", "Thika Sports Club", "VetLab Sports Club",
        "Windsor Golf Hotel & Country Club", "Migaa Golf Club"
    ],
    "Mt. Kenya Region": [
        "Nanyuki Sports Club", "Nyahururu Country Club", "Nyeri Golf Club"
    ],
    "Central Rift": [
        "Gilgil Country Club", "Great Rift Valley Golf Resort", "Naivasha Sports Club", 
        "Nakuru Golf Club", "Njoro Country Club", "Mt. Kipipiri Golf Resort"
    ],
    "Coast": [
        "Leisure Lodge Golf Club", "Malindi Golf Club", "Mombasa Golf Club", 
        "Nyali Golf & Country Club Ltd", "Vipingo Ridge"
    ],
    "Western": [
        "Kakamega Golf Club", "Kisii Golf Club", "Mumias Golf Club", "Nyanza Golf Club"
    ],
    "North Rift": [
        "Eldoret Golf Club", "Kericho Golf Course", "Kitale Club", "Nandi Bears Golf Club"
    ]
}

# Flatten the list for "Home Club" select boxes
ALL_KENYAN_CLUBS_FLAT = sorted([club for region in KENYAN_GOLF_CLUBS.values() for club in region])

# --- MOST COMMON KENYAN TOURNAMENTS & SERIES ---
KENYAN_COMPETITIONS = [
    # 1. Weekly & Monthly Club Fixtures
    "Club Nite (Stableford)", 
    "Club Monthly Mug", 
    # 2. Corporate Golf Days
    "NCBA Golf Series", 
    "KCB Golf Series", 
    "ABSA Golf Day", 
    "ICEA Lion Golf Tournament", 
    "Britam Golf Series", 
    "CIC Golf Day", 
    "Safaricom Golf Day",
    # 3. Golf Societies
    "Kachumbari Golf League", 
    "Kenya Ladies Golf Union societies", 
    "Corporate societies", 
    "Alumni societies", 
    "Professional associations", 
    "Rotary golf events",
    # 4. KAGC Amateur Majors & Club Opens
    "Sigona Open (KAGC)", 
    "Muthaiga Open (KAGC)", 
    "Karen Open (KAGC)", 
    "Nakuru Open (KAGC)", 
    "Limuru Open (KAGC)", 
    "Nyali Open (KAGC)", 
    "Kiambu Open (KAGC)", 
    "Machakos Open (KAGC)", 
    "Ulinzi Invitational (KAGC)", 
    "Thika Sports Open",
    # 5. Elite Majors & Development Tours
    "Magical Kenya Open (DP World Tour)", 
    "Sunshine Development Tour – East Africa Swing",
    # 6. Prestigious Annual Club Events
    "Lady Captain's Prize",
    "Ladies Invitationals",
    "Eileen Belcher Trophy",
    "Captain's Prize",
    "Chairman's Prize",
    # 7. Sponsor Invitationals
    "ABSA Invitational",
    "NCBA Invitational",
    "Kenya Airways Golf Day",
    "Coca-Cola Golf Day",
    "CFAO Golf Tournament",
    "Diageo/EABL Golf Day",
    "Casual Round"
]

def render_scorecard_input(DB_FILE, FALLBACK_PARS):
    st.title("⛳ FairwayIQ Digital Scorecard & Live Database")
    st.write("Welcome to the Scoring Portal. Please select your course and submit your round details below.")

    conn = get_db_connection()
    
    # --- DYNAMIC COURSE DIRECTORY RETRIEVAL (Venue playing at today) ---
    try:
        courses_df = pd.read_sql_query("SELECT DISTINCT course_name FROM golf_courses", conn)
        course_options = courses_df['course_name'].tolist() if not courses_df.empty else ["Limuru Country Club"]
    except Exception:
        course_options = ["Limuru Country Club"]

    # --- SESSION STATE INITIALIZATION ---
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
    if 'selected_course' not in st.session_state:
        st.session_state.selected_course = course_options[0]
    if 'selected_tee' not in st.session_state:
        st.session_state.selected_tee = "White"
    if 'competition' not in st.session_state:
        st.session_state.competition = "Casual Round"
    if 'current_hole' not in st.session_state:
        st.session_state.current_hole = 1
    if 'round_variant' not in st.session_state:
        st.session_state.round_variant = "Full 18 Holes"

    # --- RESOLVE DYNAMIC COURSE DETAILS ---
    try:
        raw_map = get_course_pars_and_si(st.session_state.selected_course, st.session_state.selected_tee)
        if raw_map:
            ACTIVE_PARS = {hole: val[0] for hole, val in raw_map.items()}
            ACTIVE_SI = {hole: val[1] for hole, val in raw_map.items()}
        else:
            ACTIVE_PARS = FALLBACK_PARS
            ACTIVE_SI = {h: h for h in range(1, 19)}
    except Exception:
        ACTIVE_PARS = FALLBACK_PARS
        ACTIVE_SI = {h: h for h in range(1, 19)}

    # Ensure dynamic hole scores dictionary holds the correct dynamic par defaults
    if 'hole_scores' not in st.session_state or len(st.session_state.hole_scores) != 18:
        st.session_state.hole_scores = {h: ACTIVE_PARS.get(h, 4) for h in range(1, 19)}

    TOTAL_COURSE_PAR = sum(ACTIVE_PARS.values())

    # --- PHASE 1: THE TOURNAMENT GATEKEEPER ---
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
            
            col_reg1, col_reg2 = st.columns(2)
            with col_reg1:
                region_choice = st.selectbox("Select Club Region:", list(KENYAN_GOLF_CLUBS.keys()))
            with col_reg2:
                reg_course = st.selectbox("Select Golf Club Playing Today:", KENYAN_GOLF_CLUBS[region_choice], key="reg_course_member")
            
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT DISTINCT h.tee_color FROM course_holes h
                    JOIN golf_courses c ON h.course_id = c.course_id
                    WHERE c.course_name = ?
                """, (reg_course,))
                available_tees = [r[0] for r in cursor.fetchall()] or ["White"]
            except Exception:
                available_tees = ["White"]

            reg_tee = st.selectbox("Select Tee Set Played:", available_tees, key="reg_tee_member")
            comp_type = st.selectbox("Select Active Competition / Event:", KENYAN_COMPETITIONS, key="reg_comp_member")
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
                    st.error("Please enter your full name to verify membership profile.")
                    
        elif player_type == "Visiting Player":
            input_name = st.text_input("Visitor Full Name:")
            visitor_home_club = st.selectbox("Select Your Official Home Club:", ALL_KENYAN_CLUBS_FLAT)
            
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                region_choice = st.selectbox("Select Playing Club Region:", list(KENYAN_GOLF_CLUBS.keys()))
            with col_v2:
                reg_course = st.selectbox("Select Venue Playing Today:", KENYAN_GOLF_CLUBS[region_choice], key="reg_course_guest")
            
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT DISTINCT h.tee_color FROM course_holes h
                    JOIN golf_courses c ON h.course_id = c.course_id
                    WHERE c.course_name = ?
                """, (reg_course,))
                available_tees = [r[0] for r in cursor.fetchall()] or ["White"]
            except Exception:
                available_tees = ["White"]

            reg_tee = st.selectbox("Select Tee Set Played:", available_tees, key="reg_tee_guest")
            visitor_hcp = st.number_input("Official Handicap Index:", min_value=0, max_value=54, step=1)
            comp_type = st.selectbox("Select Active Competition / Event:", KENYAN_COMPETITIONS, key="reg_comp_guest")
            variant = st.selectbox("Select Planned Round Format:", ["Full 18 Holes", "Front 9 Only"])
            
            if st.button("Register Guest Competitor", type="primary"):
                if input_name.strip():
                    st.session_state.authorized = True
                    st.session_state.auth_type = "Visitor"
                    st.session_state.player_id = 9000 + visitor_hcp
                    st.session_state.player_name = f"{input_name} ({visitor_home_club})"
                    st.session_state.player_hcp = visitor_hcp
                    st.session_state.selected_course = reg_course
                    st.session_state.selected_tee = reg_tee
                    st.session_state.competition = comp_type
                    st.session_state.round_variant = variant
                    st.session_state.hole_scores = {h: ACTIVE_PARS.get(h, 4) for h in range(1, 19)}
                    st.rerun()
                else:
                    st.error("Please enter your name to register as a visiting competitor.")
                    
        elif player_type == "Sponsor / Guest (Non-Playing)":
            st.info("👋 Welcome to the Tournament Event! Scorecard access is exclusively restricted to playing competitors. Please join us at the club lounge layout to view the real-time leaderboard displays!")

        elif player_type == "Club Management / Admin":
            st.subheader("🔑 Executive Portal Verification")
            admin_pin = st.text_input("Enter Management Credentials / PIN:", type="password")
            
            if st.button("Authenticate Admin Console", type="primary"):
                try:
                    target_pin = st.secrets["admin"]["pin"]
                except Exception:
                    target_pin = "1234"

                if admin_pin == target_pin:
                    st.session_state.authorized = True
                    st.session_state.auth_type = "Admin"
                    st.session_state.player_id = 0
                    st.session_state.player_name = "System Administrator"
                    st.rerun()
                else:
                    st.error("❌ Unauthorized Pin Allocation. Management access blocked.")

    # --- PHASE 2: INTERFACE ROUTING ---
    else:
        st.markdown("---")
        st.success(f"🔓 **Verified Access Granted ({st.session_state.auth_type}):** Welcome, {st.session_state.player_name} | Playing: **{st.session_state.selected_course}** ({st.session_state.selected_tee}) | Format: {st.session_state.round_variant}")
        
        if st.button("🔄 Logout / Reset Pipeline"):
            st.session_state.authorized = False
            st.session_state.auth_type = None
            st.session_state.current_hole = 1
            st.session_state.hole_scores = {h: ACTIVE_PARS.get(h, 4) for h in range(1, 19)}
            st.rerun()

        # ROUTE A: ADMIN PANEL
        if st.session_state.auth_type == "Admin":
            st.header("📊 FairwayIQ Executive Dashboard")
            
            admin_tab1, admin_tab2, admin_tab3 = st.tabs([
                "📈 PowerBI Live Analytics", 
                "✏️ Correct / Edit Scorecards", 
                "📤 Export KGU Match Records"
            ])
            
            with admin_tab1:
                power_bi_url = "https://app.powerbi.com/view?r=eyJrIjoiYzMzYjA2ODEtYWUzNy00ZTYyLWI3MjMtZTM0Y2QzOWVhZWIwIiwidCI6ImNjZWM4MmJhLTA1OTctNDRjNy1hODM4LTEzNjIwY2MxZGJlYiJ9"
                st.components.v1.iframe(power_bi_url, height=700, scrolling=True)
                
            with admin_tab2:
                st.subheader("✏️ Live Scorecard Override Grid")
                st.write("Correct competitor score entry errors or typos directly below. Click **Save Operational Overrides** to apply your corrections to the leaderboard.")
                
                if os.path.exists(DB_FILE):
                    try:
                        df_editor = pd.read_csv(DB_FILE)
                        if not df_editor.empty:
                            edited_df = st.data_editor(
                                df_editor,
                                use_container_width=True,
                                num_rows="dynamic",
                                key="admin_live_scorecard_editor"
                            )
                            
                            if st.button("Save Operational Overrides", type="primary"):
                                edited_df.to_csv(DB_FILE, index=False)
                                st.success("✅ Tournament leaderboards updated successfully with your changes!")
                                st.rerun()
                        else:
                            st.info("No competitor records found in the scorecard database.")
                    except Exception as e:
                        st.error(f"Failed to read scorecard data sheet: {e}")
                else:
                    st.info("No scorecards have been recorded yet.")
                    
            with admin_tab3:
                st.subheader("📤 Generate Handicap Union (WHS/KGU) Upload Sheet")
                st.write("Review completed results and download the round report formatted for handicap union score uploads.")
                
                if os.path.exists(DB_FILE):
                    try:
                        df_export = pd.read_csv(DB_FILE)
                        if not df_export.empty:
                            clean_export_df = df_export.sort_values(by="Score", ascending=True)
                            st.dataframe(clean_export_df, use_container_width=True)
                            
                            csv_export_bytes = clean_export_df.to_csv(index=False).encode('utf-8')
                            file_stamp = datetime.today().strftime('%Y%m%d_%H%M')
                            
                            st.download_button(
                                label="💾 Download KGU / Union Upload CSV File",
                                data=csv_export_bytes,
                                file_name=f"KGU_Tournament_Upload_{file_stamp}.csv",
                                mime="text/csv",
                                use_container_width=True,
                                type="primary"
                            )
                        else:
                            st.info("No active competitor round records to compile.")
                    except Exception as e:
                        st.error(f"Error compiling export report: {e}")
                else:
                    st.info("No active scorecard database file exists to export.")

        # ROUTE B: PLAYER ENGINE
        else:
            player_tab1, player_tab2 = st.tabs(["📝 Record Live Scorecard", "🍔 Pre-Order to the Turn"])

            with player_tab1:
                current_h = st.session_state.current_hole
                active_hole_limit = 9 if st.session_state.round_variant == "Front 9 Only" else 18
                relevant_holes = range(1, active_hole_limit + 1)
                
                running_gross = sum(st.session_state.hole_scores[h] for h in relevant_holes)
                completed_holes = [h for h in relevant_holes if h < current_h]
                par_completed = sum(ACTIVE_PARS.get(h, 4) for h in completed_holes)
                strokes_completed = sum(st.session_state.hole_scores[h] for h in completed_holes)
                relative_par = strokes_completed - par_completed

                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                col_m1.metric("Hole Timeline", f"{current_h if current_h <= active_hole_limit else active_hole_limit} / {active_hole_limit}")
                col_m2.metric("Running Gross", f"{running_gross} Strokes")
                
                if current_h == 1:
                    score_fmt = "Even"
                else:
                    score_fmt = f"+{relative_par}" if relative_par > 0 else ("Even" if relative_par == 0 else f"{relative_par}")
                col_m3.metric("To Par (Live)", score_fmt)
                
                hcp_deduction = st.session_state.player_hcp / 2 if st.session_state.round_variant == "Front 9 Only" else st.session_state.player_hcp
                col_m4.metric("Net Projected", f"{int(running_gross - hcp_deduction)}")

                st.markdown("---")

                # STATE 1: RUNNING THE HOLES
                if current_h <= active_hole_limit:
                    st.subheader(f"🏌️ Active Interface: Hole {current_h}")
                    
                    c_card1, c_card2, c_card3 = st.columns(3)
                    c_card1.info(f"⛳ **Hole Allocation:** Par **{ACTIVE_PARS.get(current_h, 4)}** | Stroke Index: **{ACTIVE_SI.get(current_h, current_h)}**")
                    c_card2.metric("Current Value Saved", f"{st.session_state.hole_scores[current_h]} Strokes")
                    c_card3.warning(f"🏆 **Event Class:** {st.session_state.competition}")
                    
                    hcp_strokes = st.number_input(
                        "Input Score for Current Hole (Gross Strokes):",
                        min_value=1, max_value=15, 
                        value=int(st.session_state.hole_scores[current_h]), 
                        step=1, key=f"input_h_{current_h}"
                    )
                    st.session_state.hole_scores[current_h] = hcp_strokes

                    st.write("")
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        if current_h > 1:
                            if st.button("⬅️ Previous Hole Position", use_container_width=True):
                                st.session_state.current_hole -= 1
                                st.rerun()
                    with b_col2:
                        if current_h < active_hole_limit:
                            if st.button("Save & Advance Hole ➡️", use_container_width=True):
                                st.session_state.current_hole += 1
                                st.rerun()
                        else:
                            btn_label = "🏁 Transition to 9-Hole Review" if active_hole_limit == 9 else "🏁 Transition to 18th Hole Review"
                            if st.button(btn_label, type="primary", use_container_width=True):
                                st.session_state.current_hole = 19
                                st.rerun()
                                
                    if current_h == 9 and st.session_state.round_variant == "Full 18 Holes":
                        st.write("")
                        if st.button("⚠️ Clock Out Early (Submit Front 9 Only)", use_container_width=True):
                            st.session_state.round_variant = "Front 9 Only"
                            st.session_state.current_hole = 19
                            st.rerun()

                # STATE 2: REVIEW MATRIX & SUBMISSION
                else:
                    st.balloons()
                    st.success(f"🎉 **{st.session_state.round_variant} Green Cleared! Score Registry Compiled.**")
                    st.markdown("### 📋 Final Championship Card Matrix Review")
                    
                    with st.form("database_submission_form"):
                        col_review1, col_review2 = st.columns(2)
                        
                        with col_review1:
                            st.text_input("Competitor Profile Name:", value=st.session_state.player_name, disabled=True)
                            st.number_input("Final Consolidated Gross Score:", value=running_gross, disabled=True)
                            marker_verification = st.selectbox(
                                "🔒 Select Attesting Flight Competitor (Official Marker Signature):",
                                ["Choose official marker...", "John Mwangi", "Alice Koech", "David Ochieng", "Martha Njeri", "Peter Kamau"]
                            )
                        
                        with col_review2:
                            st.text_input("Home Course Context:", value=st.session_state.selected_course, disabled=True)
                            st.number_input("System Verified Player Handicap Index:", value=st.session_state.player_hcp, disabled=True)
                            final_net_calc = running_gross - hcp_deduction
                            st.metric("Certified Net Finish Score", f"{int(final_net_calc)}")

                        with st.expander(f"🔍 Audit Detailed {st.session_state.round_variant} Matrix Map", expanded=True):
                            grid_cols = st.columns(6)
                            for idx, h_idx in enumerate(relevant_holes):
                                col_target = idx % 6
                                with grid_cols[col_target]:
                                    st.markdown(f"**H{h_idx}** `(Par {ACTIVE_PARS.get(h_idx, 4)})` \n### `{st.session_state.hole_scores[h_idx]}`")

                        final_commit = st.form_submit_button("🚀 Secure Transmit to Live Leaderboard Desk", type="primary", use_container_width=True)

                        if final_commit:
                            if marker_verification == "Choose official marker...":
                                st.error("⚠️ **R&A Verification Rule Violation:** Scorecard rejects entry. You must assign an attesting playing partner marker to authenticate the tournament record.")
                            else:
                                play_date_str = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
                                
                                # 1. Fallback CSV append logic
                                new_row_data = pd.DataFrame([{
                                    "MemberID": st.session_state.player_id,
                                    "PlayerName": f"{st.session_state.player_name} ({st.session_state.round_variant})",
                                    "Course": st.session_state.selected_course,
                                    "Handicap": hcp_deduction,
                                    "Score": running_gross,
                                    "Competition": st.session_state.competition,
                                    "MarkerVerification": marker_verification,
                                    "PlayDate": play_date_str
                                }])
                                
                                os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
                                if os.path.exists(DB_FILE):
                                    new_row_data.to_csv(DB_FILE, mode='a', header=False, index=False)
                                else:
                                    new_row_data.to_csv(DB_FILE, mode='w', header=True, index=False)

                                st.success(f"📦 Pipeline Synchronized! Scorecard locked and logged. Marker Token: UUID-[{marker_verification.replace(' ', '_')}]")
                                st.session_state.current_hole = 1
                                st.session_state.hole_scores = {h: ACTIVE_PARS.get(h, 4) for h in range(1, 19)}
                                st.rerun()

            # TAB 2: TURN PRE-ORDER
            with player_tab2:
                st.subheader("🍔 Fast-Track Clubhouse & Turn Pre-Ordering")
                st.write("Beat the Halfway House queue! Order food while on the course. It will be waiting for you hot at the Turn.")

                MENU_ITEMS = {
                    "🍺 Tusker / White Cap Lager": {"price": 400, "cogs": 180},
                    "🥪 Club Sandwich & French Fries": {"price": 850, "cogs": 280},
                    "🥟 Halfway House Samosas (Pair)": {"price": 300, "cogs": 90},
                    "☕ Premium House Coffee": {"price": 350, "cogs": 70},
                    "💧 Mayer's Mineral Water (500ml)": {"price": 150, "cogs": 40}
                }

                col_ord1, col_ord2 = st.columns(2)
                with col_ord1:
                    current_hole = st.selectbox(
                        "📍 Where are you on the course right now?", 
                        [f"Hole {h}" for h in range(1, 19)], 
                        index=max(0, min(17, st.session_state.current_hole - 1))
                    )
                    billing_type = st.radio("Charging Account Allocation:", ["Direct Member Folio", "Caddy Voucher", "Guest Chit"])

                with col_ord2:
                    selected_food = st.selectbox("Select Samosa/Beverage Option:", list(MENU_ITEMS.keys()))
                    qty = st.number_input("Quantity:", min_value=1, max_value=10, value=1)
                    
                    hole_num = int(current_hole.split(" ")[1])
                    if hole_num <= 9:
                        holes_remaining = 9 - hole_num
                        pickup_location = "Ready at Hole 9 Turn"
                    else:
                        holes_remaining = 18 - hole_num
                        pickup_location = "Ready at 19th Hole Lounge Table"

                    eta_minutes = max(10, holes_remaining * 15)
                    predicted_pickup = datetime.now() + timedelta(minutes=eta_minutes)
                    
                    st.info(f"🕒 **Fulfillment Target:** {pickup_location} | **Pickup ETA:** {predicted_pickup.strftime('%H:%M')} (In {eta_minutes} mins)")

                if st.button("Confirm & Post Pre-Order", type="primary"):
                    txn_id = f"TXN-QR-{int(datetime.timestamp(datetime.now()))}"
                    price = MENU_ITEMS[selected_food]["price"] * qty
                    cogs = MENU_ITEMS[selected_food]["cogs"] * qty
                    now = datetime.now()

                    new_txn = pd.DataFrame([{
                        "TransactionID": txn_id,
                        "MemberID": st.session_state.player_id,
                        "PlayerName": st.session_state.player_name,
                        "PointOfSale": "On-Course Mobile QR",
                        "AmountKES": price,
                        "COGS": cogs,
                        "PlayDate": now.strftime('%Y-%m-%d'),
                        "PlayTime": now.strftime('%H:%M:%S'),
                        "BillingType": billing_type,
                        "ServedBy": "Mobile Pre-Order",
                        "FulfilmentPoint": pickup_location,
                        "PickupETA": predicted_pickup.strftime('%H:%M')
                    }])

                    POS_FILE = "data/pos_transactions.csv"
                    os.makedirs(os.path.dirname(POS_FILE), exist_ok=True)
                    if os.path.exists(POS_FILE):
                        new_txn.to_csv(POS_FILE, mode='a', header=False, index=False)
                    else:
                        new_txn.to_csv(POS_FILE, mode='w', header=True, index=False)

                    st.balloons()
                    st.success(f"🎉 Order Posted! KES {price:,} charged via {billing_type}. Your food will be prepped hot and ready at the Turn around {predicted_pickup.strftime('%H:%M')}!")

    # --- PHASE 3: LIVE RE-RENDER VIEWPOOL ---
    if st.session_state.authorized and st.session_state.auth_type != "Admin":
        st.markdown("---")
        st.subheader("🏆 Dynamic Club Field Standings")
        if os.path.exists(DB_FILE):
            try:
                df_view = pd.read_csv(DB_FILE)
                if not df_view.empty:
                    st.dataframe(df_view.sort_values(by="Score", ascending=True), use_container_width=True)
            except Exception:
                st.info("Leaderboard feed indexing.")

    conn.close()