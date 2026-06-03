Import streamlit as st
import pandas as pd

# ページの設定
st.set_page_config(page_title="規定回数 推測ツール", layout="centered")
st.title("🎯 規定スイカ回数 推測ツール")

# 初期データ
PRIOR_PROBS = {10: 0.066, 15: 0.031, 20: 0.059, 25: 0.031, 30: 0.125, 35: 0.078, 40: 0.227, 45: 0.078, 50: 0.227, 100: 0.078}

def get_dice_category(dice_str):
    dice_str = str(dice_str).strip()
    if len(dice_str) != 2 or not dice_str.isdigit(): return "その他"
    d1, d2 = int(dice_str[0]), int(dice_str[1])
    if d1 == d2: return f"ゾロ目_{d1}"
    if (d1 + d2) <= 5: return "合計5以下"
    if (d1 % 2 == 0) and (d2 % 2 == 0): return "偶数×偶数"
    if (d1 % 2 != 0) and (d2 % 2 != 0): return "奇数×奇数"
    return "その他"

def calculate_likelihood(target_limit, current_suika, dice_category):
    remaining = target_limit - current_suika
    if remaining <= 0: return 0.0
    state = "1-29" if 1 <= remaining <= 29 else "30-49" if 30 <= remaining <= 49 else "50+"
    if "ゾロ目" in dice_category:
        if state != "1-29": return 0.0
        num = int(dice_category.split("_")[1])
        return 0.25 if remaining <= {1: 5, 2: 10, 3: 15, 4: 20, 5: 25, 6: 30}[num] else 0.0
    if dice_category == "合計5以下": return 0.15 if state == "1-29" else 0.0
    tens_digit = (remaining // 10) % 10
    if dice_category == "偶数×偶数" and tens_digit % 2 != 0: return 0.0
    if dice_category == "奇数×奇数" and tens_digit % 2 == 0: return 0.0
    return {"偶数×偶数": {"1-29": 0.15, "30-49": 0.50, "50+": 0.35}, "奇数×奇数": {"1-29": 0.15, "30-49": 0.50, "50+": 0.35}, "その他": {"1-29": 0.45, "30-49": 0.50, "50+": 0.65}}.get(dice_category, {"1-29": 0.45, "30-49": 0.50, "50+": 0.65})[state]

# セッション状態（データ保持用）の初期化
if "history" not in st.session_state:
    st.session_state.history = [
        {"dice": "43", "suika": 3},
        {"dice": "24", "suika": 12},
    ]

# --- 入力エリア ---
st.subheader("📥 データの入力")
col1, col2 = st.columns(2)
with col1:
    input_dice = st.text_input("出目（2桁の数字）", value="", max_chars=2, key="input_dice_val")
with col2:
    input_suika = st.number_input("その時のスイカ回数", min_value=0, value=0, step=1)

if st.button("➕ 履歴を追加する", use_container_width=True):
    if len(input_dice) == 2 and input_dice.isdigit():
        st.session_state.history.append({"dice": input_dice, "suika": input_suika})
        st.rerun()
    else:
        st.error("出目は2桁の数字で入力してください（例: 43）")

# --- 履歴の管理・表示 ---
st.subheader("📋 入力履歴")
if st.session_state.history:
    for idx, item in enumerate(st.session_state.history):
        c1, c2, c3 = st.columns([2, 2, 1])
        c1.write(f"**{idx+1}回目**")
        c2.write(f"出目: {item['dice']} / スイカ: {item['suika']}回")
        if c3.button("❌ 削除", key=f"del_{idx}"):
            st.session_state.history.pop(idx)
            st.rerun()
else:
    st.info("履歴がありません。上のフォームから追加してください。")
    if st.button("🔄 サンプルデータを読み込む"):
        st.session_state.history = [{"dice": "43", "suika": 3}, {"dice": "24", "suika": 12}]
        st.rerun()

st.markdown("---")

# --- 計算・結果表示エリア ---
if st.session_state.history:
    current_probs = PRIOR_PROBS.copy()
    conflict_detected = False
    
    for i, imp in enumerate(st.session_state.history):
        dice_cat = get_dice_category(imp['dice'])
        new_probs = {}
        total_likelihood = 0
        for limit in current_probs.keys():
            likelihood = calculate_likelihood(limit, imp['suika'], dice_cat)
            new_probs[limit] = current_probs[limit] * likelihood
            total_likelihood += new_probs[limit]
        if total_likelihood > 0:
            for limit in new_probs.keys(): current_probs[limit] = new_probs[limit] / total_likelihood
        else:
            st.error(f"❌ 矛盾発生: {i+1}回目 (出目:{imp['dice']} / スイカ:{imp['suika']}回)")
            conflict_detected = True
            break

    if not conflict_detected:
        res_df = pd.DataFrame([{"規定": f"{k}回", "確率": v * 100, "k": k} for k, v in current_probs.items()]).sort_values(by="確率", ascending=False).reset_index(drop=True)
        latest_suika = st.session_state.history[-1]['suika']
        mean_limit = sum(k * v for k, v in current_probs.items())
        w_5 = sum(v for k, v in current_probs.items() if k - latest_suika <= 5) * 100
        w_10 = sum(v for k, v in current_probs.items() if k - latest_suika <= 10) * 100
        w_20 = sum(v for k, v in current_probs.items() if k - latest_suika <= 20) * 100
        
        rank = "D"
        if w_5 > 50 or mean_limit - latest_suika <= 5: rank = "S"
        elif w_10 > 50 or mean_limit - latest_suika <= 12: rank = "A"
        elif w_20 > 50 or mean_limit - latest_suika <= 20: rank = "B"
        elif mean_limit - latest_suika <= 35: rank = "C"

        # 要約メッセージの表示
        st.subheader("🏆 分析結果")
        
        # 3つの主要指標をカード形式で表示
        m1, m2, m3 = st.columns(3)
        m1.metric("最有力 規定", f"{res_df.iloc[0]['規定']}", f"{res_df.iloc[0]['確率']:.1f}%")
        m2.metric("平均規定まで", f"あと {(mean_limit - latest_suika):.1f} 回", f"平均: {mean_limit:.1f}回")
        m3.metric("現在のランク", f"ランク {rank}")

        # 近い回数の確率
        st.markdown(f"🎯 **あと5回以内:** {w_5:.1f}% | **10回以内:** {w_10:.1f}% | **20回以内:** {w_20:.1f}%")

        # 詳細な確率テーブル
        st.write("📈 **詳細確率ランキング**")
        # 表示用に成形
        show_df = res_df.copy()
        show_df["確率"] = show_df["確率"].map("{:.1f}%".format)
        st.dataframe(show_df[["規定", "確率"]], use_container_width=True)

