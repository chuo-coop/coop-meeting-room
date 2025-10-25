import streamlit as st
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
    st.title("🔒 会議室予約システム ログイン")
    input_pw = st.text_input("パスワードを入力してください", type="password")
    if st.button("ログイン"):
        if input_pw == PASSWORD:
            st.session_state["authenticated"] = True
            st.success("ログイン成功。システムを開きます。")
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
    st.session_state["reservations"] = {r: [] for r in ["前側", "奥側"]}

ROOMS = ["前側", "奥側"]
TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(9, 21) for m in (0, 30)]

# -------------------------------------------------------------
# 関数定義
# -------------------------------------------------------------
def overlap(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1

def parse_time(tstr: str) -> time:
    h, m = map(int, tstr.split(":"))
    return time(h, m)

def register_reservation(room, date, start, end, user):
    new_res = {"date": date, "start": start, "end": end, "user": user}
    for r in st.session_state["reservations"][room]:
        if (r["date"] == date) and overlap(parse_time(r["start"]), parse_time(r["end"]), parse_time(start), parse_time(end)):
            st.warning(f"{room} のこの時間帯はすでに予約があります。")
            return False
    st.session_state["reservations"][room].append(new_res)
    return True

# -------------------------------------------------------------
# カレンダー画面
# -------------------------------------------------------------
if st.session_state["page"] == "calendar":
    st.title("📅 会議室カレンダー")

    selected = st.date_input("日付を選択", st.session_state["selected_date"])
    st.session_state["selected_date"] = selected

    if st.button("この日の予約状況を見る"):
        st.session_state["page"] = "day_view"
        st.experimental_rerun()

# -------------------------------------------------------------
# 日別表示（30分スロット＋満インジケーター）
# -------------------------------------------------------------
elif st.session_state["page"] == "day_view":
    selected_date = st.session_state["selected_date"]
    st.markdown(f"## 🗓️ {selected_date} の利用状況")

    st.markdown("""
    <div style='display:flex;gap:24px;align-items:center;margin:6px 0 14px 2px;font-size:14px;'>
      <div><span style='display:inline-block;width:18px;height:18px;background:#ccffcc;border:1px solid #999;'></span>空室</div>
      <div><span style='display:inline-block;width:18px;height:18px;background:#ffcccc;border:1px solid #999;'></span>予約済</div>
      <div><span style='display:inline-block;border:1px solid #000;padding:1px 4px;'>満</span> 前・奥 両方利用中</div>
    </div>
    """, unsafe_allow_html=True)

    # 30分スロット表示
    st.markdown("### 🏢 利用スロット")
    for slot in TIME_SLOTS:
        s0 = parse_time(slot)
        e0 = (datetime.combine(datetime.today(), s0) + timedelta(minutes=30)).time()

        # 前側状態
        front_reserved = any(
            (r["date"] == selected_date)
            and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
            for r in st.session_state["reservations"]["前側"]
        )

        # 奥側状態
        back_reserved = any(
            (r["date"] == selected_date)
            and overlap(parse_time(r["start"]), parse_time(r["end"]), s0, e0)
            for r in st.session_state["reservations"]["奥側"]
        )

        # 背景色設定
        front_color = "#ffcccc" if front_reserved else "#ccffcc"
        back_color = "#ffcccc" if back_reserved else "#ccffcc"

        # 満インジケーター
        full_label = "<div style='border:1px solid #000;padding:0 6px;display:inline-block;'>満</div>" if (front_reserved and back_reserved) else ""

        st.markdown(f"""
        <div style='display:flex;align-items:center;margin-bottom:2px;'>
          <div style='width:70px;font-size:12px;'>{slot}</div>
          <div style='flex:1;display:flex;'>
            <div style='flex:1;background:{front_color};border:1px solid #aaa;text-align:center;font-size:11px;'>前側</div>
            <div style='flex:1;background:{back_color};border:1px solid #aaa;text-align:center;font-size:11px;'>奥側</div>
            <div style='width:60px;text-align:center;font-size:11px;'>{full_label}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 登録フォーム
    # -------------------------------------------------------------
    st.divider()
    st.subheader("📝 新しい予約を登録")

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    with c1:
        room_sel = st.selectbox("区分", ROOMS)
    with c2:
        start_sel = st.selectbox("開始", TIME_SLOTS)
    with c3:
        end_sel = st.selectbox("終了", TIME_SLOTS)
    with c4:
        user = st.text_input("担当者（苗字）", max_chars=16)

    if st.button("登録"):
        s = parse_time(start_sel)
        e = parse_time(end_sel)
        if e <= s:
            st.error("終了時刻は開始より後にしてください。")
        elif not user:
            st.error("担当者名（苗字）は必須です。")
        else:
            if register_reservation(room_sel, selected_date, start_sel, end_sel, user):
                st.success("登録が完了しました。")
                st.experimental_rerun()

    if st.button("⬅ カレンダーへ戻る"):
        st.session_state["page"] = "calendar"
        st.experimental_rerun()

    st.caption("中央大学生活協同組合　情報通信チーム（v3：30分スロット＋3行満インジケーター）")
