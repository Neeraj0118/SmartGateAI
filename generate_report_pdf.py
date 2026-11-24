import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#6B7280"))

        # Don't draw header/footer on cover/first page if desired, or draw subtle ones
        if self._pageNumber > 1:
            # Header
            self.drawString(45, 800, "SmartGateAI — Phase 1 Project Report | Academic Documentation")
            self.setStrokeColor(colors.HexColor("#E5E7EB"))
            self.setLineWidth(0.5)
            self.line(45, 792, 550, 792)

        # Footer
        self.setStrokeColor(colors.HexColor("#E5E7EB"))
        self.setLineWidth(0.5)
        self.line(45, 45, 550, 45)
        
        self.drawString(45, 32, "Confidential — SmartGateAI Academic Project Submission")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(550, 32, page_text)
        self.restoreState()


def create_pdf(output_filename):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=A4,
        leftMargin=45,
        rightMargin=45,
        topMargin=50,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#1A4731")    # Deep Forest Green
    secondary_color = colors.HexColor("#2B2D2F")  # Charcoal
    accent_color = colors.HexColor("#B45309")     # Amber / Gold
    text_color = colors.HexColor("#1F2937")       # Dark Grey

    styles.add(ParagraphStyle(
        name='DocTitle',
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=primary_color,
        spaceAfter=6,
        alignment=0
    ))

    styles.add(ParagraphStyle(
        name='DocSubtitle',
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=secondary_color,
        spaceAfter=15,
        alignment=0
    ))

    styles.add(ParagraphStyle(
        name='SectionHeader',
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        name='SubsectionHeader',
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=secondary_color,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        name='CustomBody',
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=text_color,
        spaceAfter=6
    ))

    styles.add(ParagraphStyle(
        name='CustomBodyBold',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=14,
        textColor=text_color,
        spaceAfter=6
    ))

    styles.add(ParagraphStyle(
        name='BulletItem',
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=text_color,
        leftIndent=15,
        spaceAfter=3
    ))

    styles.add(ParagraphStyle(
        name='CalloutBoxText',
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#92400E")
    ))

    styles.add(ParagraphStyle(
        name='TableHeader',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=0
    ))

    styles.add(ParagraphStyle(
        name='TableCell',
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=text_color,
        alignment=0
    ))

    styles.add(ParagraphStyle(
        name='TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=text_color,
        alignment=0
    ))

    story = []

    # Title & Metadata
    story.append(Paragraph("SmartGateAI: AI-Powered Smart Campus Gate Monitoring & Hostel Exit Permission System", styles['DocTitle']))
    story.append(Paragraph("<b>Phase 1 Project Report & Technical Architecture</b> | Automated Biometric Security", styles['DocSubtitle']))
    
    meta_data = [
        [Paragraph("<b>Project Phase:</b> Phase 1 (Completed & Verified)", styles['TableCell']),
         Paragraph("<b>Student / Lead:</b> Neeraj Giri (ID: 230111472)", styles['TableCell'])],
        [Paragraph("<b>Core Stack:</b> FastAPI, React 19, OpenCV YuNet+SFace", styles['TableCell']),
         Paragraph("<b>Database:</b> Local SQLite (On-Premises)", styles['TableCell'])]
    ]
    meta_table = Table(meta_data, colWidths=[250, 255])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F3F7F4")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBDAD0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2ECE5")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # SECTION 1: EXECUTIVE SUMMARY
    story.append(Paragraph("1. Executive Summary & Project Abstract", styles['SectionHeader']))
    story.append(Paragraph(
        "Educational institutions, universities, and residential campuses face escalating operational challenges "
        "in monitoring student movements, managing hostel curfew rules, preventing proxy entries, and safeguarding "
        "campus perimeters. Traditional manual register logs and physical guard inspections suffer from long waiting queues, "
        "handwriting illegibility, proxy attendance, and an inability to detect intruders or unreturned hostellers in real time.",
        styles['CustomBody']
    ))
    story.append(Paragraph(
        "<b>SmartGateAI</b> resolves these issues by implementing an end-to-end automated campus access control system. "
        "It deploys high-speed computer vision at campus gates, coupling deep facial embeddings with strict residential "
        "authorization policies.",
        styles['CustomBody']
    ))

    # Scope Callout Box
    scope_data = [[
        Paragraph(
            "<b>Important Phase 1 Scope Distinction:</b><br/>"
            "Phase 1 exclusively implements <b>Person Biometrics, Dual-Gate Flow Management (ENTRY vs. EXIT), and Smart Hostel "
            "Exit Permission Tracking</b>. The <b>Vehicle Monitoring & Automatic Number Plate Recognition (ANPR)</b> system is "
            "strictly designated as <b>Future Scope (Phase 2)</b>.",
            styles['CalloutBoxText']
        )
    ]]
    scope_table = Table(scope_data, colWidths=[505])
    scope_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FEF3C7")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#F59E0B")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(scope_table)
    story.append(Spacer(1, 10))

    # SECTION 2: PROBLEM STATEMENT & OBJECTIVES
    story.append(Paragraph("2. Problem Statement & System Objectives", styles['SectionHeader']))
    story.append(Paragraph("<b>2.1 Weaknesses of Existing Campus Access Systems:</b>", styles['SubsectionHeader']))
    story.append(Paragraph("• <b>Manual Logbooks:</b> Easily forged, slow throughput during morning/evening rush hours, prone to log loss.", styles['BulletItem']))
    story.append(Paragraph("• <b>Smart Card / RFID Proxy:</b> Students routinely share physical ID cards with friends to fake presence or exit.", styles['BulletItem']))
    story.append(Paragraph("• <b>Hostel Curfew Blindspots:</b> Wardens have no automated visibility when hostellers exit without passes or return late.", styles['BulletItem']))
    story.append(Paragraph("• <b>Unknown Intruders:</b> Guards cannot cross-check every face against thousands of registered campus members.", styles['BulletItem']))
    
    story.append(Paragraph("<b>2.2 Core Phase 1 Objectives:</b>", styles['SubsectionHeader']))
    story.append(Paragraph("• <b>Sub-100ms Biometric Matching:</b> On-premises face detection and cosine similarity matching on standard CPU hardware.", styles['BulletItem']))
    story.append(Paragraph("• <b>Dual-Gate Intelligence:</b> Dedicated operational logic for ENTRY gates (arrival) and EXIT gates (permission enforcement).", styles['BulletItem']))
    story.append(Paragraph("• <b>Residential Categorization:</b> Day Scholars receive immediate exit clearance; Hostellers require an approved active exit pass.", styles['BulletItem']))
    story.append(Paragraph("• <b>Single-Use Atomic Pass Lifecycle:</b> Eliminates pass reuse and automatically tracks off-campus active outings.", styles['BulletItem']))
    story.append(Spacer(1, 10))

    # SECTION 3: SYSTEM ARCHITECTURE & TECH STACK
    story.append(Paragraph("3. System Architecture & Technology Stack", styles['SectionHeader']))
    story.append(Paragraph(
        "SmartGateAI utilizes a high-throughput, microservice-ready architecture comprising an edge AI pipeline, "
        "asynchronous FastAPI application server, local relational database, and a responsive React 19 administrative portal.",
        styles['CustomBody']
    ))

    tech_table_data = [
        [Paragraph("<b>Component</b>", styles['TableHeader']), Paragraph("<b>Technology</b>", styles['TableHeader']), Paragraph("<b>Architectural Role & Description</b>", styles['TableHeader'])],
        [Paragraph("<b>Backend API</b>", styles['TableCellBold']), Paragraph("FastAPI (Python 3.11)", styles['TableCell']), Paragraph("Asynchronous REST service, OpenAPI/Swagger docs, Pydantic schema validation.", styles['TableCell'])],
        [Paragraph("<b>Face Detection</b>", styles['TableCellBold']), Paragraph("YuNet (OpenCV Zoo)", styles['TableCell']), Paragraph("Ultra-lightweight edge detector (ONNX), ~15ms inference, multi-face tracking.", styles['TableCell'])],
        [Paragraph("<b>Face Recognition</b>", styles['TableCellBold']), Paragraph("SFace (OpenCV Zoo)", styles['TableCell']), Paragraph("Deep CNN generating compact 128-dimensional unit hypersphere feature vectors.", styles['TableCell'])],
        [Paragraph("<b>Vector Matcher</b>", styles['TableCellBold']), Paragraph("In-Memory Cosine Similarity", styles['TableCell']), Paragraph("Instant vector comparison (>0.36 cosine threshold) with zero latency.", styles['TableCell'])],
        [Paragraph("<b>Database</b>", styles['TableCellBold']), Paragraph("SQLite 3 + SQLAlchemy", styles['TableCell']), Paragraph("Local relational database storing profiles, BLOB vectors, logs, and passes.", styles['TableCell'])],
        [Paragraph("<b>Frontend SPA</b>", styles['TableCellBold']), Paragraph("React 19 + Vite", styles['TableCell']), Paragraph("Sub-second live monitor HUD, administrative portals, and responsive UI.", styles['TableCell'])],
        [Paragraph("<b>UI Styling</b>", styles['TableCellBold']), Paragraph("TailwindCSS + Lucide Icons", styles['TableCell']), Paragraph("Institutional color palette (Forest Green, Charcoal, Warm Ivory).", styles['TableCell'])],
        [Paragraph("<b>Security / Auth</b>", styles['TableCellBold']), Paragraph("Header-only API Key", styles['TableCell']), Paragraph("Strict header enforcement (X-Admin-API-Key) with session memory protection.", styles['TableCell'])]
    ]
    t1 = Table(tech_table_data, colWidths=[95, 115, 295])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#D1D5DB")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
    ]))
    story.append(t1)
    story.append(Spacer(1, 10))

    # SECTION 4: PHASE 1 CORE IMPLEMENTATION MODULES
    story.append(Paragraph("4. Phase 1 Core Implemented Modules", styles['SectionHeader']))
    
    story.append(Paragraph("<b>4.1 Biometric Registration & Embeddings Pipeline:</b>", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Students enroll using 1 to 2 facial photographs. The system enforces strict digital consent compliance "
        "(<code>consent_given=True</code>). Raw photographs are converted into normalized 128-D float32 vectors and stored "
        "as binary BLOBs. The VectorMatcher cache dynamically refreshes in memory without requiring server restarts.",
        styles['CustomBody']
    ))

    story.append(Paragraph("<b>4.2 Dual-Gate Operational Workflows (ENTRY vs. EXIT):</b>", styles['SubsectionHeader']))
    story.append(Paragraph(
        "• <b>ENTRY Gate Workflow:</b> Prioritizes seamless campus arrival. When a recognized hosteller arrives, the system "
        "queries their active outing record and automatically marks it <b>Returned</b> with the exact return timestamp, "
        "simultaneously resolving any late-return alerts. Entry is never challenged or blocked.",
        styles['CustomBody']
    ))
    story.append(Paragraph(
        "• <b>EXIT Gate Workflow (Hostel Verification):</b> Day Scholars receive immediate exit approval with departure attendance logged. "
        "For Hostellers, the gate engine inspects active digital passes. If an approved pass exists within the current validity window, "
        "it is atomically transitioned to <b>Used</b>, an active outing is recorded, and green HUD clearance is granted. "
        "If no valid pass is found, exit is <b>DENIED</b>, a crimson red HUD alert appears, an audio alarm sounds, and a security alert is recorded.",
        styles['CustomBody']
    ))

    story.append(Paragraph("<b>4.3 Smart Hostel Exit Permission Lifecycle:</b>", styles['SubsectionHeader']))
    story.append(Paragraph(
        "1. <b>Creation:</b> Wardens submit Student ID, Departure Window (Date/Time IST), Return Window, and Reason.<br/>"
        "2. <b>Review & Approval:</b> Authorized staff approve or reject with audit notes (<code>approved_by</code>, <code>rejection_reason</code>).<br/>"
        "3. <b>Atomic Single-Use:</b> Once a pass is verified at the exit camera, it transitions to <b>Used</b>. Re-exit attempts with the same pass are blocked.<br/>"
        "4. <b>Auto-Expiration:</b> Unused approved passes whose expected return window has elapsed are automatically marked <b>Expired</b>.",
        styles['CustomBody']
    ))

    story.append(Paragraph("<b>4.4 Automated Late Return & Real-Time Threat Alerts:</b>", styles['SubsectionHeader']))
    story.append(Paragraph(
        "The system background engine regularly checks active outings. If the current time exceeds the <code>expected_return_time</code>, "
        "the outing status transitions to <b>Late</b> and a high-severity <code>LATE_RETURN</code> security alert is posted to the dashboard. "
        "Similarly, unrecognized faces at either gate trigger live <code>UNKNOWN PERSON DETECTED</code> banners and audio chimes.",
        styles['CustomBody']
    ))

    story.append(Paragraph("<b>4.5 Security Dashboard & Administrative Web Interface:</b>", styles['SubsectionHeader']))
    story.append(Paragraph(
        "Built with React 19, the interface features a real-time Security Dashboard with traffic metrics, a Live Monitor with MJPEG video "
        "and HUD bounding boxes, a Student Management console with residential category badges, and a comprehensive Hostel Passes portal.",
        styles['CustomBody']
    ))
    story.append(Spacer(1, 10))

    # SECTION 5: DATABASE SCHEMA & STORAGE
    story.append(Paragraph("5. Database Schema & Local Storage Architecture", styles['SectionHeader']))
    story.append(Paragraph(
        "All data is hosted strictly on-premises in SQLite (<code>backend/storage/smartgate.db</code>), ensuring zero external cloud leakage:",
        styles['CustomBody']
    ))

    db_table_data = [
        [Paragraph("<b>Table Name</b>", styles['TableHeader']), Paragraph("<b>Primary Function</b>", styles['TableHeader']), Paragraph("<b>Key Columns & Schema Details</b>", styles['TableHeader'])],
        [Paragraph("<code>students</code>", styles['TableCellBold']), Paragraph("Core student identity & category", styles['TableCell']), Paragraph("student_id, full_name, department, category (Day Scholar/Hosteller), hostel_name, room_number", styles['TableCell'])],
        [Paragraph("<code>face_embeddings</code>", styles['TableCellBold']), Paragraph("128-D facial feature vectors", styles['TableCell']), Paragraph("embedding_blob (binary BLOB), photo_path (storage/student_photos/)", styles['TableCell'])],
        [Paragraph("<code>recognition_events</code>", styles['TableCellBold']), Paragraph("Historical gate audit log", styles['TableCell']), Paragraph("student_id, event_type (entry/exit), gate_id, similarity, captured_at", styles['TableCell'])],
        [Paragraph("<code>hostel_permissions</code>", styles['TableCellBold']), Paragraph("Digital hostel exit passes", styles['TableCell']), Paragraph("student_id, departure_date/time, expected_return_date/time, status, approved_by", styles['TableCell'])],
        [Paragraph("<code>active_outings</code>", styles['TableCellBold']), Paragraph("Students currently outside campus", styles['TableCell']), Paragraph("permission_id, student_id, actual_exit_time, expected_return_time, status (Out/Late/Returned)", styles['TableCell'])],
        [Paragraph("<code>security_alerts</code>", styles['TableCellBold']), Paragraph("Gate denial & curfew incidents", styles['TableCell']), Paragraph("alert_type (HOSTEL_EXIT_DENIED, LATE_RETURN, UNKNOWN_FACE), severity, is_resolved", styles['TableCell'])]
    ]
    t2 = Table(db_table_data, colWidths=[105, 140, 260])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#D1D5DB")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    # SECTION 6: VERIFICATION & TEST RESULTS
    story.append(Paragraph("6. Empirical Verification & Test Results", styles['SectionHeader']))
    story.append(Paragraph(
        "All Phase 1 modules were validated against real database transactions, live camera simulations, and production builds:",
        styles['CustomBody']
    ))

    test_table_data = [
        [Paragraph("<b>Automated Test Suite</b>", styles['TableHeader']), Paragraph("<b>Tests</b>", styles['TableHeader']), Paragraph("<b>Status</b>", styles['TableHeader']), Paragraph("<b>Verified Functionality</b>", styles['TableHeader'])],
        [Paragraph("<b>Hostel Integration</b> (<code>test_hostel_exit_permission.py</code>)", styles['TableCellBold']), Paragraph("8 / 8", styles['TableCell']), Paragraph("<font color='#059669'><b>PASS</b></font>", styles['TableCell']), Paragraph("Day Scholar exit, missing pass denial, approved pass authorization, single-use check, late return, auto-return on entry.", styles['TableCell'])],
        [Paragraph("<b>Hostel API Smoke</b> (<code>test_hostel_api_smoke.py</code>)", styles['TableCellBold']), Paragraph("6 / 6", styles['TableCell']), Paragraph("<font color='#059669'><b>PASS</b></font>", styles['TableCell']), Paragraph("Auth header verification, pass creation, filtering, approval lifecycle, active outings listing, security alert queries.", styles['TableCell'])],
        [Paragraph("<b>REST Security Suite</b> (<code>test_api_endpoints.py</code>)", styles['TableCellBold']), Paragraph("10 / 10", styles['TableCell']), Paragraph("<font color='#059669'><b>PASS</b></font>", styles['TableCell']), Paragraph("API key protection, consent enforcement, 2-photo enrollment, zero biometric leakage, cascade deletion.", styles['TableCell'])],
        [Paragraph("<b>IST Timestamps & Gate Modes</b> (<code>test_ist_and_gate_modes.py</code>)", styles['TableCellBold']), Paragraph("5 / 5", styles['TableCell']), Paragraph("<font color='#059669'><b>PASS</b></font>", styles['TableCell']), Paragraph("Asia/Kolkata timezone formatting, separate entry/exit event logging, campus presence calculation, dynamic gate mode toggle.", styles['TableCell'])],
        [Paragraph("<b>Frontend Production Build</b> (<code>npm run build</code>)", styles['TableCellBold']), Paragraph("2,605 mod", styles['TableCell']), Paragraph("<font color='#059669'><b>SUCCESS</b></font>", styles['TableCell']), Paragraph("Clean compilation of Vite React bundle with zero syntax, build, or type errors.", styles['TableCell'])]
    ]
    t3 = Table(test_table_data, colWidths=[120, 45, 55, 285])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#D1D5DB")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9FAFB")]),
    ]))
    story.append(t3)
    story.append(Spacer(1, 10))

    # SECTION 7: FUTURE SCOPE
    story.append(Paragraph("7. Future Scope (Phase 2 & Beyond)", styles['SectionHeader']))
    
    # Vehicle Callout
    veh_box = [[
        Paragraph(
            "<b>7.1 Vehicle Monitoring & Automatic Number Plate Recognition (ANPR / ALPR) — Explicit Future Scope:</b><br/>"
            "While Phase 1 provides complete person biometrics and gate permissions, the <b>Vehicle & ANPR module is planned for Phase 2</b>. "
            "The <code>vehicle_registrations</code> database table serves as an architectural placeholder for this expansion.",
            styles['CustomBodyBold']
        )
    ]]
    veh_table = Table(veh_box, colWidths=[505])
    veh_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#3B82F6")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(veh_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph("• <b>YOLOv8 License Plate Detection:</b> High-speed localization of vehicle number plates under varied angles, weather, and lighting.", styles['BulletItem']))
    story.append(Paragraph("• <b>OCR Plate Reader (PaddleOCR):</b> Optical character recognition extracting alphanumeric plate characters for automated matching.", styles['BulletItem']))
    story.append(Paragraph("• <b>Driver-Vehicle Cross Verification:</b> Cross-referencing recognized vehicles with the enrolled student/faculty driver in real time.", styles['BulletItem']))
    story.append(Paragraph("• <b>Visitor Vehicle Duration Alerts:</b> Automatic detection of unauthorized or overstayed guest vehicles parked inside campus.", styles['BulletItem']))
    
    story.append(Paragraph("<b>7.2 Hardware Interfacing & Extended Capabilities:</b>", styles['SubsectionHeader']))
    story.append(Paragraph("• <b>Physical Barrier Automation (IoT):</b> Microcontroller (ESP32 / Arduino) relay interfacing to actuate motorized boom barriers.", styles['BulletItem']))
    story.append(Paragraph("• <b>Guardian SMS & WhatsApp Alerts:</b> Instant dispatch of automated alerts to parents and wardens when a student is overdue.", styles['BulletItem']))
    story.append(Paragraph("• <b>Edge AI Hardware:</b> Direct deployment on Nvidia Jetson Orin Nano / Raspberry Pi 5 boards mounted at gate barrier posts.", styles['BulletItem']))
    story.append(Paragraph("• <b>Emergency QR Backup:</b> Fallback cryptographic QR scanning on student mobile phones during extreme weather conditions.", styles['BulletItem']))
    story.append(Spacer(1, 10))

    # SECTION 8: CONCLUSION
    story.append(Paragraph("8. Conclusion", styles['SectionHeader']))
    story.append(Paragraph(
        "Phase 1 of <b>SmartGateAI</b> establishes a production-ready, privacy-respecting, and reliable gate monitoring system. "
        "By replacing error-prone manual registers with sub-100ms face recognition, distinguishing Day Scholars from Hostellers, "
        "and implementing an atomic digital exit pass lifecycle, the project solves real-world campus security challenges with 100% "
        "on-premises reliability. The platform is modular, fully verified by automated test suites, and architected for seamless "
        "integration with Phase 2 vehicle and license plate recognition.",
        styles['CustomBody']
    ))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] PDF generated successfully: {output_filename}")


if __name__ == "__main__":
    out_path = r"C:\Users\neera\OneDrive\Desktop\SmartGateAI\SmartGateAI_Phase_1_Project_Report.pdf"
    create_pdf(out_path)
