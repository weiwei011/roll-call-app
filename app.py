import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import datetime
import re
import time

# ==========================================
# 🔐 安全登入系統
# ==========================================
LOGIN_PASSWORD = "1234" # <--- 密碼

def check_password():
    def password_entered():
        if st.session_state["password"] == LOGIN_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 請輸入通行碼", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 請輸入通行碼", type="password", on_change=password_entered, key="password")
        st.error("🚫 密碼錯誤")
        return False
    else:
        return True

# ==========================================
# 1. 頁面設定
# ==========================================
st.set_page_config(page_title="部隊電子點名簿", layout="wide", page_icon="📝")

if not check_password():
    st.stop()

st.markdown("""
    <style>
    .stApp { background-color: #262729; color: #f0f0f0; }
    h1, h2, h3 { font-family: '微軟正黑體', sans-serif; color: #ffffff; }
    .person-card { 
        padding: 15px; border-radius: 16px; margin-bottom: 12px; 
        background-color: #333538; box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        border: 1px solid #454545; transition: transform 0.2s;
    }
    .status-camp { border-left: 6px solid #a5d6a7; }
    .status-leave { border-left: 6px solid #ffcc80; }
    .card-header { display: flex; justify-content: space-between; align-items: center; }
    .card-name { font-size: 1.3rem; font-weight: 600; color: #fff; }
    .tag-badge { 
        font-size: 0.7rem; padding: 3px 8px; border-radius: 10px; 
        background-color: #4a4d52; color: #ddd; margin-left: 8px;
    }
    .stButton button { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 資料庫核心
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

DEFAULT_ROSTER = [
    {"Category": "官員", "Name": "魏俊丞", "Tag": "宿"},
    {"Category": "官員", "Name": "曾小容", "Tag": "宿"},
    {"Category": "官員", "Name": "馬翔麟", "Tag": "宿"},
    {"Category": "左班", "Name": "卓士傑", "Tag": "宿"},
    {"Category": "左班", "Name": "呂培民", "Tag": "散"},
    {"Category": "左班", "Name": "廖友智", "Tag": "散"},
    {"Category": "左班", "Name": "陳怡民", "Tag": "宿"},
    {"Category": "左班", "Name": "洪靚茜", "Tag": "散"},
    {"Category": "左班", "Name": "吳枚芷", "Tag": "宿"},
    {"Category": "左班", "Name": "莊沛倫", "Tag": "宿"},
    {"Category": "左班", "Name": "李沿諭", "Tag": "宿"},
    {"Category": "左班", "Name": "簡俊昇", "Tag": "宿"},
    {"Category": "左班", "Name": "林冠中", "Tag": "宿"},
    {"Category": "左班", "Name": "范曉萱", "Tag": "散"},
    {"Category": "左班", "Name": "劉頂昱", "Tag": "宿"},
    {"Category": "左班", "Name": "劉正誼", "Tag": "宿"},
    {"Category": "左班", "Name": "林佳玄", "Tag": "散"},
    {"Category": "左班", "Name": "葉宗榮", "Tag": "宿"},
    {"Category": "左班", "Name": "溫亞晉", "Tag": "宿"},
    {"Category": "左班", "Name": "黃帷訓", "Tag": "宿"},
    {"Category": "右班", "Name": "徐偉閎", "Tag": "宿"},
    {"Category": "右班", "Name": "林松霆", "Tag": "宿"},
    {"Category": "右班", "Name": "陳泰均", "Tag": "宿"},
    {"Category": "右班", "Name": "蔡宗穎", "Tag": "宿"},
    {"Category": "右班", "Name": "黃泰洪", "Tag": "宿"},
    {"Category": "右班", "Name": "蔡詩濡", "Tag": "宿"},
    {"Category": "右班", "Name": "羅榆秀", "Tag": "宿"},
    {"Category": "右班", "Name": "李意婷", "Tag": "宿"},
    {"Category": "右班", "Name": "湯頂瑤", "Tag": "散"},
    {"Category": "右班", "Name": "曾夢婷", "Tag": "宿"},
    {"Category": "右班", "Name": "姜富議", "Tag": "宿"},
    {"Category": "右班", "Name": "毛品堯", "Tag": "散"},
    {"Category": "右班", "Name": "林興良", "Tag": "散"},
    {"Category": "右班", "Name": "傅奕翔", "Tag": "宿"},
    {"Category": "右班", "Name": "韓政叡", "Tag": "宿"},
    {"Category": "右班", "Name": "湯恩宇", "Tag": "散"},
    {"Category": "右班", "Name": "詹燦宇", "Tag": "散"},
    {"Category": "右班", "Name": "伍諾亞", "Tag": "散"},
    {"Category": "義務役", "Name": "林子祥", "Tag": "散"},
    {"Category": "義務役", "Name": "張育勝", "Tag": "散"},
    {"Category": "義務役", "Name": "夏文凱", "Tag": "散"},
    {"Category": "義務役", "Name": "張朕中", "Tag": "散"},
]

def get_taiwan_time():
    # 取得目前台灣時間 (不帶時區資訊，方便比對)
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).replace(tzinfo=None)

def get_greeting():
    hour = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).hour
    if 5 <= hour < 12: return "早安，新的一天開始了！☀️"
    elif 12 <= hour < 18: return "午安，休息一下吧！🍵"
    elif 18 <= hour < 22: return "晚安，辛苦了！🌙"
    else: return "夜深了，注意保暖喔！✨"

def load_data():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty or "Category" not in df.columns or "Name" not in df.columns:
            st.warning("⚠️ 資料庫初始化中...")
            init_df = pd.DataFrame(DEFAULT_ROSTER)
            for col in ["Incident_Reason", "Start_Time", "End_Time"]:
                init_df[col] = ""
            conn.update(data=init_df)
            return init_df
        return df.fillna("")
    except Exception as e:
        st.error(f"⚠️ 資料庫讀取失敗: {e}")
        return pd.DataFrame(columns=["Category", "Name", "Tag", "Incident_Reason", "Start_Time", "End_Time"])

def save_data(df):
    try:
        conn.update(data=df)
        st.toast("✅ 資料庫已更新", icon="☁️")
    except Exception as e:
        st.error(f"寫入失敗: {e}")

# 載入資料
raw_df = load_data()

# ==========================================
# 3. 側邊欄
# ==========================================
with st.sidebar:
    st.title("⚙️ 人員管理")
    st.write(f"時間：{datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%H:%M')}")
    st.divider()

    with st.expander("➕ 新增人員", expanded=False):
        with st.form("add_person_form"):
            new_cat = st.selectbox("類別", ["官員", "左班", "右班", "義務役"])
            new_name = st.text_input("姓名 (必填)")
            new_tag = st.selectbox("標籤", ["宿", "散", "無"])
            if st.form_submit_button("確認新增"):
                if new_name:
                    if "Name" in raw_df.columns and new_name in raw_df['Name'].values:
                        st.error("此姓名已存在！")
                    else:
                        new_row = pd.DataFrame([{
                            "Category": new_cat, "Name": new_name, "Tag": new_tag,
                            "Incident_Reason": "", "Start_Time": "", "End_Time": ""
                        }])
                        raw_df = pd.concat([raw_df, new_row], ignore_index=True)
                        save_data(raw_df)
                        st.success(f"已新增 {new_name}")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("請輸入姓名")
    
    st.divider()
    if not raw_df.empty:
        st.download_button("📥 下載備份", raw_df.to_csv(index=False).encode('utf-8-sig'), f"backup_{datetime.date.today()}.csv", "text/csv")
    
    with st.expander("🔴 危險操作"):
        if st.button("⚠️ 重置回預設名單"):
            default_df = pd.DataFrame(DEFAULT_ROSTER)
            for col in ["Incident_Reason", "Start_Time", "End_Time"]:
                default_df[col] = ""
            save_data(default_df)
            st.rerun()

def check_status_row(row):
    now = get_taiwan_time()
    reason = str(row.get('Incident_Reason', '')).strip()
    start_raw = row.get('Start_Time', '')
    end_raw = row.get('End_Time', '')

    if not reason or not str(start_raw).strip() or not str(end_raw).strip():
        return "camp", "在營", "🟢 在營"

    try:
        # ✨ 強力時間轉換 (相容字串、Excel格式、Timestamp)
        start = pd.to_datetime(start_raw, errors='coerce')
        end = pd.to_datetime(end_raw, errors='coerce')

        # 檢查是否為有效時間 (防止 NaT)
        if pd.isna(start) or pd.isna(end):
            return "camp", "在營", "🟢 在營"

        # 確保不帶時區，統一比對
        if start.tzinfo is not None: start = start.tz_localize(None)
        if end.tzinfo is not None: end = end.tz_localize(None)

        # 判斷狀態
        if start <= now <= end:
            return "leave", reason, f"🟡 {reason} ({start.strftime('%m/%d %H:%M')}~)"
        elif now < start:
             return "camp", "在營", f"🟢 在營 (預劃: {reason})"
    except: pass
    return "camp", "在營", "🟢 在營"

def parse_batch_input(text_input, current_df):
    if current_df.empty: return current_df, 0
    lines = text_input.strip().split('\n')
    updated_count = 0
    now = get_taiwan_time()
    current_year = now.year

    for line in lines:
        line = line.strip()
        if not line: continue
        found_name = None
        for name in current_df['Name'].values:
            if name in line:
                found_name = name
                break
        if not found_name: continue

        try:
            pattern = r"(\d{1,2})[./](\d{1,2})\s+(\d{4})\s*[-~至]?\s*(\d{1,2})[./](\d{1,2})\s+(\d{4})"
            match = re.search(pattern, line)
            start_dt, end_dt = None, None

            if match:
                m1, d1, t1, m2, d2, t2 = match.groups()
                y1 = current_year + 1 if (now.month >= 10 and int(m1) <= 3) else current_year
                y2 = current_year + 1 if (now.month >= 10 and int(m2) <= 3) else current_year
                start_dt = datetime.datetime.strptime(f"{y1}-{m1}-{d1} {t1}", "%Y-%m-%d %H%M")
                end_dt = datetime.datetime.strptime(f"{y2}-{m2}-{d2} {t2}", "%Y-%m-%d %H%M")
            else:
                short_match = re.search(r"\b(\d{4})\s*[-~]\s*(\d{4})\b", line)
                if short_match:
                    t1, t2 = short_match.groups()
                    d_today = now.date()
                    start_dt = datetime.datetime.strptime(f"{d_today} {t1}", "%Y-%m-%d %H%M")
                    end_dt = datetime.datetime.strptime(f"{d_today} {t2}", "%Y-%m-%d %H%M")
                    if end_dt < start_dt: end_dt += datetime.timedelta(days=1)
            
            if not start_dt or not end_dt: continue
            
            temp_line = line.replace(found_name, "")
            if match: temp_line = temp_line.replace(match.group(0), "")
            reason = re.sub(r'[ \t,，.\-~]+', '', temp_line).strip()
            if not reason: reason = "外散宿"

            idx = current_df[current_df['Name'] == found_name].index[0]
            current_df.at[idx, 'Incident_Reason'] = reason
            current_df.at[idx, 'Start_Time'] = start_dt.isoformat()
            current_df.at[idx, 'End_Time'] = end_dt.isoformat()
            updated_count += 1
        except: pass
    return current_df, updated_count

# ==========================================
# 4. 主頁面顯示
# ==========================================
st.title(get_greeting())
tab1, tab2 = st.tabs(["📋 點名簿", "📝 批次作業"])

with tab1:
    col_refresh, _ = st.columns([1, 3])
    if col_refresh.button("🔄 刷新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    if raw_df.empty:
        st.warning("目前沒有資料，請檢查雲端連線或按下側邊欄的重置按鈕。")
    else:
        total_should = len(raw_df)
        current_absent = 0
        for _, row in raw_df.iterrows():
            if check_status_row(row)[0] == "leave": current_absent += 1

        st.progress((total_should - current_absent) / total_should if total_should > 0 else 0)
        st.caption(f"實到: {total_should - current_absent} / 應到: {total_should} (休假: {current_absent})")

        cats = ["官員", "左班", "右班", "義務役"]
        
        for category in cats:
            if "Category" in raw_df.columns:
                group_df = raw_df[raw_df['Category'] == category]
            else:
                group_df = pd.DataFrame()
                
            if group_df.empty: continue
            
            st.subheader(f"🔹 {category}")
            for i, row in group_df.iterrows():
                status_code, reason, status_text = check_status_row(row)
                css_class = "status-leave" if status_code == "leave" else "status-camp"
                tag_str = f'<span class="tag-badge">{row["Tag"]}</span>' if row.get('Tag') else ''
                
                st.markdown(f"""
                <div class="person-card {css_class}">
                    <div class="card-header">
                        <div class="card-name">{row['Name']} {tag_str}</div>
                        <div style="font-size:1.2rem;">{'🏠' if status_code=='leave' else '🌲'}</div>
                    </div>
                    <div class="card-details">{status_text}</div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander(f"⚙️ 管理 {row['Name']}"):
                    c1, c2 = st.columns(2)
                    if c1.button("歸隊", key=f"cls_{row['Name']}", use_container_width=True):
                        real_idx = raw_df[raw_df['Name'] == row['Name']].index[0]
                        raw_df.at[real_idx, 'Incident_Reason'] = ""
                        raw_df.at[real_idx, 'Start_Time'] = ""
                        raw_df.at[real_idx, 'End_Time'] = ""
                        save_data(raw_df)
                        st.rerun()
                    
                    if c2.button("🗑️ 刪除", key=f"del_{row['Name']}", type="primary", use_container_width=True):
                        raw_df = raw_df[raw_df['Name'] != row['Name']]
                        save_data(raw_df)
                        st.success(f"已刪除 {row['Name']}")
                        time.sleep(1)
                        st.rerun()

with tab2:
    st.info("貼上假單範例：卓士傑 11/20 1800 - 11/21 0730")
    batch_text = st.text_area("假單內容", height=150)
    if st.button("🚀 更新假單", type="primary", use_container_width=True):
        if raw_df.empty:
            st.error("資料庫為空，無法更新")
        else:
            new_df, count = parse_batch_input(batch_text, raw_df.copy())
            if count > 0:
                save_data(new_df)
                st.success(f"成功更新 {count} 筆！")
                time.sleep(1)
                st.rerun()
            else:
                st.error("無資料更新，請檢查姓名或格式")
