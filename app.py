# app.py
import streamlit as st
import datetime
from excel_parser import parse_excel, build_id_title_map
from pdf_generator import generate_pdf

st.set_page_config(page_title="Field Report Builder", layout="wide")

# ---------- Session State ----------
def ensure_state():
    ss = st.session_state
    ss.setdefault("excel_df", None)
    ss.setdefault("id_title_map", {})
    ss.setdefault("project_number", "")
    ss.setdefault("title_display", "")
    ss.setdefault("project_address", "")
    ss.setdefault("client_name", "")
    ss.setdefault("date_visited_date", datetime.date.today())
    ss.setdefault("date_visited_time", datetime.datetime.now().time().replace(second=0, microsecond=0))
    now = datetime.datetime.now()
    ss.setdefault("dor_date", now.date())
    ss.setdefault("dor_time", now.time().replace(second=0, microsecond=0))
    ss.setdefault("weather", "")
    ss.setdefault("present_list", [""])                 # <- init
    ss.setdefault("observations", "")
    ss.setdefault("observation_items_list", [""])       # <- init
    ss.setdefault("remarks", "")
    ss.setdefault("prepared_by", "John")
    ss.setdefault("scope_of_work", [])
    ss.setdefault("media_items", [{"file": None, "description": ""}])  # <- init
    ss.setdefault("_do_clear", False)

def perform_clear_if_needed():
    ss = st.session_state
    if not ss.get("_do_clear"):
        return
    # keep: excel_df, id_title_map, project_number, title_display
    ss["project_address"] = ""
    ss["client_name"] = ""
    ss["date_visited_date"] = datetime.date.today()
    ss["date_visited_time"] = datetime.datetime.now().time().replace(second=0, microsecond=0)
    ss["dor_date"] = datetime.date.today()
    ss["dor_time"] = datetime.datetime.now().time().replace(second=0, microsecond=0)
    ss["weather"] = ""
    ss["present_list"] = [""]
    ss["observations"] = ""
    ss["observation_items_list"] = [""]
    ss["remarks"] = ""
    ss["prepared_by"] = "John"
    ss["scope_of_work"] = []
    ss["media_items"] = [{"file": None, "description": ""}]
    for k in list(ss.keys()):
        if k.startswith(("present_", "obs_item_", "media_file_", "media_desc_", "remove_media_", "rm_")):
            del ss[k]
    ss["_do_clear"] = False

ensure_state()

# ---------- Sidebar ----------
st.sidebar.header("Upload Excel (.xlsx)")
xlsx_file = st.sidebar.file_uploader("Upload (columns: 'MSE ID', 'Title')", type=["xlsx"])
if xlsx_file is not None:
    try:
        df = parse_excel(xlsx_file.read())
        st.session_state["excel_df"] = df
        st.session_state["id_title_map"] = build_id_title_map(df)
        st.sidebar.success(f"Loaded {len(df)} projects.")
    except Exception as e:
        st.sidebar.error(f"Failed to read Excel: {e}")

st.title("Field Report Builder")

if st.session_state["excel_df"] is None:
    st.info("Please upload an Excel file with columns **MSE ID** and **Title**.")
    st.stop()

# IMPORTANT: do any clearing BEFORE widgets render
perform_clear_if_needed()

# ---------- Two fields per row ----------
id_title_map = st.session_state["id_title_map"]
id_options = list(id_title_map.keys()) or ["—"]

# Row 1: Project Number | Project Name
c1, c2 = st.columns(2)
with c1:
    st.selectbox("Project Number (MSE ID)", id_options, index=0, key="project_number")

computed_title = id_title_map.get(st.session_state["project_number"], "")
if st.session_state.get("title_display") != computed_title:
    st.session_state["title_display"] = computed_title

with c2:
    st.text_input("Project Name (Title)", key="title_display", disabled=True)

# Row 2: Address | Client
c1, c2 = st.columns(2)
with c1:
    st.text_area("Project Address", key="project_address", height=80)
with c2:
    st.text_input("Client Name", key="client_name")

# Row 3: Dates
c1, c2 = st.columns(2)
with c1:
    st.date_input("Date Visited (Date)", key="date_visited_date")
    st.time_input("Date Visited (Time)", key="date_visited_time")
with c2:
    st.date_input("Date of Report (Date)", key="dor_date")
    st.time_input("Date of Report (Time)", key="dor_time")

# Row 4: Weather | Present
c1, c2 = st.columns(2)
with c1:
    st.text_input("Weather", key="weather", placeholder="e.g., Sunny, 75°F")
with c2:
    st.write("Present")
    # --- Robust default to avoid KeyError on reruns
    present_list = st.session_state.setdefault("present_list", [""])
    for i in range(len(present_list)):
        st.text_input(
            label=f"Present {i+1}",
            key=f"present_{i}",
            value=present_list[i],
            placeholder="Name, Company",
            label_visibility="collapsed" if i > 0 else "visible"
        )
        st.session_state["present_list"][i] = st.session_state.get(f"present_{i}", "")

if st.button("➕ Add another present"):
    st.session_state.setdefault("present_list", [""]).append("")
if len(st.session_state.setdefault("present_list", [""])) > 1:
    r1, r2, _ = st.columns([1,1,6])
    with r1:
        st.number_input("Remove present #", 1, len(st.session_state["present_list"]), 1, key="rm_present_idx")
    with r2:
        if st.button("🗑️ Remove selected present"):
            idx = st.session_state["rm_present_idx"] - 1
            if 0 <= idx < len(st.session_state["present_list"]):
                st.session_state["present_list"].pop(idx)

# Row 5: Observations | Observation Items
c1, c2 = st.columns(2)
with c1:
    st.text_area("Observations (optional extra notes)", key="observations", height=140)
with c2:
    st.write("Observation Items")
    obs_items = st.session_state.setdefault("observation_items_list", [""])
    for i in range(len(obs_items)):
        st.text_input(
            label=f"Observation Item {i+1}",
            key=f"obs_item_{i}",
            value=obs_items[i],
            placeholder="e.g., Provide additional stirrup…",
            label_visibility="collapsed" if i > 0 else "visible"
        )
        st.session_state["observation_items_list"][i] = st.session_state.get(f"obs_item_{i}", "")

if st.button("➕ Add another observation item"):
    st.session_state.setdefault("observation_items_list", [""]).append("")
if len(st.session_state.setdefault("observation_items_list", [""])) > 1:
    r1, r2, _ = st.columns([1,1,6])
    with r1:
        st.number_input("Remove item #", 1, len(st.session_state["observation_items_list"]), 1, key="rm_obs_idx")
    with r2:
        if st.button("🗑️ Remove selected item"):
            idx = st.session_state["rm_obs_idx"] - 1
            if 0 <= idx < len(st.session_state["observation_items_list"]):
                st.session_state["observation_items_list"].pop(idx)

# Row 6: Remarks
c1, c2 = st.columns(2)
with c1:
    st.text_area("Remarks", key="remarks", height=100)
with c2:
    st.markdown("&nbsp;")

# Row 7: Prepared By | Scope
c1, c2 = st.columns(2)
with c1:
    st.selectbox("Prepared By", ["Havish", "John", "Messi"], key="prepared_by")
with c2:
    st.multiselect("Scope of Work", ["Grade Beam", "SOG", "Steel Framing"], key="scope_of_work")

st.markdown("---")
st.subheader("Media")
st.caption("Each row = Image + Description. This description becomes Figure text and the numbered list in Observations.")

# --- Robust default to avoid KeyError on reruns
st.session_state.setdefault("media_items", [{"file": None, "description": ""}])

to_delete = []
for i, item in enumerate(st.session_state["media_items"]):
    mc1, mc2 = st.columns(2)
    with mc1:
        st.file_uploader(f"Image {i+1}", type=["png", "jpg", "jpeg", "heic"], key=f"media_file_{i}")
    with mc2:
        st.text_area(f"Description {i+1}", key=f"media_desc_{i}", height=100)

    st.session_state["media_items"][i]["file"] = st.session_state.get(f"media_file_{i}")
    st.session_state["media_items"][i]["description"] = st.session_state.get(f"media_desc_{i}", "")

    rm_col = st.columns([1,9])[0]
    with rm_col:
        if st.button(f"🗑️ Remove media {i+1}", key=f"remove_media_{i}"):
            if len(st.session_state["media_items"]) > 1:
                to_delete.append(i)
    st.markdown("---")

if to_delete:
    st.session_state["media_items"] = [m for j, m in enumerate(st.session_state["media_items"]) if j not in to_delete]

if st.button("➕ Add more media"):
    st.session_state.setdefault("media_items", [{"file": None, "description": ""}]).append({"file": None, "description": ""})

# ---------- Action Buttons ----------
st.markdown("## ")
btn_col1, btn_col2 = st.columns([1,1])
with btn_col1:
    generate_clicked = st.button("📄 Generate PDF Report")
with btn_col2:
    if st.button("🧹 Clear Form (keep Project ID & Name)"):
        st.session_state["_do_clear"] = True
        st.rerun()

# ---------- Generate PDF ----------
if generate_clicked:
    try:
        date_visited = datetime.datetime.combine(st.session_state["date_visited_date"], st.session_state["date_visited_time"])
    except Exception:
        date_visited = datetime.datetime.now()
    try:
        date_of_report = datetime.datetime.combine(st.session_state["dor_date"], st.session_state["dor_time"])
    except Exception:
        date_of_report = datetime.datetime.now()

    present = [p.strip() for p in st.session_state.setdefault("present_list", [""]) if p and p.strip()]
    obs_items = [o.strip() for o in st.session_state.setdefault("observation_items_list", [""]) if o and o.strip()]

    media_struct = []
    for item in st.session_state.setdefault("media_items", [{"file": None, "description": ""}]):
        f = item.get("file")
        desc = item.get("description", "")
        try:
            file_bytes = f.read() if f is not None else None
        except Exception:
            file_bytes = None
        media_struct.append({"image_bytes": file_bytes, "description": desc})

    payload = {
        "project_number": st.session_state["project_number"],
        "title": st.session_state["title_display"],
        "project_address": st.session_state["project_address"],
        "client_name": st.session_state["client_name"],
        "date_visited": date_visited,
        "date_of_report": date_of_report,
        "weather": st.session_state["weather"],
        "present": present,
        "observations": st.session_state["observations"],
        "observation_items": obs_items,
        "remarks": st.session_state["remarks"],
        "prepared_by": st.session_state["prepared_by"],
        "scope_of_work": st.session_state["scope_of_work"],
        "media": media_struct,
        "footer_address": "5177 RICHMOND AVENUE, SUITE 670, HOUSTON, TEXAS 77056",
    }

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
