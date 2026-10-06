"""Demo seed data for Nepal Parliamentary Party (संसदीय दलको कार्यालय) Management System.
All persons, details and sample motions are prepared for official demo purposes.
"""
import os
import glob
import sqlite3
import datetime as dt
from werkzeug.security import generate_password_hash


def reset_database(DATA, DB_PATH, UPLOADS, SCHEMA):
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(UPLOADS, exist_ok=True)
    for f in glob.glob(os.path.join(UPLOADS, "*")):
        try:
            os.remove(f)
        except Exception:
            pass

    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except PermissionError:
            try:
                con_clean = sqlite3.connect(DB_PATH)
                con_clean.execute("PRAGMA foreign_keys=OFF")
                tables = [r[0] for r in con_clean.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                for t in tables:
                    con_clean.execute(f"DROP TABLE IF EXISTS {t}")
                con_clean.commit()
                con_clean.close()
            except Exception:
                pass

    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    con.execute("PRAGMA foreign_keys=ON")
    D = dt.date.today()
    day = lambda n: (D + dt.timedelta(days=n)).isoformat()
    ts = dt.datetime.now().isoformat(timespec="seconds")
    pw = generate_password_hash(os.environ.get("PMS_DEMO_PASSWORD", "demo1234"))

    def ins(sql, args):
        return con.execute(sql, args).lastrowid

    # ------------------------------------------------------------- 1. Users
    # Note: Keep original 7 users at indices 1..7 for backward test compatibility
    users = [
        ("Sita Admin", "admin@pms.test", "super_admin"),           # ID 1
        ("Ram Party-Admin", "partyadmin@pms.test", "party_admin"),    # ID 2
        ("Gita Coordinator", "coordinator@pms.test", "coordinator"), # ID 3
        ("Hari Researcher", "researcher@pms.test", "researcher"),   # ID 4
        ("Maya Researcher", "researcher2@pms.test", "researcher"),  # ID 5
        ("Hon. Bimal Sharma", "mp1@pms.test", "mp"),                # ID 6
        ("Hon. Anita Rai", "mp2@pms.test", "mp"),                   # ID 7
        ("Hon. Dr. Shekhar Sharma", "leader@pms.test", "pp_leader"),# ID 8
        ("Hon. Ramesh Adhikari", "chiefwhip@pms.test", "chief_whip"), # ID 9
        ("Hon. Sunita Baral", "whip@pms.test", "whip"),             # ID 10
        ("Hon. Kiran Thapa", "mp3@pms.test", "mp"),                 # ID 11
        ("Hon. Pasang Sherpa", "mp4@pms.test", "mp"),               # ID 12
    ]
    uid = {}
    for name, email, role in users:
        uid[email] = ins(
            "INSERT INTO users(name,email,password_hash,role,status,created_at) VALUES(?,?,?,?,?,?)",
            (name, email, pw, role, "active", ts)
        )

    # ------------------------------------------------------------- 2. Parliamentarians
    # Note: Keep original 4 parliamentarians at IDs 1..4 for test compatibility
    mps_data = [
        # ID 1: Hon. Bimal Sharma (linked to mp1@pms.test)
        ("Hon. Bimal Sharma", "बिमल शर्मा", "House of Representatives", "Federal", "FPTP", "Khas Arya",
         "Member of Parliament", "Kathmandu", "Kathmandu-4", "Information Technology Committee", "+977-9851000004",
         "Nabin Giri", "+977-9841000004", "Bansbari, Kathmandu", "A+ve",
         "Chair of IT Committee. Expert on telecommunications and cyber governance.", "mp1@pms.test"),

        # ID 2: Hon. Anita Rai (linked to mp2@pms.test)
        ("Hon. Anita Rai", "अनिता राई", "House of Representatives", "Federal", "FPTP", "Aadibasi Janajati",
         "Member of Parliament", "Morang", "Morang-2", "Finance Committee", "+977-9851000005",
         "Ramesh Rai", "+977-9841000005", "Shantinagar, Kathmandu", "AB+ve",
         "Chair of Finance Committee. Focus on fiscal decentralization and economic legislation.", "mp2@pms.test"),

        # ID 3: Hon. Kiran Thapa (National Assembly)
        ("Hon. Kiran Thapa", "किरण थापा", "National Assembly", "Federal", "Nominated", "Khas Arya",
         "Member of Parliament", "Gandaki", "Gandaki Province Cluster", "Legislation Management Committee", "+977-9851000010",
         "Sunil Shrestha", "+977-9841000010", "Sanepa, Lalitpur", "B+ve",
         "Member of Legislation Management Committee. Reviews bills referred to the Upper House.", "mp3@pms.test"),

        # ID 4: Hon. Sunita Gurung (HoR)
        ("Hon. Sunita Gurung", "सुनिता गुरुङ", "House of Representatives", "Federal", "PR", "Aadibasi Janajati",
         "Member of Parliament", "Kaski", "Kaski PR", "Information Technology Committee", "+977-9851000009",
         "Pooja Gurung", "+977-9841000009", "Chabahil, Kathmandu", "A+ve",
         "Member of IT Committee. Active in education and digital literacy.", None),

        # ID 5+: Additional authentic Samsadiya Dal leadership and Province Assembly MPs
        ("Hon. Dr. Shekhar Sharma", "डा. शेखर शर्मा", "House of Representatives", "Federal", "FPTP", "Khas Arya",
         "Parliamentary Party Leader", "Morang", "Morang-6", "State Affairs Committee", "+977-9851000001",
         "Mukesh Thapa", "+977-9841000001", "Baluwatar, Kathmandu", "O+ve",
         "Parliamentary Party Leader. Oversees coalition affairs and major political decisions.", "leader@pms.test"),

        ("Hon. Ramesh Adhikari", "रमेश अधिकारी", "House of Representatives", "Federal", "FPTP", "Khas Arya",
         "Chief Whip", "Kanchanpur", "Kanchanpur-2", "Law and Human Rights Committee", "+977-9851000002",
         "Dipak Joshi", "+977-9841000002", "New Baneshwor, Kathmandu", "A+ve",
         "Chief Whip of Parliamentary Party. Directs parliamentary business, issues whips, allocates floor time.", "chiefwhip@pms.test"),

        ("Hon. Sunita Baral", "सुनिता बराल", "House of Representatives", "Federal", "PR", "Khas Arya",
         "Whip", "Jhapa", "Jhapa PR", "Information Technology Committee", "+977-9851000003",
         "Sarita Neupane", "+977-9841000003", "Koteshwor, Kathmandu", "B+ve",
         "Party Whip. Coordinates floor presence, member attendance, and voting compliance.", "whip@pms.test"),

        ("Hon. Manju Chaudhary", "मन्जु चौधरी", "House of Representatives", "Federal", "PR", "Tharu",
         "Member of Parliament", "Dang", "Dang PR", "Agriculture & Natural Resources", "+977-9851000006",
         "Santosh Dahit", "+977-9841000006", "Anamnagar, Kathmandu", "B+ve",
         "Active in agriculture policy, irrigation, and indigenous welfare.", None),

        ("Hon. Rajendra Paswan", "राजेन्द्र पासवान", "House of Representatives", "Federal", "PR", "Dalit",
         "Member of Parliament", "Saptari", "Saptari PR", "Public Accounts Committee", "+977-9851000007",
         "Kishor Ram", "+977-9841000007", "Ghattekulo, Kathmandu", "O+ve",
         "Member of Public Accounts Committee. Advocate for social justice and fiscal accountability.", None),

        ("Hon. Mohammad Alam", "मोहम्मद आलम", "House of Representatives", "Federal", "FPTP", "Muslim",
         "Member of Parliament", "Rautahat", "Rautahat-1", "Infrastructure Development Committee", "+977-9851000008",
         "Imran Khan", "+977-9841000008", "Babarmahal, Kathmandu", "O-ve",
         "Focus on infrastructure, highway connectivity, and Terai-Madhesh flood control.", None),

        # 7 Province Assemblies
        ("Hon. Pasang Sherpa", "पासाङ शेर्पा", "Koshi Province Assembly", "Koshi", "FPTP", "Aadibasi Janajati",
         "Member of Parliament", "Solukhumbu", "Solukhumbu-1(A)", "Finance & Planning Committee", "+977-9852000001",
         "Tenzing Sherpa", "+977-9842000001", "Biratnagar / Salleri", "O+ve",
         "Koshi Province Assembly Member. Active in mountain tourism and infrastructure.", "mp4@pms.test"),

        ("Hon. Binod Yadav", "विनोद यादव", "Madhesh Province Assembly", "Madhesh", "FPTP", "Madhesi",
         "Member of Parliament", "Dhanusha", "Dhanusha-3(B)", "Development Committee", "+977-9854000001",
         "Suraj Yadav", "+977-9844000001", "Janakpurdham, Madhesh", "A+ve",
         "Madhesh Province Assembly Member. Focus on rural roads and border trade.", None),

        ("Hon. Shrijana Shrestha", "सृजना श्रेष्ठ", "Bagmati Province Assembly", "Bagmati", "PR", "Aadibasi Janajati",
         "Member of Parliament", "Lalitpur", "Lalitpur PR", "Provincial Affairs Committee", "+977-9851000012",
         "Usha Maharjan", "+977-9841000012", "Hetauda / Lalitpur", "B+ve",
         "Bagmati Province Assembly Member. Promotes cooperative reform and vocational training.", None),

        ("Hon. Tek Bahadur Gurung", "टेक बहादुर गुरुङ", "Gandaki Province Assembly", "Gandaki", "FPTP", "Aadibasi Janajati",
         "Member of Parliament", "Kaski", "Kaski-1(A)", "Public Accounts Committee", "+977-9856000001",
         "Prabin Gurung", "+977-9846000001", "Pokhara, Gandaki", "O+ve",
         "Gandaki Province Assembly Member. Oversight on provincial budget execution.", None),

        ("Hon. Saraswati BK", "सरस्वती विक", "Lumbini Province Assembly", "Lumbini", "PR", "Dalit",
         "Member of Parliament", "Rupandehi", "Rupandehi PR", "Social Development Committee", "+977-9857000001",
         "Gita BK", "+977-9847000001", "Deukhuri / Butwal", "A+ve",
         "Lumbini Province Assembly Member. Advocate for women empowerment and education equity.", None),

        ("Hon. Chandra Prakash Budha", "चन्द्र प्रकाश बुढा", "Karnali Province Assembly", "Karnali", "FPTP", "Khas Arya",
         "Member of Parliament", "Surkhet", "Surkhet-2(B)", "Legislation Committee", "+977-9858000001",
         "Karna Budha", "+977-9848000001", "Birendranagar, Karnali", "AB+ve",
         "Karnali Province Assembly Member. Champion for remote area development.", None),

        ("Hon. Dipendra Saud", "दिपेन्द्र साउद", "Sudurpashchim Province Assembly", "Sudurpashchim", "FPTP", "Khas Arya",
         "Member of Parliament", "Kailali", "Kailali-5(A)", "Finance & Natural Resources", "+977-9859000001",
         "Harka Saud", "+977-9849000001", "Dhangadhi, Sudurpashchim", "O+ve",
         "Sudurpashchim Assembly Member. Water resources and cross-border connectivity specialist.", None),
    ]

    pm = {}
    for name, n_ne, house, prov, el_t, clus, dal_r, dist, cons, comm, cont, pa_n, pa_c, res, bg, bio, u_email in mps_data:
        pm[name] = ins(
            "INSERT INTO parliamentarians(name,name_ne,house,province,election_type,pr_cluster,dal_role,district,"
            "constituency,committee,contact,pa_name,pa_contact,capital_address,blood_group,bio,status,user_id)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (name, n_ne, house, prov, el_t, clus, dal_r, dist, cons, comm, cont, pa_n, pa_c, res, bg, bio, "active",
             uid.get(u_email) if u_email else None)
        )

    # ------------------------------------------------------------- 3. Committees
    com = {}
    committees_data = [
        ("Information Technology Committee", "House of Representatives", "Digital policy, cyber law, and e-governance bills."),
        ("Finance Committee", "House of Representatives", "Budget, taxation, monetary policy and economic legislation."),
        ("Legislation Management Committee", "National Assembly", "Reviews bills referred to the upper house."),
        ("State Affairs and Good Governance Committee", "House of Representatives", "Civil service, security, election laws and governance."),
        ("Provincial Affairs Committee", "Bagmati Province Assembly", "Oversight on provincial governance and local coordination."),
    ]
    for name, house, desc in committees_data:
        com[name] = ins(
            "INSERT INTO committees(name,house,description,status) VALUES(?,?,?,?)",
            (name, house, desc, "active")
        )

    for c, p, r in [
        ("Information Technology Committee", "Hon. Bimal Sharma", "Chair"),
        ("Information Technology Committee", "Hon. Sunita Gurung", "Member"),
        ("Information Technology Committee", "Hon. Sunita Baral", "Member"),
        ("Finance Committee", "Hon. Anita Rai", "Chair"),
        ("Legislation Management Committee", "Hon. Kiran Thapa", "Member"),
        ("State Affairs and Good Governance Committee", "Hon. Dr. Shekhar Sharma", "Member"),
        ("Provincial Affairs Committee", "Hon. Shrijana Shrestha", "Member"),
    ]:
        con.execute("INSERT INTO committee_members VALUES(?,?,?)", (com[c], pm[p], r))

    IT, FIN, LEG = ("Information Technology Committee", "Finance Committee", "Legislation Management Committee")

    # ------------------------------------------------------------- 4. Bills (Exactly 6 for test count compatibility)
    bills_data = [
        ("Cybersecurity and Digital Safety Bill, 2083", "सूचना प्रविधि तथा साइबर सुरक्षा विधेयक, २०८३",
         "Framework for national cyber incident response, critical infrastructure protection, and online safety duties.",
         "Information Technology", "House of Representatives", "Government", "Under Review", "High", -20, IT, 10,
         "Policy discussion & committee amendments", "Pending"),

        ("Digital Payments and Fintech Regulation Bill", "डिजिटल भुक्तानी तथा वित्तीय प्रविधि नियमन विधेयक",
         "Licensing, interoperability and consumer-protection rules for digital payment operators.",
         "Finance & Economy", "House of Representatives", "Government", "Researching", "High", -35, FIN, 21,
         "Complete economic impact brief & cross-party consultations", "Pending"),

        ("Public Health Service (Amendment) Bill", "जनस्वास्थ्य सेवा (पहिलो संशोधन) विधेयक",
         "Amends rural health post staffing, medicine supply chains, and emergency referral subsidies.",
         "Health", "National Assembly", "Government", "Party Discussion", "Medium", -50, LEG, 14,
         "Prepare discussion note for Samsadiya Dal meeting", "Pending"),

        ("Renewable Energy Promotion Bill", "नवीकरणीय ऊर्जा प्रवर्द्धन तथा विकास विधेयक",
         "Incentives, net-metering, and grid-access guarantees for small-scale community renewables.",
         "Energy & Environment", "National Assembly", "Private Member", "Position Decided", "Medium", -70, LEG, 30,
         "Brief MP for floor debate & table party amendments", "Support with amendments"),

        ("School Education Governance Bill", "विद्यालय शिक्षा व्यवस्थापन विधेयक, २०८०",
         "Clarifies roles of local, provincial and federal authorities in teacher tenure, licensing, and standards.",
         "Education", "House of Representatives", "Government", "New", "Low", -3, None, None,
         "Initial review by policy research desk", "Pending"),

        ("Land Records Digitisation Bill", "भू-अभिलेख डिजिटलीकरण तथा जग्गा प्रशासन विधेयक",
         "Digitises cadastral land records with citizen digital lockers and data safeguards.",
         "Governance", "House of Representatives", "Government", "Closed", "Low", -120, FIN, None,
         "Enacted by parliament", "Support"),
    ]

    bid = {}
    for t, n_ne, d, cat, h, bt, st, pr, intro, c, dl, nxt, pos in bills_data:
        bid[t] = ins(
            "INSERT INTO bills(title,nepali_title,description,category,house,bill_type,status,priority,"
            "introduced_date,committee_id,deadline,next_action,party_position,decision_date,created_by,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (t, n_ne, d, cat, h, bt, st, pr, day(intro), com[c] if c else None, day(dl) if dl is not None else None,
             nxt, pos, day(-10) if pos != "Pending" else None, uid["coordinator@pms.test"], ts, ts)
        )

    cyber, fin, health, energy, school, land = [bid[b[0]] for b in bills_data]

    # Bill Assignments
    def assign(b, email, kind):
        con.execute(
            "INSERT INTO bill_assignments(bill_id,user_id,assignment_type,status,assigned_at) VALUES(?,?,?,?,?)",
            (b, uid[email], kind, "active", ts)
        )

    assign(fin, "researcher@pms.test", "researcher")
    assign(fin, "mp2@pms.test", "parliamentarian")
    assign(health, "researcher2@pms.test", "researcher")
    assign(energy, "researcher@pms.test", "researcher")
    assign(energy, "mp1@pms.test", "parliamentarian")
    assign(land, "mp2@pms.test", "parliamentarian")

    # Research notes
    con.execute(
        "INSERT INTO bill_research(bill_id,researcher_id,summary,notes,created_at) VALUES(?,?,?,?,?)",
        (fin, uid["researcher@pms.test"], "Comparative review of three regional fintech licensing regimes",
         "Draft brief covers licensing tiers, consumer redress and capital requirements. Section on rural financial inclusion pending.", ts)
    )
    con.execute(
        "INSERT INTO bill_research(bill_id,researcher_id,summary,notes,created_at) VALUES(?,?,?,?,?)",
        (energy, uid["researcher@pms.test"], "Grid-access provisions and net-metering safeguards",
         "Net-metering clause needs to guarantee minimum 15-year purchase power parity for local cooperatives.", ts)
    )

    # Party positions
    con.execute(
        "INSERT INTO party_positions(bill_id,position,decision_date,decided_by,notes,recorded_by,created_at) VALUES(?,?,?,?,?,?,?)",
        (energy, "Support with amendments", day(-10), "Parliamentary Party Working Committee (संसदीय दल कार्यसमिति)",
         "Support in principle; mandate amendment to Clause 9 protecting micro-hydropower cooperatives.", uid["coordinator@pms.test"], ts)
    )

    # ------------------------------------------------------------- 5. Registered Party Amendments
    con.execute(
        "INSERT INTO bill_amendments(bill_id,parliamentarian_id,section_clause,proposed_text,rationale,party_stance,status,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (energy, pm["Hon. Bimal Sharma"], "दफा ९ को उपदफा (२)",
         "स्थानीय स्तरमा ५०० किलोवाट सम्म उत्पादन हुने सामुदायिक नवीकरणीय ऊर्जाको राष्ट्रिय प्रसारण लाइनमा निःशुल्क जडान सुनिश्चित गरिनेछ।",
         "स्थानीय समुदाय तथा सहकारीलाई हरित ऊर्जा उत्पादनमा प्रोत्साहन गर्न र प्रक्रियागत झन्झट हटाउन।",
         "Endorsed", "Registered", uid["coordinator@pms.test"], ts)
    )
    con.execute(
        "INSERT INTO bill_amendments(bill_id,parliamentarian_id,section_clause,proposed_text,rationale,party_stance,status,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (cyber, pm["Hon. Sunita Baral"], "दफा २४ को उपदफा (४)",
         "साइबर सुरक्षा अनुगमनका क्रममा नागरिकको गोपनीयता सम्बन्धी मौलिक हकको उल्लंघन नहुने गरी न्यायिक अनुमति अनिवार्य गरिनुपर्नेछ।",
         "संविधानको धारा २८ ले प्रत्याभूत गरेको गोपनीयताको हकको संरक्षण सुनिश्चित गर्न।",
         "Endorsed", "Registered", uid["coordinator@pms.test"], ts)
    )

    # ------------------------------------------------------------- 6. Tasks
    tasks = [
        ("Draft economic impact brief on Fintech bill", "researcher@pms.test", "bill", fin, 4, "High", "In Progress"),
        ("Collect committee member feedback on Cybersecurity Bill", "coordinator@pms.test", "bill", cyber, 3, "High", "Open"),
        ("Brief MP before floor debate on Renewable Energy", "coordinator@pms.test", "bill", energy, -2, "Medium", "Open"),
        ("Prepare party discussion note for Public Health Bill", "researcher2@pms.test", "bill", health, 6, "Medium", "Open"),
        ("Update MP district and PA contact directory", "partyadmin@pms.test", None, None, 12, "Low", "Open"),
        ("File research on land records safeguards", "researcher@pms.test", "bill", land, -30, "Low", "Done"),
    ]
    for t, o, rt, rid, dl, pr, st in tasks:
        con.execute(
            "INSERT INTO tasks(title,owner_id,related_type,related_id,deadline,priority,status,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (t, uid[o], rt, rid, day(dl), pr, st, uid["coordinator@pms.test"], ts)
        )

    # ------------------------------------------------------------- 7. Meetings & Attendance
    def at(n, hh):
        return f"{day(n)}T{hh}"

    meetings = [
        ("IT Committee — Cybersecurity Bill briefing", at(3, "11:00"), "Committee Room 4, Singha Durbar", IT, cyber,
         "Hon. Bimal Sharma, Hon. Sunita Gurung, Hon. Sunita Baral", "1. Bill overview\n2. Data security framework\n3. Committee timeline",
         None, None, "Scheduled", "Committee Thematic Group", "House of Representatives"),

        ("Samsadiya Dal Full Meeting — Session Strategy & Directives", at(1, "15:00"), "Parliamentary Party Office, Singha Durbar", None, None,
         "All Parliamentary Party Members (HoR & National Assembly)", "1. Discussion on Vote of Confidence\n2. Chief Whip directives\n3. Zero Hour speaker allocation",
         None, None, "Scheduled", "Samsadiya Dal Full Caucus (संसदीय दलको पूर्ण बैठक)", "House of Representatives"),

        ("Finance Committee — Fintech Hearing with Regulators", at(-8, "10:00"), "Committee Room 2, Singha Durbar", FIN, fin,
         "Hon. Anita Rai, researchers, NRB representatives", "Hear from fintech payment operators and financial supervisors.",
         "Payment providers requested a 24-month transition period for ISO compliance.",
         "Party position will support licensing with consumer protection safeguards.", "Completed", "Committee Thematic Group", "House of Representatives"),
    ]

    for t, d, loc, c, b, ppl, ag, mins, dec, st, mc, h in meetings:
        mid = ins(
            "INSERT INTO meetings(title,date,location,committee_id,bill_id,participants,agenda,minutes,decisions,status,meeting_category,house,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (t, d, loc, com[c] if c else None, b, ppl, ag, mins, dec, st, mc, h, uid["coordinator@pms.test"], ts)
        )
        if st == "Completed":
            con.execute("INSERT INTO meeting_attendance VALUES(?,?,?,?)", (mid, pm["Hon. Anita Rai"], "Present", "Chaired session"))
            con.execute("INSERT INTO meeting_attendance VALUES(?,?,?,?)", (mid, pm["Hon. Dr. Shekhar Sharma"], "Present", "Active participant"))

    # ------------------------------------------------------------- 8. Parliamentary Questions
    for qt, p, ms, subj, st, resp in [
        ("What measures is the Ministry taking to protect citizen data held by public agencies and prevent digital identity leaks?",
         "Hon. Bimal Sharma", "Ministry of Communication and IT", "Public-sector data security and privacy", "Submitted", None),
        ("When will rural health post staffing vacancies be filled across mountain and Terai districts?",
         "Hon. Anita Rai", "Ministry of Health and Population", "Rural health workforce and hospital posts", "Answered",
         "The Ministry reported that the Public Service Commission vacancy intake is scheduled within two quarters."),
    ]:
        con.execute(
            "INSERT INTO parliamentary_questions(question,parliamentarian_id,ministry,subject,submitted_date,status,response,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (qt, pm[p], ms, subj, day(-9), st, resp, uid["coordinator@pms.test"], ts)
        )

    # ------------------------------------------------------------- 9. Documents
    for name, b, cat, level, text in [
        ("Cybersecurity Bill — draft text (demo)", cyber, "Bill Text", "internal",
         "OFFICIAL DEMO DRAFT\nCybersecurity and Digital Safety Bill, 2083 text copy."),
        ("Fintech licensing comparison (demo)", fin, "Research Brief", "internal",
         "OFFICIAL DEMO BRIEF\nComparative licensing frameworks across South Asia."),
        ("Internal strategy note (restricted demo)", cyber, "Position Paper", "restricted",
         "CONFIDENTIAL: Parliamentary Party Strategy Memo on Floor Voting and Committee Amendments."),
    ]:
        stored = "seed-%d.txt" % (abs(sum(map(ord, name))) * 7919)
        with open(os.path.join(UPLOADS, stored), "w") as fh:
            fh.write(text + "\n")
        con.execute(
            "INSERT INTO documents(name,file_path,original_name,category,related_type,related_id,access_level,uploaded_by,uploaded_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (name, stored, name.split(" (")[0].replace(" ", "_") + ".txt", cat, "bill", b, level, uid["coordinator@pms.test"], ts)
        )

    # ------------------------------------------------------------- 10. Whips (ह्वीप तथा दलको निर्देशन)
    whips_data = [
        # Whip 1: 3-Line Whip on Vote of Confidence
        ("स.द.२०८१/०२-००८", "प्रधानमन्त्रीको विश्वासको मत सम्बन्धी प्रस्तावमा अनिवार्य पक्षमा मतदान",
         "Three-line", "House of Representatives", "In Favor", day(2), "13:00", None,
         "सम्माननीय प्रधानमन्त्रीज्यूले प्रतिनिधि सभा समक्ष पेश गर्नुहुने विश्वासको मत सम्बन्धी प्रस्ताव निर्णयार्थ पेश हुँदा दलका सम्पूर्ण माननीय सदस्यहरू अनिवार्य उपस्थित भई प्रस्तावको पक्षमा मतदान गर्न यो ३-लाइन ह्वीप जारी गरिएको छ।",
         "राजनीतिक दल सम्बन्धी ऐन, २०७३ को दफा २८ बमोजिम", "Issued", uid["chiefwhip@pms.test"],
         "ह्वीप उल्लंघन गरेमा राजनीतिक दल सम्बन्धी ऐन, २०७३ को दफा ३१ र ३२ बमोजिम दल त्याग गरेको मानी सांसद पद खारेजी सम्मको कारबाही हुनेछ।"),

        # Whip 2: 3-Line Whip on School Education Bill
        ("स.द.२०८१/०२-०१५", "विद्यालय शिक्षा व्यवस्थापन विधेयक - दलको संशोधनसहित पारित गर्ने सम्बन्धी",
         "Three-line", "House of Representatives", "In Favor", day(12), "14:00", school,
         "विद्यालय शिक्षा व्यवस्थापन विधेयकमा दलको तर्फबाट दर्ता भएका संशोधन प्रस्तावहरूको पक्षमा र समग्र विधेयकको निर्णयार्थ पक्षमा मतदान गर्न निर्देशन गरिन्छ।",
         "राजनीतिक दल सम्बन्धी ऐन, २०७३ को दफा २८ बमोजिम", "Issued", uid["chiefwhip@pms.test"],
         "दलको आधिकारिक धारणा अनुसार शिक्षक हित र स्थानीय तह समन्वय सम्बन्धी दफावार संशोधनलाई दृढ समर्थन गर्ने।"),

        # Whip 3: 2-Line Whip on Budget Deliberations
        ("स.द.२०८१/०२-०२१", "विनियोजन विधेयकमाथिको सैद्धान्तिक छलफल - अनिवार्य उपस्थिति",
         "Two-line", "House of Representatives", "Mandatory Attendance", day(5), "11:00", None,
         "आगामी आर्थिक वर्षको विनियोजन विधेयकमाथिको महत्वपूर्ण सैद्धान्तिक छलफल प्रारम्भ हुने भएकाले सम्पूर्ण माननीय सदस्यहरू बैठक कक्षमा अनिवार्य उपस्थित रहन यो २-लाइन ह्वीप जारी गरिएको छ।",
         "राजनीतिक दल सम्बन्धी ऐन, २०७३ को दफा २८ बमोजिम", "Issued", uid["whip@pms.test"],
         "बिना पूर्वस्वीकृति अनुपस्थित रहने सांसदलाई दलको सचेतक कार्यालयले हाजिरी विवरण माग गर्नेछ।"),
    ]

    wid = {}
    for ref, title, wtype, house, direc, vdate, vtime, rbill, agenda, legal, wst, iss_by, notes in whips_data:
        wid[ref] = ins(
            "INSERT INTO whips(ref_no,title,whip_type,house,directive,voting_date,voting_time,bill_id,agenda,legal_basis,status,issued_by,issued_at,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ref, title, wtype, house, direc, vdate, vtime, rbill, agenda, legal, wst, iss_by, ts, notes)
        )

    # Roll call for Whip 1 (Vote of Confidence) across HoR MPs
    whip1_id = wid["स.द.२०८१/०२-००८"]
    roll_call_data = [
        ("Hon. Dr. Shekhar Sharma", "Served", "Present", "In Line", "Complied", "None", "दलको नेताको रुपमा पक्षमा मतदान"),
        ("Hon. Ramesh Adhikari", "Served", "Present", "In Line", "Complied", "None", "प्रमुख सचेतकको रुपमा फ्लोर अनुगमन र मतदान"),
        ("Hon. Sunita Baral", "Served", "Present", "In Line", "Complied", "None", "सचेतकको रुपमा उपस्थित र पक्षमा मतदान"),
        ("Hon. Bimal Sharma", "Served", "Present", "In Line", "Complied", "None", "ह्वीप अनुसार पक्षमा मतदान सम्पन्न"),
        ("Hon. Anita Rai", "Served", "Present", "In Line", "Complied", "None", "ह्वीप अनुसार पक्षमा मतदान सम्पन्न"),
        ("Hon. Rajendra Paswan", "Served", "Present", "In Line", "Complied", "None", "ह्वीप अनुसार पक्षमा मतदान सम्पन्न"),
        ("Hon. Sunita Gurung", "Served", "Present", "In Line", "Complied", "None", "ह्वीप अनुसार पक्षमा मतदान सम्पन्न"),
        ("Hon. Manju Chaudhary", "Served", "Absent with Leave", "Did Not Vote", "Exempted", "None", "स्वीकृत बिरामी बिदाका कारण अनुपस्थित"),
        ("Hon. Mohammad Alam", "Served", "Present", "Cross-voted", "Violated", "Show-cause Issued", "ह्वीपको विपरित विपक्षमा मतदान - ऐनको दफा ३२ बमोजिम ३ दिने स्पष्टीकरण सोधिएको"),
    ]
    for p_name, s_st, att_st, v_cast, c_st, d_act, rem in roll_call_data:
        if p_name in pm:
            con.execute(
                "INSERT INTO whip_members(whip_id,parliamentarian_id,served_status,served_at,attendance_status,vote_cast,compliance_status,disciplinary_action,remarks) VALUES(?,?,?,?,?,?,?,?,?)",
                (whip1_id, pm[p_name], s_st, ts, att_st, v_cast, c_st, d_act, rem)
            )

    # ------------------------------------------------------------- 11. Floor Speaker Rosters (सदन वक्ता तालिका)
    rosters_data = [
        ("House of Representatives", day(0), "Zero Hour", pm["Hon. Bimal Sharma"],
         "काठमाडौँ उपत्यकाको चक्रपथ विस्तार तथा धुलो नियन्त्रण", 1, 1,
         "१. कलंकी-महाराजगन्ज सडक खण्डको ढिलासुस्ती\n२. खानेपानी र ढल निर्माणका कारण सिर्जित जनस्वास्थ्य जोखिम\n३. भौतिक पूर्वाधार मन्त्रालयको ध्यानाकर्षण।",
         None, "Scheduled", uid["chiefwhip@pms.test"]),

        ("House of Representatives", day(0), "Zero Hour", pm["Hon. Manju Chaudhary"],
         "दाङ उपत्यकामा समयमै रासायनिक मल आपूर्ति सम्बन्धी", 1, 2,
         "१. धान रोपाईको समयमा युरिया र डिएपी मलको चरम अभाव\n२. कृषि सामग्री कम्पनीको आपूर्ति प्रणालीमा सुधार\n३. किसानलाई तत्काल राहत।",
         None, "Scheduled", uid["chiefwhip@pms.test"]),

        ("House of Representatives", day(0), "Special Hour", pm["Hon. Anita Rai"],
         "अर्थतन्त्रमा सुधार, युवा पलायन नियन्त्रण र आन्तरिक रोजगारी प्रवर्द्धन", 5, 1,
         "१. बैंक ब्याजदर र निजी क्षेत्रको लगानी संकुचन\n२. दैनिक २ हजार युवा वैदेशिक रोजगारीमा जानुपर्ने बाध्यता\n३. स्वदेशी उत्पादन र स्टार्ट-अपलाई कर छुट।",
         None, "Submitted to Secretariat", uid["chiefwhip@pms.test"]),

        ("House of Representatives", day(1), "Bill Discussion", pm["Hon. Ramesh Adhikari"],
         "संघीय निजामती सेवा विधेयकमा ट्रेड युनियन अधिकार र कर्मचारी समायोजन", 10, 1,
         "१. स्थायी सरकारको रुपमा निजामती प्रशासनको तटस्थता\n२. आधिकारिक ट्रेड युनियनको मात्र व्यवस्था\n३. दुर्गममा काम गर्ने कर्मचारीलाई विशेष वृत्ति विकास।",
         None, "Scheduled", uid["chiefwhip@pms.test"]),
    ]
    for h, s_date, s_type, p_id, topic, mins, s_ord, t_pts, b_id, s_st, cr_by in rosters_data:
        con.execute(
            "INSERT INTO speaker_rosters(house,session_date,session_type,parliamentarian_id,topic,allocated_minutes,speaking_order,talking_points,bill_id,status,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (h, s_date, s_type, p_id, topic, mins, s_ord, t_pts, b_id, s_st, cr_by, ts)
        )

    # ------------------------------------------------------------- 12. MP Leaves (संविधान धारा ८९(घ) अनुगमन)
    leaves_data = [
        (pm["Hon. Manju Chaudhary"], "Medical", day(-4), day(2), 7,
         "अस्पतालमा स्वास्थ्य परीक्षण तथा चिकित्सकको सल्लाह अनुसार आराम।", "Approved", uid["chiefwhip@pms.test"]),
        (pm["Hon. Rajendra Paswan"], "Constituency Visit", day(-10), day(-6), 5,
         "सप्तरी निर्वाचन क्षेत्रमा बाढी तथा डुबान प्रभावित क्षेत्रको स्थलगत अनुगमन र राहत समन्वय।", "Approved", uid["chiefwhip@pms.test"]),
    ]
    for p_id, l_type, s_date, e_date, d_cnt, reas, l_st, app_by in leaves_data:
        con.execute(
            "INSERT INTO mp_leaves(parliamentarian_id,leave_type,start_date,end_date,days_count,reason,status,approved_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (p_id, l_type, s_date, e_date, d_cnt, reas, l_st, app_by, ts)
        )

    # ------------------------------------------------------------- 13. Activity Logs
    for b, action, detail in [
        (cyber, "created bill", "Cybersecurity and Digital Safety Bill, 2083"),
        (fin, "assigned researcher", "Hari Researcher"),
        (fin, "assigned parliamentarian", "Hon. Anita Rai"),
        (energy, "recorded party position", "Support with amendments (decided by Parliamentary Party Committee)"),
    ]:
        con.execute(
            "INSERT INTO activity_logs(actor_id,action,entity_type,entity_id,detail,timestamp) VALUES(?,?,?,?,?,?)",
            (uid["coordinator@pms.test"], action, "bill", b, detail, ts)
        )

    con.commit()
    con.close()
