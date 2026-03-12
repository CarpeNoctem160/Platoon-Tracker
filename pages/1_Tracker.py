import streamlit as st
import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import timezone # For UTC handling

# Google Sheets Setup (repeated for page independence, but could be modularized)
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SHEET_NAME = "PlatoonTrackerData"
sheet = client.open(SHEET_NAME).sheet1

# Helper functions (repeated)
def load_data():
    try:
        records = sheet.get_all_records()
        if not records:
            return {"personnel": [], "statuses": {}, "pfd": {}, "week_key": "", "platoon_map": {}}
        df = pd.DataFrame(records)
        data = {
            "personnel": json.loads(df.iloc[0]["personnel"]),
            "statuses": json.loads(df.iloc[0]["statuses"]),
            "pfd": json.loads(df.iloc[0]["pfd"]),
            "week_key": df.iloc[0]["week_key"],
            "platoon_map": json.loads(df.iloc[0].get("platoon_map", "{}"))
        }
        return data
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return {"personnel": [], "statuses": {}, "pfd": {}, "week_key": "", "platoon_map": {}}

def save_data(data):
    try:
        row = [
            json.dumps(data["personnel"]),
            json.dumps(data["statuses"]),
            json.dumps(data["pfd"]),
            data["week_key"],
            json.dumps(data["platoon_map"])
        ]
        sheet.clear()
        sheet.append_row(["personnel", "statuses", "pfd", "week_key", "platoon_map"])
        sheet.append_row(row)
    except Exception as e:
        st.error(f"Error saving data: {e}")

# Load data
data = load_data()

# UTC Date and week logic (Zulu time)
utc_now = datetime.datetime.now(timezone.utc)
today_utc = utc_now.date()
today_str = str(today_utc)

# Calculate start of current week (Sunday) in UTC
weekday = today_utc.weekday() # Monday=0, Sunday=6
days_to_sunday = (weekday + 1) % 7 # Days back to last Sunday
start_sunday = today_utc - datetime.timedelta(days=days_to_sunday)
current_week_key = str(start_sunday)

days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
options = ["", "PFD", "Flying", "Leave", "Pass", "School", "O/P", "Duty", "Recovery", "Appointment", "QTRS", "Range", "Exercise"]

# Status colors
STATUS_COLORS = {
    "": "#333333", # Default
    "PFD": "#92D050", # Assuming same as Flying, or adjust
    "Flying": "#92D050",
    "Leave": "#00B0F0",
    "Pass": "#7030A0",
    "School": "#00B050",
    "O/P": "#AEAAAA",
    "Duty": "#FFC000",
    "Recovery": "#FFFF00",
    "Appointment": "#FF00FF",
    "QTRS": "#F4B084",
    "Range": "#FF0000",
    "Exercise": "#C00000",
}

# Weekly reset if needed (at 00:00 UTC Saturday -> effectively rolls to new week Sunday)
if data.get("week_key", "") != current_week_key:
    data["week_key"] = current_week_key
    for name in data["personnel"]:
        data["statuses"][name] = {day: "" for day in days}
    save_data(data)

# Daily PFD reset (at 00:00 UTC)
for name in data.get("personnel", []):
    if name not in data["pfd"]:
        data["pfd"][name] = {"status": False, "last_date": today_str}
    if data["pfd"][name]["last_date"] != today_str:
        data["pfd"][name] = {"status": False, "last_date": today_str}
        save_data(data)

# Get selected platoon from session state
selected_platoon = st.session_state.get("selected_platoon", "All")

# Filter personnel
if selected_platoon != "All":
    filtered_personnel = [name for name in data["personnel"] if data["platoon_map"].get(name) == selected_platoon]
else:
    filtered_personnel = data["personnel"]

# Streamlit UI
st.title("Platoon Accountability Tracker")
st.set_page_config(layout="wide") # Better for mobile

# Add personnel with platoon selector
new_name = st.text_input("Add Personnel")
platoon_options = ["1st", "2nd"]
selected_platoon_add = st.selectbox("Platoon", platoon_options, key="add_platoon")
if st.button("Add") and new_name:
    if new_name not in data["personnel"]:
        data["personnel"].append(new_name)
        data["statuses"][new_name] = {day: "" for day in days}
        data["pfd"][new_name] = {"status": False, "last_date": today_str}
        data["platoon_map"][new_name] = selected_platoon_add
        save_data(data)
        st.rerun()

# Remove personnel
remove_name = st.selectbox("Remove Personnel", [""] + data["personnel"])
if st.button("Remove") and remove_name:
    data["personnel"].remove(remove_name)
    if remove_name in data["statuses"]:
        del data["statuses"][remove_name]
    if remove_name in data["pfd"]:
        del data["pfd"][remove_name]
    if remove_name in data["platoon_map"]:
        del data["platoon_map"][remove_name]
    save_data(data)
    st.rerun()

# Dashboard
st.subheader(f"Weekly Dashboard - {selected_platoon if selected_platoon != 'All' else 'Company'}")

if not filtered_personnel:
    st.write("No personnel added yet.")
else:
    # Header row with wider day columns
    header_cols = st.columns([1, 3] + [2] * 7) # Wider name (3) and days (2 each)
    header_cols[0].write("PFD (Today)")
    header_cols[1].write("Name")
    for i, day in enumerate(days):
        header_cols[i + 2].write(day)

    # Inject CSS for wider selectboxes and colors
    st.markdown("""
    <style>
        /* Widen selectboxes */
        div[data-baseweb="select"] {
            width: 150px !important; /* Adjust width as needed */
            min-width: 150px;
        }
        /* Optional: Make text wrap or ellipsis if too long */
        div[data-baseweb="select"] > div {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
    </style>
    """, unsafe_allow_html=True)

    # Data rows
    for name in filtered_personnel:
        row_cols = st.columns([1, 3] + [2] * 7) # Match header widths
        
        # PFD checkbox
        current_pfd = data["pfd"][name]["status"]
        new_pfd = row_cols[0].checkbox(
            "PFD today",
            value=current_pfd,
            key=f"pfd_{name}_{today_str}",
            label_visibility="hidden"
        )
        if new_pfd != current_pfd:
            data["pfd"][name]["status"] = new_pfd
            data["pfd"][name]["last_date"] = today_str
            save_data(data)
        
        # Name
        row_cols[1].write(name)
        
        # Day dropdowns with color
        for i, day in enumerate(days):
            current_status = data["statuses"][name].get(day, "")
            color = STATUS_COLORS.get(current_status, "#333333")
            # Use markdown to apply background color to the selectbox container
            row_cols[i + 2].markdown(
                f"<div style='background-color: {color}; padding: 5px; border-radius: 4px;'>",
                unsafe_allow_html=True
            )
            new_status = row_cols[i + 2].selectbox(
                f"Status for {day}",
                options,
                index=options.index(current_status),
                key=f"status_{name}_{day}_{current_week_key}",
                label_visibility="hidden"
            )
            row_cols[i + 2].markdown("</div>", unsafe_allow_html=True)
            if new_status != current_status:
                data["statuses"][name][day] = new_status
                save_data(data)