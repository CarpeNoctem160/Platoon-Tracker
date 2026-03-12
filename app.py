import streamlit as st
import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import timezone # For UTC handling

# Google Sheets Setup
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Your Google Sheet name (match what you created)
SHEET_NAME = "PlatoonTrackerData"
sheet = client.open(SHEET_NAME).sheet1 # First worksheet

# Helper functions for data
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

# Streamlit UI for Home Page
st.set_page_config(page_title="Company Accountability Organizer", layout="wide")
st.title("Company Accountability Organizer")

# Platoon selector (persists via session state)
platoon_choice = st.selectbox(
    "Select Platoon to View / Edit",
    ["All (Company View)", "1st Platoon", "2nd Platoon"],
    index=1 # default to 1st
)

# Map to simple key
if platoon_choice == "All (Company View)":
    st.session_state.selected_platoon = "All"
elif platoon_choice == "1st Platoon":
    st.session_state.selected_platoon = "1st"
else:
    st.session_state.selected_platoon = "2nd"

st.markdown("---")

st.write("Use the sidebar navigation to access the detailed tracker (filtered by your selection above).")
st.info("Add/edit personnel on the Tracker page. Changes apply to the whole company but filtered views show only the selected platoon.")

# Quick company stats
st.metric("Total Personnel", len(data["personnel"]))
col1, col2 = st.columns(2)
col1.metric("1st Platoon", sum(1 for v in data["platoon_map"].values() if v == "1st"))
col2.metric("2nd Platoon", sum(1 for v in data["platoon_map"].values() if v == "2nd"))