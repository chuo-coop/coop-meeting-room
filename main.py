import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="会議室予約システム", layout="wide")

CSV_FILE = "reservations.csv"

def load_reservations():
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        df = pd.DataFrame(columns=["room", "date", "start", "end", "user", "purpose", "extension"])
    return df

def save_reservations(df):
    df.to_csv(CSV_FILE, index=False)

reservations = load_reservations()

rooms = ["前方区画", "後方区画", "全体利用"]
time_slots = [f"{h:02d}:{m:02d}" for h in range(9, 20) for m in (0, 30)]

def check_availability(df, room, date, start, end):
    df = df[(df["room"] == room) & (df["date"] == date)]
    for _, r in df.iterrows():
        if not (end <= r["start"] or start >= r["end"]):
            return False
    return True

def sync_full_room(df):
    full_list = []
    for date in df["date"].unique():
        f = df[(df["date"] == date) & (df["room"] == "前方区画")]
        b = df[(df["date"] == date) & (df["room"] == "後方区画")]
        for _, fr in f.iterrows():
            for _, br in b.iterrows():
                if not (fr["end"] <= br["start"] or fr["start"] >= br["end"]):
                    full_list.append([
                        "全体利用", date,
                        max(fr["start"], br["start"]),
                        min(fr["end"], br["end"]),
                        fr["user"], fr["purpose"], fr["extension"]
                    ])
    full_df = pd.DataFrame(full_list, columns=df.columns)
    df = df[df["room"] != "全体利用"]
    df = pd.concat([df, full_df], ignore_index=True)
    return df

today = datetime.date.today()
target_date = st.date_input("日付を選択", today)

st.header(f"{target_date} の利用状況")
view = reservations[reservations["date"] == str(target_date)]

for room in rooms:
    st.subheader(room)
    df = view[view["room"] == room]
    cols = st.columns(len(time_slots))
    for i, slot in enumerate(time_slots):
        color = "lightgreen"
        for _, r in df.iterrows():
            if r["start"] <= slot < r["end"]:
                color = "#ffb3b3"
        cols[i].markdown(
            f"<div style='background:{color};border:1px solid #ccc;text-align:center;"
            f"font-size:10px;padding:2px'>{slot}</div>", unsafe_allow_html=True
        )

st.markdown("---")

st.subheader("新しい予約を登録")
col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 1])
with col1:
    room = st.selectbox("区画", rooms[:2])
with col2:
    start = st.selectbox("開始", time_slots, index=time_slots.index("12:00"))
with col3:
    end = st.selectbox("終了", time_slots, index=time_slots.index("13:00"))
with col4:
    user = st.text_input("氏名")
with col5:
    purpose = st.text_input("目的", "会議")
with col6:
    extension = st.text_input("内線", "1234")

if st.button("登録"):
    if not user.strip():
        st.warning("氏名を入力してください。")
    elif start >= end:
        st.warning("開始時刻が終了時刻以上です。")
    elif not check_availability(reservations, room, str(target_date), start, end):
        st.error("この時間帯は既に予約があります。")
    else:
        new_data = pd.DataFrame(
            [[room, str(target_date), start, end, user, purpose, extension]],
            columns=reservations.columns
        )
        reservations = pd.concat([reservations, new_data], ignore_index=True)
        reservations = sync_full_room(reservations)
        save_reservations(reservations)
        st.success("予約を登録しました。")
        st.rerun()

st.subheader("予約を取り消す")
df_today = reservations[reservations["date"] == str(target_date)]
if not df_today.empty:
    df_today = df_today.sort_values(["room", "start"])
    df_today["表示名"] = df_today.apply(
        lambda x: f"{x['room']} | {x['user']} | {x['start']}〜{x['end']}", axis=1
    )
    target = st.selectbox("削除する予約を選択", df_today["表示名"])
    if st.button("選択した予約を取り消す"):
        sel = df_today[df_today["表示名"] == target].iloc[0]
        reservations = reservations[~(
            (reservations["room"] == sel["room"]) &
            (reservations["date"] == sel["date"]) &
            (reservations["start"] == sel["start"]) &
            (reservations["end"] == sel["end"]) &
            (reservations["user"] == sel["user"])
        )]
        reservations = sync_full_room(reservations)
        save_reservations(reservations)
        st.success("予約を削除しました。")
        st.rerun()
else:
    st.info("本日の予約はありません。")
