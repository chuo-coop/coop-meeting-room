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
                            if (d["user"] in r["user"]  # ← 部分一致で照合
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
