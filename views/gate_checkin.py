import streamlit as st

def render_gate_checkin():
    """
    Tournament Gate Check-in - Full Version with Success Summary Card
    """

    st.markdown("### 🔒 Tournament Gate Check-in")
    st.caption("Please select your registration type to unlock your portal view.")

    reg_type = st.radio(
        "Select Registration Type:",
        [
            "Club Member",
            "Visiting Player",
            "Sponsor / Guest (Non-Playing)",
            "Club Management / Admin"
        ],
        horizontal=True,
        index=0
    )

    st.markdown("---")

    # Common lists
    kenyan_clubs = [
        "Limuru Country Club", "Karen Country Club", "Muthaiga Golf Club",
        "Sigona Golf Club", "Windsor Golf Hotel & Country Club",
        "Vet Lab Sports Club", "Thika Sports Club", "Nyali Golf & Country Club",
        "Nyanza Golf Club", "Eldoret Golf Club", "Golf Park", "Other"
    ]
    regions = ["Nairobi Region", "Rift Valley Region", "Coast Region", "Western Region", "Other"]
    tee_sets = ["White", "Yellow", "Red", "Blue", "Championship"]
    competitions = [
        "Club Nite (Stableford)", "Monthly Mug", "Medal Round",
        "KAGC Event", "Corporate Day", "Casual Round", "Other"
    ]
    round_formats = ["Full 18 Holes", "Front 9", "Back 9", "Custom"]

    # ============================================
    # 1. CLUB MEMBER
    # ============================================
    if reg_type == "Club Member":
        col1, col2 = st.columns(2)

        with col1:
            member_id = st.text_input("Enter your Club Member ID:")
            full_name = st.text_input("Enter Registered Full Name:")
            handicap = st.number_input("Verified Club Handicap:", min_value=0.0, max_value=54.0, value=18.0, step=0.1)

        with col2:
            home_club = st.selectbox("Select Club Home:", kenyan_clubs)
            playing_club = st.selectbox("Select Golf Club Playing Today:", kenyan_clubs)
            tee_set = st.selectbox("Select Tee Set Played:", tee_sets)

        competition = st.selectbox("Select Active Competition / Event:", competitions)
        round_format = st.selectbox("Select Planned Round Format:", round_formats)

        if st.button("Unlock Scorecard Portal", type="primary", use_container_width=True):
            if member_id.strip() and full_name.strip():
                st.session_state.authorized = True
                st.session_state.auth_type = "player"
                st.session_state.player_id = member_id.strip()
                st.session_state.player_name = full_name.strip()
                st.session_state.player_hcp = handicap
                st.session_state.home_club = home_club
                st.session_state.playing_club = playing_club
                st.session_state.tee_set = tee_set
                st.session_state.competition = competition
                st.session_state.round_format = round_format
                st.session_state.registration_type = "Club Member"
                st.rerun()
            else:
                st.warning("Please fill in Member ID and Full Name.")

    # ============================================
    # 2. VISITING PLAYER
    # ============================================
    elif reg_type == "Visiting Player":
        visitor_name = st.text_input("Visitor Full Name:")

        col1, col2 = st.columns(2)
        with col1:
            home_club = st.selectbox("Select Your Official Home Club:", kenyan_clubs)
            region = st.selectbox("Select Playing Club Region:", regions)
        with col2:
            playing_club = st.selectbox("Select Venue Playing Today:", kenyan_clubs)
            tee_set = st.selectbox("Select Tee Set Played:", tee_sets)

        handicap = st.number_input("Official Handicap Index:", min_value=0.0, max_value=54.0, value=0.0, step=0.1)
        competition = st.selectbox("Select Active Competition / Event:", competitions)
        round_format = st.selectbox("Select Planned Round Format:", round_formats)

        if st.button("Register Guest Competitor", type="primary", use_container_width=True):
            if visitor_name.strip():
                st.session_state.authorized = True
                st.session_state.auth_type = "player"
                st.session_state.player_name = visitor_name.strip()
                st.session_state.player_id = "VISITOR"
                st.session_state.player_hcp = handicap
                st.session_state.home_club = home_club
                st.session_state.playing_club = playing_club
                st.session_state.tee_set = tee_set
                st.session_state.competition = competition
                st.session_state.round_format = round_format
                st.session_state.registration_type = "Visiting Player"
                st.rerun()
            else:
                st.warning("Please enter the Visitor Full Name.")

    # ============================================
    # 3. SPONSOR / GUEST (Non-Playing)
    # ============================================
    elif reg_type == "Sponsor / Guest (Non-Playing)":
        st.info("👋 Welcome to the Tournament Event! Scorecard access is exclusively restricted to playing competitors. Please join us at the club lounge to view the real-time leaderboard displays!")

    # ============================================
    # 4. CLUB MANAGEMENT / ADMIN
    # ============================================
    else:
        st.markdown("### 🔑 Executive Portal Verification")
        admin_pin = st.text_input("Enter Management Credentials / PIN:", type="password")

        if st.button("Authenticate Admin Console", type="primary"):
            try:
                target_pin = st.secrets["admin"]["pin"]
            except Exception:
                target_pin = "1800"

            if admin_pin == target_pin:
                st.session_state.admin_authenticated = True
                st.session_state.auth_type = "admin"
                st.success("Admin access granted.")
                st.rerun()
            else:
                st.error("Invalid Management Credentials.")

    # ============================================
        # ============================================
    # SUCCESS SUMMARY CARD + CONTINUE BUTTON
    # ============================================
    if st.session_state.get("authorized") and st.session_state.get("auth_type") == "player":
        st.markdown("---")
        st.success("✅ Registration Successful!")

        st.markdown(f"""
        <div style="
            background-color: #f0fdf4;
            border: 1px solid #86efac;
            border-radius: 12px;
            padding: 22px 24px;
            margin-top: 12px;
            margin-bottom: 20px;
        ">
            <h4 style="margin-top: 0; color: #166534; font-size: 1.15rem;">Player Summary</h4>
            <p style="margin: 7px 0;"><strong>Name:</strong> {st.session_state.player_name}</p>
            <p style="margin: 7px 0;"><strong>Member / ID:</strong> {st.session_state.player_id}</p>
            <p style="margin: 7px 0;"><strong>Handicap:</strong> {st.session_state.get('player_hcp', 'N/A')}</p>
            <p style="margin: 7px 0;"><strong>Home Club:</strong> {st.session_state.get('home_club', 'N/A')}</p>
            <p style="margin: 7px 0;"><strong>Playing Today:</strong> {st.session_state.get('playing_club', 'N/A')}</p>
            <p style="margin: 7px 0;"><strong>Competition:</strong> {st.session_state.get('competition', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("➡️ Continue to Digital Scorecard", type="primary", use_container_width=True):
            st.rerun()