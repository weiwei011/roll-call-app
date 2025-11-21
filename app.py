import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import datetime
import re
import time

# ==========================================
# 🔐 安全登入系統 (新增功能)
# ==========================================
# 設定你的登入密碼 (請修改這裡的 123456)
LOGIN_PASSWORD = "你的部隊專用密碼"

def check_password():
    """Returns `True` if the user had a correct password."""
    def password_entered():
        if st.session_state["password"] == LOGIN_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input("🔒 請輸入通行碼", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input again.
        st.text_input("🔒 請輸入通行碼", type="password", on_change=password_entered, key="password")
        st.error("🚫 密碼錯誤")
        return False
    else:
        # Password correct.
        return True

# ==========================================
# 1. 頁面與樣式設定
# ==========================================
st.set_page_config(page_title="部隊電子點名簿", layout="wide", page_icon="📝")

# ⚠️ 啟動密碼檢查！如果密碼不對，程式就會停在這裡，不會往下執行
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
    .person-card:hover { transform: translateY(-2px); border-color: #666; }
    .status-camp { border-left: 6px solid #a5d6a7; }
    .status-leave { border-left: 6px solid #ffcc80; }
    .card-header { display: flex; justify-content: space-between; align-items: center; }
    .card-name { font-size: 1.3rem; font-weight: 600; color: #fff; letter-spacing: 1px; }
    .card-details { font-size: 0.95rem; color: #bbb; margin-top: 4px; }
    .tag-badge { 
        font-size: 0.7rem; padding: 3px 8px; border-radius: 10px; 
        background-color: #4a4d52; color: #ddd; margin-left: 8px; vertical-align: middle;
    }
    #MainMenu {visibility: hidden;} header {visibility: hidden;}
    .stButton button { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# ... (以下內容保持不變，從 conn = st.connection... 開始)
# ==========================================
# 2. 資料庫連線與基礎函式
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def get_taiwan_time():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))

def get_greeting():
    hour = get_taiwan_time().hour
    if 5 <= hour < 12: return "早安，新的一天開始了！☀️"
    elif 12 <= hour < 18: return "午安，休息一下吧！🍵"
    elif 18 <= hour < 22: return "晚安，辛苦了！🌙"
    else: return "夜深了，注意保暖喔！✨"

def load_data():
    try:
        df = conn.read(worksheet="Sheet1", ttl=0)
        return df
    except Exception as e:
        st.error(f"⚠️ 資料庫讀取錯誤: {e}")
        return pd.DataFrame()

def save_data(df):
    try:
        conn.update(worksheet="Sheet1", data=df)
        st.toast("✅ 資料已雲端同步", icon="☁️")
    except Exception as e:
        st.error(f"寫入失敗: {e}")

# 載入資料
raw_df = load_data()

# ==========================================
# 3. 自動初始化 (將你的名單內建於此)
# ==========================================
# 如果資料庫是空的 (或沒有 Name 欄位)，就會執行這一段
if raw_df is None or raw_df.empty or "Name" not in raw_df.columns:
    st.warning("偵測到資料庫為空，正在寫入完整部隊名單，請稍候...")
    
    # 這裡是你剛剛提供的完整名單
    initial_roster = [
        # 官員
        {"Category": "官員", "Name": "魏俊丞", "Tag": "宿"},
        {"Category": "官員", "Name": "曾小容", "Tag": "宿"},
        {"Category": "官員", "Name": "馬翔麟", "Tag": "宿"},
        # 左班
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
        # 右班
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
        # 義務役
        {"Category": "義務役", "Name": "林子祥", "Tag": "散"},
        {"Category": "義務役", "Name": "張育勝", "Tag": "散"},
        {"Category": "義務役", "Name": "夏文凱", "Tag": "散"},
        {"Category": "義務役", "Name": "張朕中", "Tag": "散"},
    ]
    
    raw_df = pd.DataFrame(initial_roster)
    # 補上時間欄位
    for col in ["Incident_Reason", "Start_Time", "End_Time"]:
        raw_df[col] = ""
        
    save_data(raw_df)
    st.success("名單建立完成！正在重整頁面...")
    time.sleep(2)
    st.rerun()

# 欄位檢查與補全 (防止崩潰)
required_cols = ["Category", "Name", "Tag", "Incident_Reason", "Start_Time", "End_Time"]
for col in required_cols:
    if col not in raw_df.columns: raw_df[col] = ""
raw_df = raw_df.fillna("")

# ==========================================
# 4. 側邊欄與核心邏輯
# ==========================================
with st.sidebar:
    st.title("⚙️ 系統管理")
    st.write(f"時間：{get_taiwan_time().strftime('%H:%M')}")
    st.divider()
    st.download_button("📥 下載備份", raw_df.to_csv(index=False).encode('utf-8-sig'), f"backup_{datetime.date.today()}.csv", "text/csv")
    
    uploaded_file = st.file_uploader("匯入舊資料", type=["csv"])
    if uploaded_file and st.button("確認還原"):
        try:
            uploaded_df = pd.read_csv(uploaded_file).fillna("")
            save_data(uploaded_df)
            st.rerun()
        except: st.error("格式錯誤")

    with st.expander("🛑 刪除所有資料"):
        if st.button("確認清空"):
            save_data(pd.DataFrame(columns=required_cols))
            st.rerun()

def check_status_row(row):
    now = get_taiwan_time()
    reason, start_str, end_str = str(row['Incident_Reason']).strip(), str(row['Start_Time']).strip(), str(row['End_Time']).strip()
    if not reason or not start_str or not end_str: return "camp", "在營", "🟢 在營"
    try:
        start = datetime.datetime.fromisoformat(start_str)
        end = datetime.datetime.fromisoformat(end_str)
        if start.tzinfo is None: start = start.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
        if end.tzinfo is None: end = end.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
        if start <= now <= end:
            return "leave", reason, f"🟡 {reason} ({start.strftime('%m/%d %H:%M')}~)"
        elif now < start:
             return "camp", "在營", f"🟢 在營 (預劃: {reason})"
    except: pass
    return "camp", "在營", "🟢 在營"

def parse_batch_input(text_input, current_df):
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
            # 格式 11/20 1600
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

            start_dt = start_dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
            end_dt = end_dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
            
            idx = current_df[current_df['Name'] == found_name].index[0]
            current_df.at[idx, 'Incident_Reason'] = reason
            current_df.at[idx, 'Start_Time'] = start_dt.isoformat()
            current_df.at[idx, 'End_Time'] = end_dt.isoformat()
            updated_count += 1
        except: pass
    return current_df, updated_count

# ==========================================
# 5. 主頁面
# ==========================================
st.title(get_greeting())
tab1, tab2 = st.tabs(["📋 點名簿", "📝 批次作業"])

with tab1:
    col_refresh, _ = st.columns([1, 3])
    if col_refresh.button("🔄 刷新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    total_should = len(raw_df)
    current_absent = 0
    for _, row in raw_df.iterrows():
        if check_status_row(row)[0] == "leave": current_absent += 1

    st.progress((total_should - current_absent) / total_should if total_should > 0 else 0)
    st.caption(f"實到: {total_should - current_absent} / 應到: {total_should} (休假: {current_absent})")

    # 依照你的要求排序類別：官員 -> 左班 -> 右班 -> 義務役
    cats = ["官員", "左班", "右班", "義務役"]
    
    for category in cats:
        group_df = raw_df[raw_df['Category'] == category]
        if group_df.empty: continue
        
        st.subheader(f"🔹 {category}")
        for i, row in group_df.iterrows():
            status_code, reason, status_text = check_status_row(row)
            css_class = "status-leave" if status_code == "leave" else "status-camp"
            tag_str = f'<span class="tag-badge">{row["Tag"]}</span>' if row['Tag'] != '無' else ''
            
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
                if c2.button("刪除", key=f"del_{row['Name']}", type="primary", use_container_width=True):
                    raw_df = raw_df[raw_df['Name'] != row['Name']]
                    save_data(raw_df)
                    st.rerun()

with tab2:
    st.info("貼上假單範例：卓士傑 11/20 1800 - 11/21 0730")
    batch_text = st.text_area("假單內容", height=150)
    if st.button("🚀 更新假單", type="primary", use_container_width=True):
        new_df, count = parse_batch_input(batch_text, raw_df.copy())
        if count > 0:
            save_data(new_df)
            st.success(f"成功更新 {count} 筆！")
            time.sleep(1)
            st.rerun()
        else:
            st.error("無資料更新，請檢查姓名或格式")
