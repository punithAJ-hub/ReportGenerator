# pdf_generator.py
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from io import BytesIO
from PIL import Image as PILImage
import datetime

# ---------- Constants ----------
STATIC_OBS_TEXT = (
    "The purpose of this site visit was to observe and review the grade beams, and to determine whether "
    "the work of the contractor was in general conformance with the structural construction documents. "
    "See Figure 1.00 for the overview of the construction site. During the observation visit, the grade "
    "beams highlighted in figure 1.01 were observed. Typical grade beam reinforcement were provided in "
    "conformance with structural drawings. Grade beam excavation and reinforcing work for several grade "
    "beams were still ongoing at the time of visit. Overall construction matched the requirements of "
    "structural drawings in the observed area except as listed below:"
)
DISCLAIMER = (
    "THE VISUAL FIELD OBSERVATIONS BY THE STRUCTURAL ENGINEER SHALL NOT BE CONSTRUED AS A CONTINUOUS OR "
    "EXHAUSTIVE PROJECT REVIEW. THESE OBSERVATIONS ARE NOT A WAIVER OF THE GENERAL CONTRACTOR (OR ANY ENTITY "
    "FURNISHING MATERIALS OR PERFORMING WORK ON THE PROJECT) FROM RESPONSIBILITY AND/OR PERFORMANCE IN "
    "ACCORDANCE WITH THE REQUIREMENTS OF THE CONTRACT DOCUMENTS AND SPECIFICATIONS."
)
BRAND_BLUE = colors.Color(0/255, 85/255, 153/255)  # #005599

# ---------- Helpers ----------
def _fmt_dt(dt, with_time=False):
    if not dt:
        return ""
    if isinstance(dt, (datetime.datetime, datetime.date)):
        if with_time and isinstance(dt, datetime.datetime):
            return dt.strftime("%m/%d/%Y %I:%M %p")
        return dt.strftime("%m/%d/%Y")
    return str(dt)

def _img_from_bytes(img_bytes, max_w, max_h):
    if not img_bytes:
        return None
    try:
        pil = PILImage.open(BytesIO(img_bytes)).convert("RGB")
        pil.thumbnail((int(max_w), int(max_h)))
        out = BytesIO()
        pil.save(out, format="JPEG", quality=85)
        out.seek(0)
        rl_img = RLImage(out)
        rl_img._restrictSize(max_w, max_h)
        return rl_img
    except Exception:
        return None

def _make_logo_reader(logo_bytes, target_width=1.6*inch):
    """Return (ImageReader, width, height) scaled to target_width."""
    if not logo_bytes:
        return None, 0, 0
    pil = PILImage.open(BytesIO(logo_bytes))
    w, h = pil.size
    scale = target_width / float(w)
    new_w, new_h = target_width, h * scale
    bio = BytesIO()
    pil.save(bio, format="PNG")
    bio.seek(0)
    return ImageReader(bio), new_w, new_h

def _draw_footer(canvas: Canvas, doc, footer_address: str):
    """Centered blue disclaimer + centered bold blue address + page number (right)."""
    canvas.saveState()
    width, height = LETTER

    # Styles for drawing paragraphs
    footer_style = ParagraphStyle(name="FooterSmall", fontName="Helvetica", fontSize=7, leading=9,
                                  textColor=BRAND_BLUE, alignment=TA_CENTER)
    address_style = ParagraphStyle(name="FooterAddress", fontName="Helvetica-Bold", fontSize=10, leading=12,
                                   textColor=BRAND_BLUE, alignment=TA_CENTER)

    disclaimer_para = Paragraph(DISCLAIMER, footer_style)
    avail_width = doc.width
    # Position just above the very bottom; we stack: disclaimer (y+20), address (y+8), number at (y+8)
    base_y = 8  # baseline above the page edge
    w, h = disclaimer_para.wrap(avail_width, 200)
    disclaimer_para.drawOn(canvas, doc.leftMargin, base_y + 20)

    if footer_address:
        address_para = Paragraph(footer_address, address_style)
        aw, ah = address_para.wrap(avail_width, 60)
        address_para.drawOn(canvas, doc.leftMargin, base_y + 8)

    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.black)
    canvas.drawRightString(width - doc.rightMargin, base_y + 8, str(canvas.getPageNumber()))
    canvas.restoreState()

def _draw_logo(canvas: Canvas, doc, logo_reader, logo_w, logo_h):
    """Draw logo at top-right inside page margins (on EVERY page)."""
    if not logo_reader:
        return
    width, height = LETTER
    x = doc.leftMargin + doc.width - logo_w
    y = height - doc.topMargin - logo_h + 6  # small nudge down like sample
    canvas.drawImage(logo_reader, x, y, width=logo_w, height=logo_h, mask='auto')

# ---------- Main ----------
def generate_pdf(data: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=1.15*inch,  # a bit more for centered footer
        title=f"{data.get('project_number','')}_{data.get('title','')}_Field_Report",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleMain", fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=8))
    styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10, leading=14))
    styles.add(ParagraphStyle(name="ObsPara", fontName="Helvetica", fontSize=10, leading=14, alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name="ObsItem", fontName="Helvetica", fontSize=10, leading=14, alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name="Sig", fontName="Helvetica-Bold", fontSize=11, leading=15, spaceBefore=8))

    story = []

    # Title (logo will be drawn by the page callback on all pages)
    story.append(Paragraph("F I E L D  R E P O R T", styles["TitleMain"]))
    story.append(Spacer(1, 6))

    # Bullet rows (■ label | value)
    bullet = '<font size="14">■</font>'
    rows = []

    proj_val = f"{(data.get('project_number') or '').strip()} {(data.get('title') or '').strip()}".strip()
    rows.append([Paragraph(f"{bullet}  <b>Project:</b>", styles["Body"]), Paragraph(proj_val, styles["Body"])])
    rows.append([Paragraph(f"{bullet}  <b>Address:</b>", styles["Body"]), Paragraph(str(data.get('project_address','')), styles["Body"])])
    rows.append([Paragraph(f"{bullet}  <b>Client:</b>", styles["Body"]), Paragraph(str(data.get('client_name','')), styles["Body"])])

    dv = _fmt_dt(data.get("date_visited"))
    dv_line = f"{dv}, {data.get('weather','')}".strip(", ")
    rows.append([Paragraph(f"{bullet}  <b>Date of Visit:</b>", styles["Body"]), Paragraph(dv_line, styles["Body"])])

    dor = _fmt_dt(data.get("date_of_report"))
    rows.append([Paragraph(f"{bullet}  <b>Date of Report:</b>", styles["Body"]), Paragraph(dor, styles["Body"])])

    present_txt = ", ".join([p for p in (data.get("present") or []) if str(p).strip()])
    rows.append([Paragraph(f"{bullet}  <b>Present:</b>", styles["Body"]), Paragraph(present_txt, styles["Body"])])

    # Observations: static text + (optional) extra obs from user + numbered list from media descriptions
    media = data.get("media") or []
    obs_cells = [Paragraph(STATIC_OBS_TEXT, styles["ObsPara"])]
    if data.get("observations"):
        obs_cells.append(Paragraph((data["observations"]).replace("\n", "<br/>"), styles["ObsPara"]))
    for i, m in enumerate(media, start=1):
        desc = (m.get("description") or "").strip()
        if desc:
            obs_cells.append(Paragraph(f"{i}. {desc}", styles["ObsItem"]))
    obs_tbl = Table([[obs_cells]], colWidths=[5.3*inch])
    obs_tbl.setStyle(TableStyle([("LEFTPADDING",(0,0),(-1,-1),0), ("RIGHTPADDING",(0,0),(-1,-1),0)]))
    rows.append([Paragraph(f"{bullet}  <b>Observations:</b>", styles["Body"]), obs_tbl])

    # Remarks
    rows.append([Paragraph(f"{bullet}  <b>Remarks:</b>", styles["Body"]),
                 Paragraph(str(data.get("remarks","")), styles["Body"])])

    info_tbl = Table(rows, colWidths=[1.5*inch, 5.3*inch])
    info_tbl.setStyle(TableStyle([
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 8))

    # Sign-off
    if data.get("prepared_by"):
        story.append(Paragraph(str(data["prepared_by"]), styles["Sig"]))
        story.append(Paragraph("Graduate Engineer", styles["Sig"]))
        story.append(Paragraph("MSE", styles["Sig"]))

    # ===== Page 2+: Media Table =====
    story.append(PageBreak())
    tbl_data = [[Paragraph("<b>Item Number</b>", styles["Body"]),
                 Paragraph("<b>Photo</b>", styles["Body"]),
                 Paragraph("<b>Comment/Action</b>", styles["Body"])]]
    for idx, item in enumerate(media, start=1):
        rl_img = _img_from_bytes(item.get("image_bytes"), max_w=2.9*inch, max_h=2.1*inch)
        desc = Paragraph((item.get("description") or "").replace("\n","<br/>"), styles["Body"])
        tbl_data.append([Paragraph(f"Figure {idx}", styles["Body"]), rl_img or Paragraph("—", styles["Body"]), desc])

    media_tbl = Table(tbl_data, colWidths=[1.1*inch, 2.9*inch, 3.4*inch], repeatRows=1)
    media_tbl.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.3,colors.grey),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ALIGN",(0,0),(0,-1),"CENTER"),
        ("BACKGROUND",(0,0),(-1,0),colors.whitesmoke),
    ]))
    story.append(media_tbl)

    footer_address = data.get("footer_address", "")
    # Prepare logo reader once and reuse in both callbacks
    logo_reader, logo_w, logo_h = (None, 0, 0)
    if data.get("logo_bytes"):
        try:
            logo_reader, logo_w, logo_h = _make_logo_reader(data["logo_bytes"], target_width=1.6*inch)
        except Exception:
            logo_reader = None

    # Build with header logo + centered footer on every page
    def _first_page(c, d):
        _draw_logo(c, d, logo_reader, logo_w, logo_h)
        _draw_footer(c, d, footer_address)

    def _later_pages(c, d):
        _draw_logo(c, d, logo_reader, logo_w, logo_h)
        _draw_footer(c, d, footer_address)

    doc.build(story, onFirstPage=_first_page, onLaterPages=_later_pages)

    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
