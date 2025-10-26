# =========================================================
# 中大生協 会議室予約システム v3.4.5
# （全面利用対応版：登録・一覧統合・一括取消）
# =========================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time

# -------------------------------------------------------------
# ページ設定
# -------------------------------------------------------------
st.set_page_config(page_title="中大生協 会議室予約システム", layout="wide")

# -------------------------------------------------------------
# ログイン認証
# -------------------------------------------------------------
PASSWORD = "coop"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if not st.session_state["authenticated"]:
    st.markdown("<h2 style='text-align:center;'>🔒 会議室予約システム</h2>", unsafe_allow_html=True)
    col = st.columns([1, 2, 1])[1]
    with col:
        pw = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if pw == PASSWORD:
                st.session_state["authenticated"] = True
                st.experimental_rerun()
            else:
                st.error("パスワードが違います。")
    st.stop()

# -------------------------------------------------------------
# 初期化
# -------------------------------------------------------------
if "page" not in st.session_state:
    st.session_state["page"] = "calendar"
if "selected_date" not in st.session_state:
    st.session_state["selected_date"] = datetime.now().date()
if "reservations" not in st.session_state:
    st.session_state["reservations"] = {"前側": [], "奥側": []}
if "pending_register" not in st.session_state:
    st.session_state["pending_register"] = None
if "pending_cancel" not in st.session_state:
    st.session_state["pending_cancel"] = None

ROOMS = ["前側", "奥側", "全面"]  # ← 全面追加
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]

# -------------------------------------------------------------
# 関数定義
# -------------------------------------------------------------
def parse_time(tstr):
    h, m = map(int, tstr.split(":"))
    return time(h, m)


def overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1


def has_conflict(room, date, start, end):
    """同区画・同日・時間重複を検出（全面相互排他対応）"""
    date_str = str(date)

    # 全面予約存在チェック（部分利用を禁止）
    for subroom in ["前側", "奥側"]:
        for r in st.session_state["reservations"][subroom]:
            if str(r.get("date")) == date_str and r.get("status") == "active" and r["user"].endswith("(全面)"):
                if overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end)):
                    return True

    # 部分 or 全面の通常判定
    if room == "全面":
        targets = ["前側", "奥側"]
    else:
        targets = [room]

    for sub in targets:
        for r in st.session_state["reservations"][sub]:
            if str(r.get("date")) == date_str and r.get("status", "active") == "active":
                s1, e1 = parse_time(r["start"]), parse_time(r["end"])
                s2, e2 = parse_time(start), parse_time(end)
                if overlap(s1, e1, s2, e2):
                    return True

    return False


def register_reservation(room, date, start, end, user, purpose, ext):
    """登録確定（rerun実行・全面対応）"""
    if room == "全面":
        # 両区画に重複がないか確認
        for subroom in ["前側", "奥側"]:
            if has_conflict(subroom, date, start, end):
                st.warning(f"{subroom}に既存の予約があります。全面予約できません。")
                return
        # 両区画へ同時登録
        for subroom in ["前側", "奥側"]:
            new = {
                "date": str(date),
                "start": start,
                "end": end,
                "user": f"{user}(全面)",
                "purpose": purpose,
                "ext": ext,
                "status": "active",
                "cancel": "",
            }
            st.session_state["reservations"][subroom].append(new)
        st.session_state["pending_register"] = None
        st.success("✅ 全面予約を登録しました。")
        st.experimental_rerun()
    else:
        new = {
            "date": str(date),
            "start": start,
            "end": end,
            "user": user,
            "purpose": purpose,
            "ext": ext,
            "status": "active",
            "cancel": "",
        }
        st.session_state["reservations"][room].append(new)
        st.session_state["pending_register"] = None
        st.success("✅ 登録が完了しました。")
        st.experimental_rerun()


def cancel_reservation(room, user, start, end, date):
    """取消確定（rerun実行）"""
    for r in st.session_state["reservations"][room]:
        if r["user"] == user and r["start"] == start and r["end"] == end and str(r["date"]) == str(date):
            r["status"] = "cancel"
            r["cancel"] = datetime.now().strftime("%Y-%m-%d")
    st.session_state["pending_cancel"] = None
    st.success("🗑️ 予約を取り消しました。")
    st.experimental_rerun()

# -------------------------------------------------------------
# カレンダー画面
# -------------------------------------------------------------
if st.session_state["page"] == "calendar":
    st.title("📅 会議室カレンダー")
    selected = st.date_input("日付を選択", datetime.now().date())
    st.session_state["selected_date"] = selected
    if st.button("この日の予約状況を見る"):
        st.session_state["page"] = "day_view"
        st.experimental_rerun()

# -------------------------------------------------------------
# 日別表示
# -------------------------------------------------------------
elif st.session_state["page"] == "day_view":
    date = st.session_state["selected_date"]
    st.markdown(f"## 🗓️ {date} の利用状況")

    # --- インジケータ ---
    st.markdown("### 🏢 利用インジケータ（凡例付き）")
    for idx, layer in enumerate(["前側", "奥側", "満"]):
        label = ["前側", "奥側", "満"][idx]
        row = [
            f"<div style='width:60px;text-align:center;font-weight:600;font-size:14px;border:1px solid #999;background:#f9f9f9;'>{label}</div>"
        ]
        for slot in TIME_SLOTS:
            s0 = parse_time(slot)
            e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()
            color, text = "#ffffff", ""
            if layer in ["前側", "奥側"]:
                active = any(
                    r["status"] == "active"
                    and str(r["date"]) == str(date)
                    and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                    for r in st.session_state["reservations"][layer]
                )
                color = "#ffcccc" if active else "#ccffcc"
                text = f"<span style='font-size:14px;font-weight:500;'>{slot}</span>"
            else:
                front_busy = any(
                    r["status"] == "active"
                    and str(r["date"]) == str(date)
                    and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                    for r in st.session_state["reservations"]["前側"]
                )
                back_busy = any(
                    r["status"] == "active"
                    and str(r["date"]) == str(date)
                    and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                    for r in st.session_state["reservations"]["奥側"]
                )
                if front_busy and back_busy:
                    color = "#ff3333"
                    text = "<b><span style='color:white;font-size:15px;'>満</span></b>"
            row.append(
                f"<div style='flex:1;background:{color};border:1px solid #aaa;text-align:center;padding:4px;'>{text}</div>"
            )
        st.markdown(f"<div style='display:flex;'>{''.join(row)}</div>", unsafe_allow_html=True)
