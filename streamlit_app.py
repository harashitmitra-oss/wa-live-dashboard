import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="WhatsApp Live Dashboard",
    page_icon="💬",
    layout="wide"
)

st_autorefresh(interval=10000, key="wa_refresh")

st.title("💬 WhatsApp Live Dashboard")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

@st.cache_resource
def get_gsheet_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(creds)

@st.cache_data(ttl=10)
def load_data():
    gc = get_gsheet_client()
    sheet = gc.open_by_key(st.secrets["SHEET_ID"]).worksheet("Messages")
    rows = sheet.get_all_records()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    if "received_at" in df.columns:
        df["received_at"] = pd.to_datetime(df["received_at"], errors="coerce")

    return df

df = load_data()

if df.empty:
    st.warning("No WhatsApp messages found yet.")
    st.stop()

total_messages = len(df)
unique_chats = df["chat_id"].nunique() if "chat_id" in df.columns else 0
unique_senders = df["sender"].nunique() if "sender" in df.columns else 0

today = pd.Timestamp.now().date()
if "received_at" in df.columns:
    today_messages = df[df["received_at"].dt.date == today].shape[0]
else:
    today_messages = 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Messages", total_messages)
col2.metric("Messages Today", today_messages)
col3.metric("Unique Chats", unique_chats)
col4.metric("Unique Senders", unique_senders)

st.divider()

if "received_at" in df.columns:
    daily = (
        df.dropna(subset=["received_at"])
        .assign(date=lambda x: x["received_at"].dt.date)
        .groupby("date")
        .size()
        .reset_index(name="messages")
    )

    st.subheader("Daily Message Trend")
    st.line_chart(daily, x="date", y="messages")

st.subheader("Top Active Senders")

if "push_name" in df.columns:
    top_senders = (
        df.groupby(["sender", "push_name"], dropna=False)
        .size()
        .reset_index(name="messages")
        .sort_values("messages", ascending=False)
        .head(20)
    )
else:
    top_senders = (
        df.groupby("sender", dropna=False)
        .size()
        .reset_index(name="messages")
        .sort_values("messages", ascending=False)
        .head(20)
    )

st.dataframe(top_senders, use_container_width=True)

st.subheader("Latest Messages")

show_cols = [
    "received_at",
    "push_name",
    "sender",
    "chat_id",
    "message_type",
    "message_text",
]

available_cols = [c for c in show_cols if c in df.columns]

latest = df.sort_values("received_at", ascending=False).head(100)
st.dataframe(latest[available_cols], use_container_width=True)
