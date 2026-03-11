import streamlit as st
import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# Google Sheets Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Your Google Sheet name (match what you created)
SHEET_NAME = "PlatoonTrackerData"
sheet = client.open(SHEET_NAME).sheet1  # First worksheet

# Helper functions for data
def load_data():
    try:
        records = sheet.get_all_records()
        if not records:
            return {"personnel": [], "statuses": {}, "pfd": {}, "week_key": ""}
        df = pd.DataFrame(records)
        data = {
            "personnel": json.loads(df.iloc[0]["personnel"]),
            "statuses": json.loads(df.iloc[0]["statuses"]),
            "pfd": json.loads(df.iloc[0]["pfd"]),
            "week_key": df.iloc[0]["week_key"]
        }
        return data
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return {"personnel": [], "statuses": {}, "pfd": {}, "week_key": ""}

def save_data(data):
    try:
        row = [
            json.dumps(data["personnel"]),
            json.dumps(data["statuses"]),
            json.dumps(data["pfd"]),
            data["week_key"]
        ]
        sheet.clear()
        sheet.append_row(["personnel", "statuses", "pfd", "week_key"])
        sheet.append_row(row)
    except Exception as e:
        st.error(f"Error saving data: {e}")

# Load data
data = load_data()

# Date and week logic
today = datetime.date.today()
today_str = str(today)
days_to_sunday = (today.weekday() + 1) % 7
start_sunday = today - datetime.timedelta(days=days_to_sunday)
current_week_key = str(start_sunday)

days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
options = ["", "PFD", "Flying", "Leave", "Pass", "School", "O/P", "Duty", "Recovery", "Appointment", "QTRS", "Range", "Exercise"]

# Weekly reset if needed
if data.get("week_key", "") != current_week_key:
    data["week_key"] = current_week_key
    for name in data["personnel"]:
        data["statuses"][name] = {day: "" for day in days}
    save_data(data)

# Daily PFD reset
for name in data.get("personnel", []):
    if name not in data["pfd"]:
        data["pfd"][name] = {"status": False, "last_date": today_str}
    if data["pfd"][name]["last_date"] != today_str:
        data["pfd"][name] = {"status": False, "last_date": today_str}
        save_data(data)

# Streamlit UI
st.title("Platoon Accountability Tracker")
st.set_page_config(layout="wide")  # Better for mobile

# Add personnel
new_name = st.text_input("Add Personnel")
if st.button("Add") and new_name:
    if new_name not in data["personnel"]:
        data["personnel"].append(new_name)
        data["statuses"][new_name] = {day: "" for day in days}
        data["pfd"][new_name] = {"status": False, "last_date": today_str}
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
    save_data(data)
    st.rerun()

# Dashboard
st.subheader("Weekly Dashboard")
if not data["personnel"]:
    st.write("No personnel added yet.")
else:
    header_cols = st.columns([1, 2] + [1] * 7)
    header_cols[0].write("PFD (Today)")
    header_cols[1].write("Name")
    for i, day in enumerate(days):
        header_cols[i + 2].write(day)

    for name in data["personnel"]:
        row_cols = st.columns([1, 2] + [1] * 7)
        current_pfd = data["pfd"][name]["status"]
        new_pfd = row_cols[0].checkbox("", value=current_pfd, key=f"pfd_{name}_{today_str}")
        if new_pfd != current_pfd:
            data["pfd"][name]["status"] = new_pfd
            data["pfd"][name]["last_date"] = today_str
            save_data(data)

        row_cols[1].write(name)

        for i, day in enumerate(days):
            current_status = data["statuses"][name].get(day, "")
            new_status = row_cols[i + 2].selectbox("", options, index=options.index(current_status), key=f"status_{name}_{day}_{current_week_key}")
            if new_status != current_status:
                data["statuses"][name][day] = new_status
                save_data(data)