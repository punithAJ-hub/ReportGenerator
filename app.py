import streamlit as st
import datetime
import uuid
from excel_parser import parse_excel, build_maps
from pdf_generator import generate_pdf

st.set_page_config(page_title="Field Report Builder", layout="wide")

# ===================== Constants =====================
OBS_TEMPLATE = (
    "The purpose of this site visit was to observe and review the _____, and to determine whether "
    "the work of the contractor was in general conformance with the structural construction documents. "
    "See Figure 1.00 for the overview of the construction site. During the observation visit, the ________ "
    "highlighted in figure 1.01 were observed. Typical _______ reinforcement were provided in conformance "
    "with structural drawings. _______ excavation and reinforcing work for several ______ were still ongoing "
    "at the time of visit. Overall construction matched the requirements of structural drawings in the observed "
    "area except as listed below:"
)

REMARKS_DEFAULT = (
    "The contractor was informed of the above-mentioned discrepancies in the field. "
    "All discrepancies shall be fixed, and all debris shall be cleaned out of grade beam trenches "
    "prior to concrete placement. See the following pages for photographs."
)

PRESENT_OPTIONS = ["Havish", "John", "Cena"]
SCOPE_OPTIONS = ["Grade Beam", "SOG", "Steel Framing"]

# ===================== Helpers =====================
def _new_media():
    return {"id": str(uuid.uuid4()), "file": None, "description": "", "include": False}

def _ensure_media_ids():
    for m in st.session_state["media_items"]:
        if "id" not in m or not m["id"]:
            m["id"] = str(uuid.uuid4())

def _delete_media_by_id(item_id: str):
    if not item_id:
        return
    st.session_state["media_items"] = [m for m in st.session_state["media_items"] if m.get("id") != item_id]
    if not st.session_state["media_items"]:
        st.session_state["media_items"] = [_new_media()]
    # Clean widget keys tied to this media row
    for k in list(st.session_state.keys()):
        if k.endswith(f"_{item_id}") or k == f"remove_media_{item_id}":
            del st.session_state[k]

def _new_obs_item(text: str = ""):
    return {"id": str(uuid.uuid4()), "text": text}

def _ensure_obs_items_struct():
    # Initialize modern structure if missing or migrate old list if present
    if "observation_items" not in st.session_state:
        legacy = st.session_state.get("observation_items_list")
        if isinstance(legacy, list):
            st.session_state["observation_items"] = [_new_obs_item(t) for t in legacy]
        else:
            st.session_state["observation_items"] = [_new_obs_item("")]
    # Ensure every item has id & text
    for it in st.session_state["observation_items"]:
        if "id" not in it or not it["id"]:
            it["id"] = str(uuid.uuid4())
        if "text" not in it:
            it["text"] = ""

def _delete_obs_by_id(oid: str):
    if not oid:
        return
    st.session_state["observation_items"] = [it for it in st.session_state["observation_items"] if it["id"] != oid]
    if not st.session_state["observation_items"]:
        st.session_state["observation_items"] = [_new_obs_item("")]
    # Clean widget keys for that row
    for k in list(st.session_state.keys()):
        if k in (f"del_obs_{oid}",) or k.endswith(f"_{oid}"):
            del st.session_state[k]

def _fill_scope_placeholders(text: str, scope: str) -> str:
    """Replace all underscore groups (_____ etc.) with the chosen scope."""
    # We simply replace every run of underscores with the scope text.
    # (Keeps it simple and predictable per your request)
    import re
    return re.sub(r"_{2,}", scope, text)

# ===================== Session State =====================
def ensure_state():
    ss = st.session_state
    ss.setdefault("excel_df", None)
    ss.setdefault("id_title_map", {})
    ss.setdefault("id_client_map", {})
    ss.setdefault("project_number", "")
    ss.setdefault("title_display", "")
    ss.setdefault("client_display", "")
    ss.setdefault("_last_project_number", None)
    ss.setdefault("project_address", "")
    ss.setdefault("date_visited_date", datetime.date.today())
    ss.setdefault("dor_date", datetime.date.today())
    ss.setdefault("weather", "")
    ss.setdefault("present_multi", [])
    ss.setdefault("scope_selected", SCOPE_OPTIONS[0])  # single select scope
    ss.setdefault("observations", _fill_scope_placeholders(OBS_TEMPLATE, ss["scope_selected"]))
    ss.setdefault("remarks", REMARKS_DEFAULT)
    ss.setdefault("prepared_by", "John")
    ss.setdefault("media_items", [_new_media()])
    ss.setdefault("_do_clear", False)
    ss.setdefault("_remove_media_id", "")

def perform_clear_if_needed():
    ss = st.session_state
    if not ss.get("_do_clear"):
        return
    # Keep: project_number, title_display, client_display, scope_selected
    ss["project_address"] = ""
    ss["date_visited_date"] = datetime.date.today()
    ss["dor_date"] = datetime.date.today()
    ss["weather"] = ""
    ss["present_multi"] = []
    ss["observations"] = _fill_scope_placeholders(OBS_TEMPLATE, ss["scope_selected"])
    ss["remarks"] = REMARKS_DEFAULT
    ss["prepared_by"] = "John"
    ss["media_items"] = [_new_media()]
    ss["observation_items"] = [_new_obs_item("")]
    # Drop transient widget keys
    for k in list(ss.keys()):
        if k.startswith(("obs_item_", "media_file_", "media_desc_", "media_include_", "remove_media_")):
            del ss[k]
    ss["_do_clear"] = False

def perform_delete_if_needed():
    item_id = st.session_state.get("_remove_media_id", "")
    if item_id:
        _delete_media_by_id(item_id)
        st.session_state["_remove_media_id"] = ""

# ===================== App Start =====================
ensure_state()

# ---- Sidebar: Excel Upload ----
st.sidebar.header("Upload Excel (.xlsx)")
st.sidebar.caption("Required: **MSE ID**, **Title**. Optional: **Client** (or **Client Name**).")
xlsx_file = st.sidebar.file_uploader("Upload (XLSX)", type=["xlsx"])
if xlsx_file is not None:
    try:
        df = parse_excel(xlsx_file.read())
        title_map, client_map = build_maps(df)
        st.session_state["excel_df"] = df
        st.session_state["id_title_map"] = title_map
        st.session_state["id_client_map"] = client_map
        st.sidebar.success(f"Loaded {len(df)} projects.")
    except Exception as e:
        st.sidebar.error(f"Failed to read Excel: {e}")

st.title("Field Report Builder")

if st.session_state["excel_df"] is None:
    st.info("Please upload an Excel file with columns **MSE ID**, **Title**, and optionally **Client**.")
    st.stop()

# ---- Deferred actions BEFORE rendering any widgets ----
perform_clear_if_needed()
perform_delete_if_needed()
_ensure_media_ids()
_ensure_obs_items_struct()

# ---- ID → Title/Client mapping ----
id_title_map = st.session_state["id_title_map"]
id_client_map = st.session_state["id_client_map"]
id_options = list(id_title_map.keys()) or ["—"]

# ===================== Form Fields (2 per row) =====================
# Row 1: Project Number | Project Name (editable)
c1, c2 = st.columns(2)
with c1:
    st.selectbox("Project Number (MSE ID)", id_options, index=0, key="project_number")

computed_title = id_title_map.get(st.session_state["project_number"], "")
computed_client = id_client_map.get(st.session_state["project_number"], "")
if st.session_state.get("_last_project_number") != st.session_state["project_number"]:
    st.session_state["title_display"] = computed_title
    st.session_state["client_display"] = computed_client
    st.session_state["_last_project_number"] = st.session_state["project_number"]

with c2:
    st.text_input("Project Name (Title)", key="title_display", placeholder="Project Title")

# Row 2: Address | Client (editable)
c1, c2 = st.columns(2)
with c1:
    st.text_area("Project Address", key="project_address", height=80, placeholder="Street, City, State ZIP")
with c2:
    st.text_input("Client Name", key="client_display", placeholder="Client Name")

# Row 3: Date Visited | Date of Report
c1, c2 = st.columns(2)
with c1:
    st.date_input("Date Visited", key="date_visited_date")
with c2:
    st.date_input("Date of Report", key="dor_date")

# Row 4: Weather | Present
c1, c2 = st.columns(2)
with c1:
    st.text_input("Weather", key="weather", placeholder="e.g., Sunny, 75°F")
with c2:
    st.multiselect("Present", PRESENT_OPTIONS, key="present_multi")

# Row 5: Scope of Work (single select) | (blank)
c1, c2 = st.columns(2)
with c1:
    # Single, authoritative Scope of Work control
    st.selectbox("Scope of Work", SCOPE_OPTIONS, key="scope_selected")
with c2:
    st.markdown("&nbsp;")

# Update observations text from scope if user hasn't edited it since last autogen
# (Light-touch approach: always regenerate from template on scope change; user can still edit after)
st.session_state["observations"] = _fill_scope_placeholders(OBS_TEMPLATE, st.session_state["scope_selected"])

# Row 6: Observations | Observation Items (with stable IDs & clean UI)
c1, c2 = st.columns(2)
with c1:
    st.text_area(
        "Observations",
        key="observations",
        height=180,
        placeholder="Enter or edit the observations paragraph…"
    )

with c2:
    st.write("Observation Items")
    to_delete_id = None
    for it in st.session_state["observation_items"]:
        oid = it["id"]
        col_text, col_btn = st.columns([9, 1])
        with col_text:
            st.text_input(
                label="",
                key=f"obs_item_{oid}",
                value=it["text"],
                placeholder="Enter observation detail…",
                label_visibility="collapsed",
            )
            it["text"] = st.session_state.get(f"obs_item_{oid}", "")
        with col_btn:
            if st.button("🗑️", key=f"del_obs_{oid}", help="Delete this observation item"):
                to_delete_id = oid

    if to_delete_id:
        _delete_obs_by_id(to_delete_id)
        st.rerun()

# Add button to append a new empty item
if st.button("➕ Add another observation item"):
    st.session_state["observation_items"].append(_new_obs_item(""))
    st.rerun()

# Row 7: Remarks | Prepared By
c1, c2 = st.columns(2)
with c1:
    st.text_area("Remarks", key="remarks", height=100)
with c2:
    st.selectbox("Prepared By", ["Havish", "John", "Messi"], key="prepared_by")

st.markdown("---")
st.subheader("Media")

# ===================== Media (stable IDs) =====================
# app.py

# Media section (stable IDs)
for m in st.session_state["media_items"]:
    item_id = m["id"]

    # Create a two-column layout: one for image upload and description, and one for the checkbox
    col1, col2 = st.columns([2, 1])  # Adjusted the width ratio for better space distribution

    # Column 1: Image Upload and Description
    with col1:
        st.file_uploader(
            "Image",
            type=["png", "jpg", "jpeg", "heic", "heif"],
            key=f"media_file_{item_id}",
            label_visibility="visible",
        )
        st.text_area("Description", key=f"media_desc_{item_id}", height=100)

    # Column 2: Checkbox to Add to Observations
    with col2:
        include_key = f"media_include_{item_id}"
        if include_key not in st.session_state:
            st.session_state[include_key] = bool(m.get("include", False))
        st.checkbox("Add to Observations", key=include_key)

        # Sync back into item dict
        m["file"] = st.session_state.get(f"media_file_{item_id}")
        m["description"] = st.session_state.get(f"media_desc_{item_id}", "")
        m["include"] = bool(st.session_state.get(include_key, False))

    # Create a new row for the delete button, ensuring proper alignment below the checkbox
    delete_col = st.columns([3])[0]  # Single-column layout for the delete button
    with delete_col:
        if st.button("🗑️ Remove media", key=f"remove_media_{item_id}", help="Remove this media item"):
            st.session_state["_remove_media_id"] = item_id
            st.rerun()

    st.markdown("---")  # Separate the sections with a line for clarity

# Add new media row
if st.button("➕ Add more media"):
    st.session_state["media_items"].append(_new_media())
    st.rerun()

# ===================== Actions =====================
st.markdown("## ")
btn_col1, btn_col2 = st.columns([1, 1])
with btn_col1:
    generate_clicked = st.button("📄 Generate PDF Report")
with btn_col2:
    if st.button("🧹 Clear Form"):
        st.session_state["_do_clear"] = True
        st.rerun()

# ===================== Generate PDF =====================
if generate_clicked:
    date_visited = st.session_state["date_visited_date"]
    date_of_report = st.session_state["dor_date"]

    # Build media struct
    media_struct = []
    for m in st.session_state["media_items"]:
        f = m.get("file")
        desc = m.get("description", "")
        include = bool(m.get("include", False))
        try:
            file_bytes = f.read() if f is not None else None
        except Exception:
            file_bytes = None
        media_struct.append({
            "image_bytes": file_bytes,
            "description": desc,
            "include_in_obs": include
        })

    payload = {
        "project_number": st.session_state["project_number"],
        "title": st.session_state["title_display"],
        "project_address": st.session_state["project_address"],
        "client_name": st.session_state["client_display"],
        "date_visited": date_visited,
        "date_of_report": date_of_report,
        "weather": st.session_state["weather"],
        "present": st.session_state["present_multi"],
        "scope_of_work": st.session_state["scope_selected"],
        "observations": st.session_state["observations"],
        "observation_items": [it["text"] for it in st.session_state["observation_items"] if it["text"].strip()],
        "remarks": st.session_state["remarks"],
        "prepared_by": st.session_state["prepared_by"],
        "media": media_struct,
        "footer_address": "5177 RICHMOND AVENUE, SUITE 670, HOUSTON, TEXAS 77056",
    }

    # Optional logo
    try:
        with open("Logo.jpg", "rb") as logo_file:
            payload["logo_bytes"] = logo_file.read()
    except Exception:
        st.warning("Logo.jpg not found — continuing without logo.")

    try:
        pdf_bytes = generate_pdf(payload)
        filename = f"{payload['project_number']}_{payload['title']}_Field_Report.pdf".replace(" ", "_")
        st.success("PDF generated successfully.")
        st.download_button("⬇️ Download Field Report", data=pdf_bytes, file_name=filename, mime="application/pdf")
    except Exception as e:
        st.error(f"Failed to generate PDF: {e}")

st.caption("Tip: For HEIC/HEIF images, install `pillow-heif` to improve support (already handled if available).")
