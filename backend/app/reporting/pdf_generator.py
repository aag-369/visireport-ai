"""Real multi-page NCR PDF generation via ReportLab."""
import io
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

SEVERITY_COLORS = {
    "CRITICAL": colors.HexColor("#FF3B3B"),
    "MAJOR": colors.HexColor("#FFB020"),
    "MINOR": colors.HexColor("#00A651"),
}


def build_ncr_pdf(inspection: dict, narrative: dict | None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("VRTitle", parent=styles["Title"], textColor=colors.HexColor("#0A0C0F"))
    h2 = ParagraphStyle("VRH2", parent=styles["Heading2"], textColor=colors.HexColor("#111418"))
    body = styles["BodyText"]
    mono_small = ParagraphStyle("mono", parent=styles["BodyText"], fontName="Courier", fontSize=8)

    elements = []
    elements.append(Paragraph("VisiReport AI — Non-Conformance Report (NCR)", title_style))
    elements.append(Paragraph("ISO 13485:2016 Cl. 8.3 (Control of Nonconforming Product) &amp; Cl. 8.5.2 (Corrective Action)", mono_small))
    elements.append(Spacer(1, 0.2 * inch))

    header_data = [
        ["Report ID", inspection["report_id"], "Board ID", inspection["board_id"]],
        ["Inspection Timestamp", str(inspection["inspection_timestamp"]), "Disposition", inspection["board_disposition"]],
        ["Cycle Time (ms)", str(inspection.get("cycle_time_ms", "-")), "Schema Valid", str(inspection.get("schema_valid", "-"))],
    ]
    header_table = Table(header_data, colWidths=[1.6 * inch, 2.1 * inch, 1.3 * inch, 1.6 * inch])
    header_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EDF5")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#E8EDF5")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#8896A8")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ]
        )
    )
    elements.append(header_table)
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("Defect Registry", h2))
    defect_rows = [["Defect ID", "Class", "Severity", "Confidence", "BBox (x,y,w,h)", "Status"]]
    for d in inspection.get("defects", []):
        bbox = d["global_bbox"]
        defect_rows.append(
            [
                d["defect_id"],
                d["class"],
                d["iso_severity"],
                f"{d['confidence']:.2f}",
                f"{bbox['x']},{bbox['y']},{bbox['w']},{bbox['h']}",
                d["status"],
            ]
        )
    if len(defect_rows) == 1:
        defect_rows.append(["-", "No defects detected", "-", "-", "-", "-"])

    defect_table = Table(defect_rows, repeatRows=1, colWidths=[0.9 * inch, 0.9 * inch, 0.8 * inch, 0.8 * inch, 1.4 * inch, 0.9 * inch])
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A1F26")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#8896A8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F4F7")]),
    ]
    for row_idx, d in enumerate(inspection.get("defects", []), start=1):
        sev_color = SEVERITY_COLORS.get(d["iso_severity"])
        if sev_color:
            style_cmds.append(("TEXTCOLOR", (2, row_idx), (2, row_idx), sev_color))
    defect_table.setStyle(TableStyle(style_cmds))
    elements.append(defect_table)
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("NCR Narrative", h2))
    if narrative and narrative.get("narrative_text"):
        elements.append(Paragraph(narrative["narrative_text"], body))
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(Paragraph("Root Cause Hypothesis", h2))
        elements.append(Paragraph(narrative.get("root_cause_text") or "-", body))
        elements.append(Spacer(1, 0.15 * inch))
        elements.append(Paragraph("CAPA (Corrective and Preventive Action)", h2))
        capa = narrative.get("capa") or {}
        if isinstance(capa, str):
            try:
                capa = json.loads(capa)
            except Exception:
                capa = {}
        for label, key in [
            ("Immediate Containment", "immediate_containment"),
            ("Root Cause Elimination", "root_cause_elimination"),
            ("Preventive Measure", "preventive_measure"),
        ]:
            elements.append(Paragraph(f"<b>{label}:</b> {capa.get(key, '-')}", body))
    else:
        status = (narrative or {}).get("status", "PENDING")
        elements.append(
            Paragraph(
                f"Narrative not yet available (status: {status}). This report reflects the defect "
                "registry only; regenerate the PDF once LLM synthesis completes.",
                body,
            )
        )

    doc.build(elements)
    return buf.getvalue()
