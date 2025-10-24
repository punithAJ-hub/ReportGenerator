from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas
from io import BytesIO
from PIL import Image as PILImage
import datetime

# Enable HEIC/HEIF if present (optional)
try:
    import pillow_heif  # type: ignore
    pillow_heif.register_heif_opener()
except Exception:
    pass

# ---- Layout constants ----
PHOTO_W = 2.9 * inch
PHOTO_H = 2.1 * inch
LOGO_TARGET_W = 1.6 * inch
LOGO_PAD = 0.12 * inch  # tight gap to the top-right page edges

BRAND_BLUE = colors.Color(0/255, 85/255, 153/255)  # #005599
DISCLAIMER = (
    "THE VISUAL FIELD OBSERVATIONS BY THE STRUCTURAL ENGINEER SHALL NOT BE CONSTRUED AS A CONTINUOUS OR "
    "EXHAUSTIVE PROJECT REVIEW. THESE OBSERVATIONS ARE NOT A WAIVER OF THE GENERAL CONTRACTOR (OR ANY ENTITY "
    "FURNISHING MATERIALS OR PERFORMING WORK ON THE PROJECT) FROM RESPONSIBILITY AND/OR PERFORMANCE IN "
    "ACCORDANCE WITH THE REQUIREMENTS OF THE CONTRACT DOCUMENTS AND SPECIFICATIONS."
)

def _fmt_dt(dt, with_time=False):
    if not dt:
        return ""
    if isinstance(dt, (datetime.datetime, datetime.date)):
        if with_time and isinstance(dt, datetime.datetime):
            return dt.strftime("%m/%d/%Y %I:%M %p")
        return dt.strftime("%m/%d/%Y")
    return str(dt)

def _scaled_dims(orig_w, orig_h, max_w, max_h):
    scale = min(float(max_w) / float(orig_w), float(max_h) / float(orig_h))
    return (orig_w * scale, orig_h * scale)

def _img_from_bytes(img_bytes, max_w=PHOTO_W, max_h=PHOTO_H):
    """
    Return a ReportLab Image using the ORIGINAL bytes (no re-encode) for best quality,
    scaled to fit inside (max_w x max_h). If reader fails, fallback to single JPEG encode.
    """
    if not img_bytes:
        return None
    try:
        pil = PILImage.open(BytesIO(img_bytes))
        w, h = pil.size
        new_w, new_h = _scaled_dims(w, h, max_w, max_h)

        # Prefer original bytes to avoid recompression blur
        try:
            rdr = ImageReader(BytesIO(img_bytes))
            return RLImage(rdr, width=new_w, height=new_h)
        except Exception:
            out = BytesIO()
            pil.convert("RGB").save(out, format="JPEG", quality=95)
            out.seek(0)
            return RLImage(out, width=new_w, height=new_h)
    except Exception:
        return None

def _make_logo_reader(logo_bytes, target_width=LOGO_TARGET_W):
    if not logo_bytes:
        return None, 0, 0
    pil = PILImage.open(BytesIO(logo_bytes))
    w, h = pil.size
    scale = float(target_width) / float(w)
    new_w, new_h = target_width, h * scale
    bio = BytesIO()
    pil.save(bio, format="PNG")  # keep clarity
    bio.seek(0)
    return ImageReader(bio), new_w, new_h

def _draw_footer(canvas: Canvas, doc, footer_address: str):
    canvas.saveState()
    width, height = LETTER
    footer_style = ParagraphStyle(
        name="FooterSmall", fontName="Helvetica", fontSize=7, leading=9,
        textColor=BRAND_BLUE, alignment=TA_CENTER
    )
    address_style = ParagraphStyle(
        name="FooterAddress", fontName="Helvetica-Bold", fontSize=10, leading=12,
        textColor=BRAND_BLUE, alignment=TA_CENTER
    )

    disclaimer_para = Paragraph(DISCLAIMER, footer_style)
    avail_width = doc.width
    base_y = 8
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
    """Place logo at the page top-right corner with a tiny padding on every page."""
    if not logo_reader:
        return
    page_w, page_h = LETTER
    x = page_w - LOGO_PAD - logo_w
    y = page_h - LOGO_PAD - logo_h
    canvas.drawImage(logo_reader, x, y, width=logo_w, height=logo_h, mask='auto')

def generate_pdf(data: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch,
        topMargin=0.9*inch,   # normal frame margin; logo sits in page margin
        bottomMargin=1.15*inch,
        title=f"{data.get('project_number','')}_{data.get('title','')}_Field_Report",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleMain", fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=8))
    styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10, leading=14))
    styles.add(ParagraphStyle(name="ObsPara", fontName="Helvetica", fontSize=10, leading=14, alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name="ObsItem", fontName="Helvetica", fontSize=10, leading=14, alignment=TA_JUSTIFY))
    styles.add(ParagraphStyle(name="Sig", fontName="Helvetica-Bold", fontSize=11, leading=15, spaceBefore=8))

    story = []
    story.append(Paragraph("F I E L D  R E P O R T", styles["TitleMain"]))
    story.append(Spacer(1, 6))

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

    # ------ Scope of Work (before Observations) ------
    scope_text = str(data.get("scope_of_work", "") or "")
    rows.append([Paragraph(f"{bullet}  <b>Scope of Work:</b>", styles["Body"]), Paragraph(scope_text, styles["Body"])])

    # ------ Observations ------
    obs_text = (data.get("observations") or "").strip()
    if not obs_text:
        obs_text = ""
    obs_cells = [Paragraph(obs_text.replace("\n", "<br/>"), styles["ObsPara"])]

    # Append numbered items: first observation items, then included media descriptions with figure number
    count = 0
    observation_items = [it.strip() for it in (data.get("observation_items") or []) if it and it.strip()]
    for it in observation_items:
        count += 1
        obs_cells.append(Paragraph(f"{count}. {it}", styles["ObsItem"]))

    media = data.get("media") or []
    for idx, m in enumerate(media, start=1):
        desc = (m.get("description") or "").strip()
        include = bool(m.get("include_in_obs", False))
        if desc and include:
            count += 1
            obs_cells.append(Paragraph(f"{count}. {desc} (Figure {idx})", styles["ObsItem"]))

    obs_tbl = Table([[obs_cells]], colWidths=[5.3*inch])
    obs_tbl.setStyle(TableStyle([
        ("LEFTPADDING",(0,0),(-1,-1),0),
        ("RIGHTPADDING",(0,0),(-1,-1),0),
        ("TOPPADDING",(0,0),(-1,-1),0),
        ("BOTTOMPADDING",(0,0),(-1,-1),0),
    ]))
    rows.append([Paragraph(f"{bullet}  <b>Observations:</b>", styles["Body"]), obs_tbl])

    # Remarks
    rows.append([
        Paragraph(f"{bullet}  <b>Remarks:</b>", styles["Body"]),
        Paragraph(str(data.get("remarks","")), styles["Body"])
    ])

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

    # ------ Media page ------
    story.append(PageBreak())
    tbl_data = [[Paragraph("<b>Item Number</b>", styles["Body"]),
                 Paragraph("<b>Photo</b>", styles["Body"]),
                 Paragraph("<b>Comment/Action</b>", styles["Body"])]]

    for idx, item in enumerate(media, start=1):
        rl_img = _img_from_bytes(item.get("image_bytes"), max_w=PHOTO_W, max_h=PHOTO_H)
        photo_cell = rl_img if rl_img is not None else Paragraph("—", styles["Body"])
        desc = Paragraph((item.get("description") or "").replace("\n","<br/>"), styles["Body"])
        tbl_data.append([Paragraph(f"Figure {idx}", styles["Body"]), photo_cell, desc])

    media_tbl = Table(tbl_data, colWidths=[1.1*inch, PHOTO_W, 3.4*inch], repeatRows=1)
    media_tbl.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.3,colors.grey),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("ALIGN",(0,0),(0,-1),"CENTER"),
        ("BACKGROUND",(0,0),(-1,0),colors.whitesmoke),
    ]))
    story.append(media_tbl)

    footer_address = data.get("footer_address", "")

    # Logo on all pages (absolute top-right in page margin)
    logo_reader, logo_w, logo_h = (None, 0, 0)
    if data.get("logo_bytes"):
        try:
            logo_reader, logo_w, logo_h = _make_logo_reader(data["logo_bytes"], target_width=LOGO_TARGET_W)
        except Exception:
            logo_reader = None

    def _first_page(c, d):
        if logo_reader:
            _draw_logo(c, d, logo_reader, logo_w, logo_h)
        _draw_footer(c, d, footer_address)

    def _later_pages(c, d):
        if logo_reader:
            _draw_logo(c, d, logo_reader, logo_w, logo_h)
        _draw_footer(c, d, footer_address)

    doc.build(story, onFirstPage=_first_page, onLaterPages=_later_pages)

    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
