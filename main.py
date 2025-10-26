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
            new = {"date": str(date), "start": start, "end": end, "user": f"{user}(全面)",
                   "purpose": purpose, "ext": ext, "status": "active", "cancel": ""}
            st.session_state["reservations"][subroom].append(new)
        st.session_state["pending_register"] = None
        st.success("✅ 全面予約を登録しました。")
        st.experimental_rerun()
    else:
        new = {"date": str(date), "start": start, "end": end, "user": user,
               "purpose": purpose, "ext": ext, "status": "active", "cancel": ""}
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
        row = [f"<div style='width:60px;text-align:center;font-weight:600;font-size:14px;border:1px solid #999;background:#f9f9f9;'>{label}</div>"]
        for slot in TIME_SLOTS:
            s0 = parse_time(slot)
            e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()
            color, text = "#ffffff", ""
            if layer in ["前側", "奥側"]:
                active = any(r["status"] == "active" and str(r["date"]) == str(date) and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                             for r in st.session_state["reservations"][layer])
                color = "#ffcccc" if active else "#ccffcc"
                text = f"<span style='font-size:14px;font-weight:500;'>{slot}</span>"
            else:
                front_busy = any(r["status"] == "active" and str(r["date"]) == str(date) and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                                 for r in st.session_state["reservations"]["前側"])
                back_busy = any(r["status"] == "active" and str(r["date"]) == str(date) and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
                                for r in st.session_state["reservations"]["奥側"])
                if front_busy and back_busy:
                    color = "#ff3333"
                    text = "<b><span style='color:white;font-size:15px;'>満</span></b>"
            row.append(f"<div style='flex:1;background:{color};border:1px solid #aaa;text-align:center;padding:4px;'>{text}</div>")
        st.markdown(f"<div style='display:flex;'>{''.join(row)}</div>", unsafe_allow_html=True)
    # --- 一覧表 ---
    st.divider()
    st.markdown("### 📋 使用状況一覧（時間順）")
    all_recs = []
    for room, items in st.session_state["reservations"].items():
        for r in items:
            if str(r["date"]) == str(date):
                all_recs.append({
                    "区画": room,
                    "時間": f"{r['start']}〜{r['end']}",
                    "担当者": r["user"],
                    "目的": r["purpose"],
                    "内線": r["ext"],
                    "状態": "取消" if r["status"] == "cancel" else "有効",
                    "取消日": r["cancel"]
                })

    # --- 全面統合表示 ---
    merged = []
    seen = set()
    for i, r1 in enumerate(all_recs):
        if i in seen:
            continue
        same = [r for r in all_recs if r["担当者"] == r1["担当者"]
                and r["時間"] == r1["時間"]
                and r["状態"] == r1["状態"]
                and r["区画"] in ["前側", "奥側"]]
        if len(same) == 2:
            merged.append({**r1, "区画": "全面"})
            seen.update([all_recs.index(x) for x in same])
        else:
            merged.append(r1)

    if merged:
        df = pd.DataFrame(merged).sort_values(by="時間")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("当日の予約はありません。")

    # --- 登録 ---
    st.divider()
    st.subheader("📝 新しい予約を登録")

    c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1, 2, 1])
    room = c1.selectbox("区画", ROOMS)
    start = c2.selectbox("開始", TIME_SLOTS)
    end = c3.selectbox("終了", TIME_SLOTS)
    user = c4.text_input("担当者")
    purpose = c5.text_input("目的（任意）")
    ext = c6.text_input("内線（任意）")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    btn_center = st.columns([1, 1, 1])[1]
    with btn_center:
        if st.button("登録", use_container_width=True):
            if not user:
                st.error("担当者名を入力してください。")
            elif parse_time(end) <= parse_time(start):
                st.error("終了時刻は開始より後にしてください。")
            elif has_conflict(room, date, start, end):
                st.warning("⚠️ この時間帯はすでに予約されています。")
            else:
                st.session_state["pending_register"] = {"room": room, "date": date, "start": start, "end": end,
                                                         "user": user, "purpose": purpose, "ext": ext}

    # 登録確認
    if st.session_state["pending_register"]:
        d = st.session_state["pending_register"]
        st.markdown(f"<div style='border:2px solid #666;padding:10px;background:#f0f0f0;text-align:center;'>"
                    f"<b>登録内容確認：</b><br>{d['room']}　{d['start']}〜{d['end']}　{d['user']}<br>これで登録しますか？</div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2:
            b1, b2 = st.columns([1, 1])
            with b1:
                if st.button("はい、登録する"):
                    register_reservation(**d)
            with b2:
                if st.button("戻る"):
                    st.session_state["pending_register"] = None

    # --- 取消 ---
    st.divider()
    st.subheader("🗑️ 予約取消")

    cancels = []
    for room, items in st.session_state["reservations"].items():
        for r in items:
            if str(r["date"]) == str(date) and r["status"] == "active":
                cancels.append(f"{room} | {r['user']} | {r['start']}〜{r['end']}")

    # 全面予約ペアを抽出して追加
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
        sel = st.selectbox("取消対象を選択", cancels)
        if st.button("取消"):
            room, user, t = sel.split(" | ")
            start, end = t.split("〜")
            st.session_state["pending_cancel"] = {"room": room, "user": user, "start": start, "end": end, "date": date}

    if st.session_state["pending_cancel"]:
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
                                if (r["user"] == d["user"]
                                    and r["start"] == d["start"]
                                    and r["end"] == d["end"]
                                    and str(r["date"]) == str(d["date"])
                                    and r["status"] == "active"):
                                    r["status"] = "cancel"
                                    r["cancel"] = datetime.now().strftime("%Y-%m-%d")
                        st.success("🗑️ 全面予約を取り消しました。")
                        st.experimental_rerun()
                    else:
                        cancel_reservation(**d)
            with b2:
                if st.button("戻る"):
                    st.session_state["pending_cancel"] = None

    if st.button("⬅ カレンダーへ戻る"):
        st.session_state["page"] = "calendar"
        st.experimental_rerun()

    st.caption("中央大学生活協同組合　情報通信チーム（v3.4.5 全面利用対応版）")

