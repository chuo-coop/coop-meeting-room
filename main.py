# main_v3.4.7_full_fixed.py
# Streamlit会議室予約システム v3.4.7 Full Fixed
# - GCPスコープ追加
# - 全面1行保存 / 読込時分解
# - 取消重複除去対応

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

# === 設定 ===
SHEET_ID = "1ebbNq681Loz2r-_Wkgbd_6qABN_H1GzsG2Ja0p9JJOg"

def get_gsheet():
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet

def load_reservations_from_gsheet():
    sheet = get_gsheet()
    records = sheet.get_all_records()
    st.session_state["reservations"] = {"前側": [], "奥側": []}
    for row in records:
        room = row.get("区画", "")
        date = row.get("日付", "")
        start = row.get("開始", "")
        end = row.get("終了", "")
        user = row.get("担当者", "")
        purpose = row.get("目的", "")
        ext = row.get("内線", "")
        status = row.get("状態", "")
        cancel = row.get("取消日", "")

        if room == "全面":
            for sub in ["前側", "奥側"]:
                st.session_state["reservations"][sub].append({
                    "date": date, "start": start, "end": end,
                    "user": f"{user}(全面)", "purpose": purpose,
                    "ext": ext, "status": status, "cancel": cancel
                })
        elif room in ["前側", "奥側"]:
            st.session_state["reservations"][room].append({
                "date": date, "start": start, "end": end,
                "user": user, "purpose": purpose, "ext": ext,
                "status": status, "cancel": cancel
            })

def save_reservations_to_gsheet():
    try:
        sheet = get_gsheet()
        def _norm_user(u): return u.replace("(全面)", "")
        buf = {}
        for room, items in st.session_state["reservations"].items():
            for r in items:
                key = (
                    str(r.get("date")), r.get("start"), r.get("end"),
                    _norm_user(r.get("user", "")),
                    r.get("status", "active"), r.get("cancel", "")
                )
                if key not in buf:
                    buf[key] = {"rooms": set(), "purpose": r.get("purpose", ""), "ext": r.get("ext", "")}
                buf[key]["rooms"].add(room)
        all_data = []
        for (date, start, end, user_norm, status, cancel), meta in buf.items():
            out_room = "全面" if {"前側", "奥側"}.issubset(meta["rooms"]) else list(meta["rooms"])[0]
            all_data.append([
                out_room, date, start, end, user_norm,
                meta.get("purpose", ""), meta.get("ext", ""), status, cancel
            ])
        sheet.clear()
        sheet.update(
            [["区画", "日付", "開始", "終了", "担当者", "目的", "内線", "状態", "取消日"]] + all_data
        )
        st.caption("💾 Google Sheetsに保存しました。")
    except Exception as e:
        st.error(f"Google Sheetsへの保存に失敗しました: {e}")

st.title("会議室予約システム v3.4.7 Full Fixed")
st.caption("中央大学生活協同組合")

if "reservations" not in st.session_state:
    load_reservations_from_gsheet()
    st.success("📗 Google Sheetsから既存データを読み込みました。")

# --- 取消 ---
st.divider()
st.subheader("🗑️ 予約取消")

cancels = []
seen = set()
date = datetime.today().strftime("%Y-%m-%d")

for room, items in st.session_state["reservations"].items():
    for r in items:
        if str(r["date"]) == str(date) and r["status"] == "active":
            key = (r["user"], r["start"], r["end"])
            if key not in seen:
                cancels.append(f"{room} | {r['user']} | {r['start']}〜{r['end']}")
                seen.add(key)

pairs = []
for r in st.session_state["reservations"]["前側"]:
    for s in st.session_state["reservations"]["奥側"]:
        if (r["user"] == s["user"]
            and r["start"] == s["start"]
            and r["end"] == s["end"]
            and str(r["date"]) == str(s["date"])
            and r["status"] == "active"
            and s["status"] == "active"):
            pairs.append(f"全面 | {r['user']} | {r['start']}〜{r['end']}")

cancels = list(dict.fromkeys(cancels + pairs))

if cancels:
    sel = st.selectbox("取消対象を選択", cancels, key=f"cancel_sel_{date}")
    if st.button("取消"):
        room, user, t = sel.split(" | ")
        start, end = t.split("〜")
        st.session_state["pending_cancel"] = {"room": room, "user": user, "start": start, "end": end, "date": date}

if st.session_state.get("pending_cancel"):
    d = st.session_state["pending_cancel"]
    st.markdown(f"<div style='border:2px solid #900;padding:10px;background:#fff0f0;text-align:center;'>"
                f"<b>取消確認：</b><br>{d['room']}　{d['start']}〜{d['end']}　{d['user']}<br>本当に取り消しますか？</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        b1, b2 = st.columns([1, 1])
        with b1:
            if st.button("はい、取消する"):
                if d["room"] == "全面":
                    for sub in ["前側", "奥側"]:
                        for r in st.session_state["reservations"][sub]:
                            if ((r["user"] == d["user"]) or (r["user"] == f"{d['user']}(全面)") or (d["user"] in r["user"]))                                 and r["start"] == d["start"] and r["end"] == d["end"]                                 and str(r["date"]) == str(d["date"]) and r["status"] == "active":
                                r["status"] = "cancel"
                                r["cancel"] = datetime.now().strftime("%Y-%m-%d")
                                r["room"] = "全面"
                    save_reservations_to_gsheet()
                    st.success("🗑️ 全面予約を取り消しました。")
                    st.session_state["pending_cancel"] = None
                    st.experimental_rerun()
                else:
                    for r in st.session_state["reservations"][d["room"]]:
                        if ((r["user"] == d["user"]) or (r["user"] == f"{d['user']}(全面)") or (d["user"] in r["user"]))                             and r["start"] == d["start"] and r["end"] == d["end"]                             and str(r["date"]) == str(d["date"]) and r["status"] == "active":
                            r["status"] = "cancel"
                            r["cancel"] = datetime.now().strftime("%Y-%m-%d")
                    save_reservations_to_gsheet()
                    st.success("🗑️ 予約を取り消しました。")
                    st.session_state["pending_cancel"] = None
                    st.experimental_rerun()
        with b2:
            if st.button("戻る"):
                st.session_state["pending_cancel"] = None

st.caption("中央大学生活協同組合　情報通信チーム（v3.4.7 Full Fixed）")
