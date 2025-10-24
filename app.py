# app.py
import streamlit as st
import datetime
import uuid
from excel_parser import parse_excel, build_maps
from pdf_generator import generate_pdf

st.set_page_config(page_title="Field Report Builder", layout="wide")

# ---------- Constants ----------
OBSERVATIONS_DEFAULT = (
    "The purpose of this site visit was to observe and review the _____, and to determine whether "
    "the work of the contractor was in general conformance with the structural construction documents. "
    "See Figure 1.00 for the overview of the construction site. During the observation visit, the ________ "
    "highlighted in figure 1.01 were observed. Typical _______ reinforcement were provided in conformance "
    "with structural drawings. _______ excavation and reinforcing work for several ______ were still ongoing "
    "at the time of visit. Overall construction matched the requirements of structural drawings in the observed area except as listed below:"
)
REMARKS_DEFAULT = (
    "The contractor was informed of the above-mentioned discrepancies in the field. "
    "All discrepancies shall be fixed, and all debris shall be cleaned out of grade beam "
    "trenches prior to concrete placement. See the following pages for photographs."
)
PRESENT_OPTIONS = ["Havish", "John", "Cena"]
SCOPE_OPTIONS = ["Grade Beam", "SOG", "Steel Framing"]  # Options for Scope of Work (only 1 scope used now)


# ---------- Session State ----------
def ensure_state():
    ss = st.session_state
    ss.setdefault("excel_df", None)
    ss.setdefault("id_title_map", {})
    ss.setdefault("id_client_map", {})
    ss.setdefault("project_number", "")
    ss.setdefault("title_display", "")
    ss.setdefault("client_display", "")
    ss.setdefault("_last_project_number", None)  # track changes to MSE ID
    ss.setdefault("project_address", "")
    ss.setdefault("date_visited_date", datetime.date.today())
    ss.setdefault("dor_date", datetime.date.today())
    ss.setdefault("weather", "")
    ss.setdefault("present_multi", [])
    ss.setdefault("observations", OBSERVATIONS_DEFAULT)
    ss.setdefault("observation_items_list", [""])
    ss.setdefault("remarks", REMARKS_DEFAULT)
    ss.setdefault("prepared_by", "John")
    ss.setdefault("scope_of_work", [])
    # media items with stable ids
    ss.setdefault("media_items", [{"id": str(uuid.uuid4()), "file": None, "description": "", "include": False}])
    ss.setdefault("_do_clear", False)
    ss.setdefault("_remove_media_id", "")


def perform_clear_if_needed():
    ss = st.session_state
    if not ss.get("_do_clear"):
        return
    # Keep: project_number, title_display, client_display (so edits persist)
    ss["project_address"] = ""
    ss["date_visited_date"] = datetime.date.today()
    ss["dor_date"] = datetime.date.today()
    ss["weather"] = ""
    ss["present_multi"] = []
    ss["observations"] = OBSERVATIONS_DEFAULT
    ss["observation_items_list"] = [""]
    ss["remarks"] = REMARKS_DEFAULT
    ss["prepared_by"] = "John"
    ss["scope_of_work"] = []
    ss["media_items"] = [{"id": str(uuid.uuid4()), "file": None, "description": "", "include": False}]
    # Drop transient keys
    for k in list(ss.keys()):
        if k.startswith(("obs_item_", "rm_", "media_file_", "media_desc_", "media_include_", "remove_media_")):
            del ss[k]
    ss["_do_clear"] = False


def perform_delete_if_needed():
    """If a delete request was set last run, apply it now (before rendering widgets)."""
    item_id = st.session_state.get("_remove_media_id", "")
    if item_id:
        _delete_media_by_id(item_id)
        st.session_state["_remove_media_id"] = ""


def _delete_media_by_id(item_id: str):
    """Delete media by stable id and cleanup widget keys."""
    if not item_id:
        return
    # Remove the item from the list
    st.session_state["media_items"] = [m for m in st.session_state["media_items"] if m.get("id") != item_id]

    # If no media items left, create a placeholder
    if not st.session_state["media_items"]:
        st.session_state["media_items"] = [{"id": str(uuid.uuid4()), "file": None, "description": "", "include": False}]

    # Remove widget keys for that specific media item
    for k in list(st.session_state.keys()):
        if k.endswith(f"_{item_id}") or k == f"remove_media_{item_id}":
            del st.session_state[k]


ensure_state()

# ---------- Sidebar: Upload ----------
st.sidebar.header("Upload Excel (.xlsx)")
st.sidebar.caption("Required: **MSE ID**, **Title**. Optional: **Client** or **Client Name**.")
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

# ---------- Perform deferred clear before drawing widgets ----------
perform_clear_if_needed()
perform_delete_if_needed()

# ---------- Ensure defaults for text areas if empty ----------
if not st.session_state.get("observations"):
    st.session_state["observations"] = OBSERVATIONS_DEFAULT
if not st.session_state.get("remarks"):
    st.session_state["remarks"] = REMARKS_DEFAULT

# ---------- Load maps ----------
id_title_map = st.session_state["id_title_map"]
id_client_map = st.session_state["id_client_map"]
id_options = list(id_title_map.keys()) or ["—"]

# ---------- Row 1: Project Number | Project Name (editable) ----------
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

# ---------- Row 2: Address | Client (editable) ----------
c1, c2 = st.columns(2)
with c1:
    st.text_area("Project Address", key="project_address", height=80, placeholder="Street, City, State ZIP")
with c2:
    st.text_input("Client Name", key="client_display", placeholder="Client Name")

# ---------- Row 3: Date Visited | Date of Report ----------
c1, c2 = st.columns(2)
with c1:
    st.date_input("Date Visited", key="date_visited_date")
with c2:
    st.date_input("Date of Report", key="dor_date")

# ---------- Row 4: Weather | Present ----------
c1, c2 = st.columns(2)
with c1:
    st.text_input("Weather", key="weather", placeholder="e.g., Sunny, 75°F")
with c2:
    st.multiselect("Present", PRESENT_OPTIONS, key="present_multi")

# ---------- Row 5: Scope of Work (editable) ----------
c1, c2 = st.columns(2)
with c1:
    # Use a unique key based on the project number
    st.selectbox("Scope of Work", SCOPE_OPTIONS, key=f"scope_of_work_{st.session_state['project_number']}", index=0)

# Update the Observations text dynamically based on selected Scope of Work
scope_selected = st.session_state[f"scope_of_work_{st.session_state['project_number']}"]
observations_text = OBSERVATIONS_DEFAULT.replace("_____",
                                                 f"{scope_selected}" if scope_selected else "Scope of Work")
st.session_state["observations"] = observations_text

# ---------- Row 6: Observations | Observation Items ----------
c1, c2 = st.columns(2)
with c1:
    st.text_area(
        "Observations",
        key="observations",
        height=180,
        placeholder="Enter or edit the observations paragraph shown on the first page…"
    )
with c2:
    st.write("Observation Items")
    obs_items = st.session_state.setdefault("observation_items_list", [""])

    # Inline delete per item
    to_delete = []
    for i in range(len(obs_items)):
        col_text, col_btn = st.columns([9, 1])
        with col_text:
            st.text_input(
                label=f"Observation Item {i + 1}",
                key=f"obs_item_{i}",
                value=obs_items[i],
                placeholder="e.g., Provide additional stirrup…",
                label_visibility="collapsed" if i > 0 else "visible",
            )
            st.session_state["observation_items_list"][i] = st.session_state.get(f"obs_item_{i}", "")
        with col_btn:
            if st.button("🗑️", key=f"del_obs_{i}", help="Delete this observation item"):
                to_delete.append(i)

    if to_delete:
        st.session_state["observation_items_list"] = [
                                                         v for idx, v in
                                                         enumerate(st.session_state["observation_items_list"]) if
                                                         idx not in to_delete
                                                     ] or [""]
        st.rerun()

# Add button to append a new empty item
if st.button("➕ Add another observation item"):
    st.session_state.setdefault("observation_items_list", [""]).append("")
    st.rerun()

# ---------- Row 7: Remarks ----------
c1, c2 = st.columns(2)
with c1:
    st.text_area("Remarks", key="remarks", height=100)
with c2:
    st.markdown("&nbsp;")

# ---------- Row 8: Prepared By ----------
c1, c2 = st.columns(2)
with c1:
    st.selectbox("Prepared By", ["Havish", "John", "Messi"], key="prepared_by")
with c2:
    st.markdown("&nbsp;")

st.markdown("---")
st.subheader("Media")
st.caption(
    "Each row = Image + Description. Tick **Add to Observations** to include that description as a numbered point under Observations.")

# ---------- Media list (with stable IDs) ----------
for m in st.session_state["media_items"]:
    item_id = m["id"]
    mc1, mc2 = st.columns(2)
    with mc1:
        st.file_uploader(
            f"Image",
            type=["png", "jpg", "jpeg", "heic"],
            key=f"media_file_{item_id}",
            label_visibility="visible",
        )
    with mc2:
        cap_left, cap_right = st.columns([8, 4])
        with cap_left:
            st.text_area(f"Description", key=f"media_desc_{item_id}", height=100)
        with cap_right:
            include_key = f"media_include_{item_id}"
            if include_key not in st.session_state:
                st.session_state[include_key] = bool(m.get("include", False))
            include_val = st.checkbox("Add to Observations", key=include_key)

        # Sync back to the item dict
        m["file"] = st.session_state.get(f"media_file_{item_id}")
        m["description"] = st.session_state.get(f"media_desc_{item_id}", "")
        m["include"] = bool(st.session_state.get(include_key, False))

    rm_col = st.columns([1, 9])[0]
    with rm_col:
        if st.button("🗑️ Remove media", key=f"remove_media_{item_id}"):
            st.session_state["_remove_media_id"] = item_id
            st.rerun()
    st.markdown("---")

# Add new media row
if st.button("➕ Add more media"):
    st.session_state["media_items"].append({"id": str(uuid.uuid4()), "file": None, "description": "", "include": False})
    st.rerun()

# ---------- Action Buttons ----------
st.markdown("## ")
btn_col1, btn_col2 = st.columns([1, 1])
with btn_col1:
    generate_clicked = st.button("📄 Generate PDF Report")
with btn_col2:
    if st.button("🧹 Clear Form (keep Project ID, Name & Client)"):
        st.session_state["_do_clear"] = True
        st.rerun()

# ---------- Generate PDF ----------
if generate_clicked:
    date_visited = st.session_state["date_visited_date"]
    date_of_report = st.session_state["dor_date"]

    # Build media list with bytes + include flag
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
        "title": st.session_state["title_display"],  # <-- uses editable field
        "project_address": st.session_state["project_address"],
        "client_name": st.session_state["client_display"],  # <-- uses editable field
        "date_visited": date_visited,
        "date_of_report": date_of_report,
        "weather": st.session_state["weather"],
        "present": st.session_state["present_multi"],
        "observations": st.session_state["observations"],
        "observation_items": [o for o in st.session_state["observation_items_list"] if o.strip()],
        "remarks": st.session_state["remarks"],
        "prepared_by": st.session_state["prepared_by"],
        "scope_of_work": st.session_state["scope_of_work"],
        "media": media_struct,
        "footer_address": "5177 RICHMOND AVENUE, SUITE 670, HOUSTON, TEXAS 77056",
    }

    # Add logo (all pages)
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
