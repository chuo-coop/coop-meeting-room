import streamlit as st
st.set_page_config(page_title="中大生協 会議室予約（日表示）", layout="wide")
from datetime import datetime, timedelta, time
import pandas as pd

# --- ページ設定（main.py 側にあるためここでは不要）
st.markdown("## 📅 会議室予約（日表示）")

ROOMS = ["前方区画", "後方区画", "全体利用"]
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]

# --- 初期化 ---
if "reservations" not in st.session_state:
    st.session_state["reservations"] = {r: [] for r in ROOMS}

def overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1

def parse_time(tstr: str) -> time:
    h, m = map(int, tstr.split(":"))
    return time(h, m)

# --- 登録関数 ---
def register_reservation(room, date, start, end, user, purpose, extension):
    new_res = {"date": date, "start": start, "end": end, "user": user, "purpose": purpose, "extension": extension}

    # 全体利用チェック
    if room == "全体利用":
        for rname in ["前方区画", "後方区画"]:
            for r in st.session_state["reservations"][rname]:
                if (r["date"] == date) and overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end)):
                    st.warning(f"⚠ {rname} に既に予約があるため、全体利用は確保できません。")
                    return False
        st.session_state["reservations"][room].append(new_res)
        for rname in ["前方区画", "後方区画"]:
            st.session_state["reservations"][rname].append(new_res.copy())
        return True

    # 半面予約時：全体利用と衝突していないか
    for r in st.session_state["reservations"]["全体利用"]:
        if (r["date"] == date) and overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end)):
            st.warning("⚠ この時間帯は全体利用で予約済みです。")
            return False

    # 半面登録
    st.session_state["reservations"][room].append(new_res)

    # 他区画と重なれば全体にも反映
    other = "後方区画" if room == "前方区画" else "前方区画"
    overlap_found = any(
        (r["date"] == date)
        and overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end))
        for r in st.session_state["reservations"][other]
    )
    if overlap_found:
        st.session_state["reservations"]["全体利用"].append(new_res.copy())
    return True

# --- 予約削除関数 ---
def cancel_reservation(room, user, start, end, selected_date):
    for rlist in st.session_state["reservations"].values():
        rlist[:] = [r for r in rlist if not (r["user"] == user and r["start"] == start and r["end"] == end and r["date"] == selected_date)]
    st.success("🗑️ 予約を取り消しました。")
    st.rerun()

# --- 日付選択 ---
selected_date = st.session_state.get("selected_date", datetime.now().date())
st.markdown(f"### 📆 {selected_date} の利用状況（全区画）")

# --- 凡例 ---
st.markdown("""
<div style='display:flex;gap:24px;align-items:center;margin:6px 0 14px 2px;font-size:14px;'>
  <div><span style='display:inline-block;width:18px;height:18px;background:#ccffcc;border:1px solid #999;'></span>空室</div>
  <div><span style='display:inline-block;width:18px;height:18px;background:#ffcccc;border:1px solid #999;'></span>予約済</div>
</div>
""", unsafe_allow_html=True)

# --- スケジュール表示 ---
for room in ROOMS:
    st.markdown(f"### 🏢 {room}")
    res_list = st.session_state["reservations"][room]
    cells = []
    for slot in TIME_SLOTS:
        s0 = parse_time(slot)
        e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()
        color = "#ccffcc"
        for r in res_list:
            if (r["date"] == selected_date) and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0):
                color = "#ffcccc"
                break
        cells.append(f"<div style='flex:1;background:{color};border:1px solid #aaa;font-size:10px;text-align:center;padding:3px;'>{slot}</div>")
    st.markdown(f"<div style='display:flex;gap:1px;margin-bottom:10px;'>{''.join(cells)}</div>", unsafe_allow_html=True)

st.divider()

# --- 予約登録 ---
st.subheader("📝 新しい予約を登録")
with st.form("add_reservation"):
    c1, c2, c3, c4, c5, c6 = st.columns([1,1,1,1,2,1])
    with c1:
        room_sel = st.selectbox("区画", ROOMS)
    with c2:
        start_sel = st.selectbox("開始", TIME_SLOTS)
    with c3:
        end_sel = st.selectbox("終了", TIME_SLOTS)
    with c4:
        user = st.text_input("氏名", max_chars=16)
    with c5:
        purpose = st.text_input("目的", placeholder="任意")
    with c6:
        extension = st.text_input("内線", placeholder="例：1234")

    submitted = st.form_submit_button("登録")

    if submitted:
        try:
            s = parse_time(start_sel)
            e = parse_time(end_sel)
            if e <= s:
                st.error("終了時刻は開始より後にしてください。")
            elif not user.strip():
                st.warning("氏名を入力してください。")
            else:
                ok = register_reservation(room_sel, selected_date, start_sel, end_sel, user, purpose, extension)
                if ok:
                    st.success("✅ 登録が完了しました。")
                    st.rerun()
        except Exception as e:
            st.error(f"⚠ 登録処理でエラーが発生しました: {e}")

# --- 予約取消 ---
st.divider()
st.subheader("🗑️ 予約を取り消す")
all_res = []
for rname, items in st.session_state["reservations"].items():
    for it in items:
        if it["date"] == selected_date:
            all_res.append({"room": rname, **it})

if all_res:
    df_cancel = pd.DataFrame(all_res)
    sel = st.selectbox("削除する予約を選択", df_cancel.apply(lambda x: f"{x['room']} | {x['user']} | {x['start']}〜{x['end']}", axis=1))
    if st.button("選択した予約を取り消す"):
        room, user, se = sel.split(" | ")
        start, end = se.split("〜")
        cancel_reservation(room, user, start, end, selected_date)
else:
    st.caption("当日の予約はありません。")

# --- 当日詳細 ---
st.divider()
st.subheader("📋 当日の予約詳細")
if all_res:
    st.dataframe(pd.DataFrame(all_res), hide_index=True, use_container_width=True)
else:
    st.caption("本日分の予約データはありません。")

st.caption("中央大学生活協同組合　情報通信チーム（安定動作版）")


