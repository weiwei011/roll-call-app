import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import datetime
import re
import time
from collections import Counter

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
# 1. 頁面與「深色護眼」樣式設定
# ==========================================
st.set_page_config(page_title="部隊電子點名簿", layout="wide", page_icon="📝")

if not check_password():
    st.stop()

# ✨ 這裡更換了全新的 CSS 配色方案 (深色護眼模式)
st.markdown("""
    <style>
    /* 全局背景：深碳黑/夜間模式 */
    .stApp { background-color: #121212; color: #E0E0E0; }
    
    /* 標題文字顏色：亮灰白 */
    h1, h2, h3 { font-family: '微軟正黑體', sans-serif; color: #FFFFFF !important; }
    
    /* 卡片設計：深鐵灰背景 */
    .person-card { 
        padding: 16px; 
        border-radius: 16px; 
        margin-bottom: 15px; 
        background-color: #1E1E1E; 
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
        border: 1px solid #333333; 
        transition: transform 0.2s;
    }
    .person-card:hover { transform: translateY(-3px); border-color: #555; }
    
    /* 狀態標籤顏色 - 螢光綠與螢光黃，但在黑底上要柔和一點 */
    .status-camp { border-left: 5px solid #66BB6A; } /* 柔和綠 */
    .status-leave { border-left: 5px solid #FFA726; } /* 柔和橘 */
    
    /* 名字與圖示 */
    .card-header { display: flex; justify-content: space-between; align-items: center; }
    .card-name { font-size: 1.3rem; font-weight: 700; color: #FFFFFF; letter-spacing: 1px; }
    .card-details { font-size: 0.95rem; color: #AAAAAA; margin-top: 6px; font-weight: 500; }
    
    /* 小標籤樣式 */
    .tag-badge { 
        font-size: 0.75rem; padding: 4px 10px; border-radius: 12px; 
        background-color: #333333; color: #CCCCCC; margin-left: 8px;
        vertical-align: middle; border: 1px solid #444;
    }
    
    /* 統計看板樣式 (深色版) */
    .stats-container {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        margin-bottom: 20px;
        border: 1px solid #333;
    }
    .stats-title { font-size: 1.1rem; color: #FFF; font-weight: bold; margin-bottom: 10px; }
    .stats-grid { display: flex; gap: 15px; flex-wrap: wrap; }
    .stat-item { 
        background-color: #2D2D2D; 
        padding: 8px 15px; 
        border-radius: 10px; 
        color: #DDDDDD;
        font-size: 0.9rem;
        border: 1px solid #444;
    }
    
    /* 按鈕優化 (深色底) */
    .stButton button { 
        border-radius: 10px; 
        background-color: #2D2D2D;
        color: #EEE;
        border: 1px solid #444;
    }
    .stButton button:hover {
        border-color: #66BB6A;
        color: #66BB6A;
    }
    
    /* 進度條顏色 */
    .stProgress > div > div > div > div {
        background-color: #66BB6A;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 資料庫連線
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
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).replace(tzinfo=None)

def get_greeting():
    hour = get_taiwan_time().hour
    if 5 <= hour < 12: return "早安，新的一天開始了！☀️"
    elif 12 <= hour < 18: return "午安，休息一下吧！🍵"
    elif 18 <= hour < 22: return "晚安，辛苦了！🌙"
    else: return "夜深了，注意保暖喔！✨"

def load_data():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty or "Category" not in df.columns or "Name" not in df.columns:
            init_df = pd.DataFrame(DEFAULT_ROSTER)
            for col in ["Incident_Reason", "Start_Time", "End_Time"]:
                init_df[col] = ""
            conn.update(data=init_df)
            return init_df
        return df.fillna("")
    except:
        return pd.DataFrame(columns=["Category", "Name", "Tag", "Incident_Reason", "Start_Time", "End_Time"])

def save_data(df):
    try:
        conn.update(data=df)
        st.toast("✅ 更新成功", icon="☁️")
    except Exception as e:
        st.error(f"寫入失敗: {e}")

raw_df = load_data()

# ==========================================
# 3. 側邊欄
# ==========================================
with st.sidebar:
    st.title("⚙️ 設定")
    st.caption(f"現在時間：{get_taiwan_time().strftime('%H:%M')}")
    st.divider()

    with st.expander("➕ 新增人員"):
        with st.form("add_person_form"):
            new_cat = st.selectbox("類別", ["官員", "左班", "右班", "義務役"])
            new_name = st.text_input("姓名")
            new_tag = st.selectbox("標籤", ["宿", "散", "無"])
            if st.form_submit_button("新增"):
                if new_name and "Name" in raw_df.columns:
                    if new_name not in raw_df['Name'].values:
                        new_row = pd.DataFrame([{"Category": new_cat, "Name": new_name, "Tag": new_tag, "Incident_Reason": "", "Start_Time": "", "End_Time": ""}])
                        raw_df = pd.concat([raw_df, new_row], ignore_index=True)
                        save_data(raw_df)
                        st.rerun()
    
    st.divider()
    if not raw_df.empty:
        st.download_button("📥 下載報表", raw_df.to_csv(index=False).encode('utf-8-sig'), f"roster_{datetime.date.today()}.csv", "text/csv")
    
    with st.expander("🔴 危險操作"):
        if st.button("⚠️ 重置全部資料"):
            default_df = pd.DataFrame(DEFAULT_ROSTER)
            for col in ["Incident_Reason", "Start_Time", "End_Time"]: default_df[col] = ""
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
        start = pd.to_datetime(start_raw, errors='coerce')
        end = pd.to_datetime(end_raw, errors='coerce')
        if pd.isna(start) or pd.isna(end): return "camp", "在營", "🟢 在營"
        if start.tzinfo is not None: start = start.tz_localize(None)
        if end.tzinfo is not None: end = end.tz_localize(None)

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
# 4. 主頁面與統計儀表板 (全新設計)
# ==========================================
st.title(get_greeting())
tab1, tab2 = st.tabs(["📋 點名簿", "📝 批次作業"])

with tab1:
    col_refresh, _ = st.columns([1, 3])
    if col_refresh.button("🔄 刷新狀態", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if not raw_df.empty:
        # --- 📊 全新統計邏輯 ---
        total_should = len(raw_df)
        leave_list = []
        
        for _, row in raw_df.iterrows():
            status, reason, _ = check_status_row(row)
            if status == "leave":
                leave_list.append(reason)
        
        current_absent = len(leave_list)
        current_present = total_should - current_absent
        reason_counts = Counter(leave_list)
        
        # --- 顯示深色版統計看板 ---
        st.markdown(f"""
        <div class="stats-container">
            <div class="stats-title">📊 即時現員統計</div>
            <div style="margin-bottom: 15px; font-size: 1rem; color: #DDD;">
                <span style="color:#66BB6A; font-weight:bold;">🌲 實到：{current_present}</span> &nbsp;&nbsp;|&nbsp;&nbsp; 
                <span style="color:#FFA726; font-weight:bold;">🏠 休假：{current_absent}</span> &nbsp;&nbsp;|&nbsp;&nbsp; 
                <span style="color:#888;">應到：{total_should}</span>
            </div>
            <div class="stats-title" style="font-size: 0.95rem; margin-top:10px; color:#CCC;">📌 休假明細：</div>
            <div class="stats-grid">
                {''.join([f'<div class="stat-item">{k}: <b>{v}</b> 員</div>' for k, v in reason_counts.items()]) if leave_list else '<div class="stat-item">目前全員在營</div>'}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- 人員卡片列表 ---
        cats = ["官員", "左班", "右班", "義務役"]
        for category in cats:
            if "Category" in raw_df.columns:
                group_df = raw_df[raw_df['Category'] == category]
            else: group_df = pd.DataFrame()
            if group_df.empty: continue
            
            st.markdown(f"### {category}")
            for i, row in group_df.iterrows():
                status_code, reason, status_text = check_status_row(row)
                css_class = "status-leave" if status_code == "leave" else "status-camp"
                tag_str = f'<span class="tag-badge">{row["Tag"]}</span>' if row.get('Tag') else ''
                
                st.markdown(f"""
                <div class="person-card {css_class}">
                    <div class="card-header">
                        <div class="card-name">{row['Name']} {tag_str}</div>
                        <div style="font-size:1.4rem;">{'🏠' if status_code=='leave' else '🌲'}</div>
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
                        st.rerun()

with tab2:
    st.info("範例：卓士傑 11/20 1800 - 11/21 0730")
    batch_text = st.text_area("批次輸入", height=150)
    if st.button("🚀 更新", type="primary", use_container_width=True):
        if raw_df.empty: st.error("無資料庫")
        else:
            new_df, count = parse_batch_input(batch_text, raw_df.copy())
            if count > 0:
                save_data(new_df)
                st.success(f"已更新 {count} 筆")
                time.sleep(1)
                st.rerun()
            else: st.error("無更新")
