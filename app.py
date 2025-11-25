import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import datetime
import re
import time
import json
from collections import Counter

# ==========================================
# 🔐 安全登入系統
# ==========================================
LOGIN_PASSWORD = "1234"  # <--- 密碼

def check_password():
    """簡單的密碼驗證機制"""
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
# 1. 頁面設定與暖色夜間 CSS
# ==========================================
st.set_page_config(page_title="部隊電子點名簿 Pro", layout="wide", page_icon="📝")

st.markdown("""
    <style>
    /* 全局背景與字體顏色 */
    .stApp { background-color: #1C1B1A; color: #E3DED5; }
    
    /* 側邊欄優化 */
    section[data-testid="stSidebar"] {
        background-color: #23201D !important;
        border-right: 1px solid #3E3935;
    }
    section[data-testid="stSidebar"] * { color: #E0E0E0 !important; }
    
    /* 輸入框優化 */
    div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
        background-color: #33302C !important;
        border-color: #666 !important;
        color: #F0ECE4 !important;
    }
    textarea { background-color: #33302C !important; color: #F0ECE4 !important; }
    
    /* 人員卡片設計 */
    .person-card { 
        padding: 18px; 
        border-radius: 18px; 
        margin-bottom: 16px; 
        background-color: #2D2A26;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        border: 1px solid #3E3935; 
        transition: transform 0.2s;
    }
    .person-card:hover { transform: translateY(-2px); border-color: #D99E6B; }
    
    /* 狀態顏色條 */
    .status-camp { border-left: 6px solid #8FBC8F; } 
    .status-leave { border-left: 6px solid #D99E6B; } 
    
    /* 卡片內容排版 */
    .card-header { display: flex; justify-content: space-between; align-items: center; }
    .card-name { font-size: 1.35rem; font-weight: 800; color: #FFF; }
    .card-details { font-size: 1rem; color: #C2B8AD; margin-top: 8px; font-weight: 500; }
    
    /* 標籤小圖示 */
    .tag-badge { 
        font-size: 0.8rem; padding: 4px 10px; border-radius: 12px; 
        background-color: #423D38; color: #E3DED5; margin-left: 10px;
        border: 1px solid #59524C; font-weight: bold;
    }
    
    /* 統計看板 */
    .stats-container {
        background-color: #2D2A26; padding: 22px; border-radius: 18px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4); margin-bottom: 25px;
        border: 1px solid #3E3935;
    }
    .stats-grid { display: flex; gap: 15px; flex-wrap: wrap; }
    .stat-item { 
        background-color: #3A3632; padding: 10px 18px; border-radius: 12px; 
        color: #E0E0E0; font-size: 0.95rem; font-weight: 500; border: 1px solid #666;
    }
    
    /* 按鈕樣式 */
    .stButton button { border-radius: 12px !important; font-weight: 700 !important; }
    
    /* 左上角箭頭 (特殊客製) */
    [data-testid="stSidebarCollapsedControl"] {
        background-color: #2D2A26 !important; border: 2px solid #D99E6B !important;
        border-radius: 12px !important; color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

if not check_password():
    st.stop()

# ==========================================
# 2. 資料庫連線與處理函式
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

# 範例名單 (僅在資料庫完全為空時使用)
DEFAULT_ROSTER = [
    {"Category": "官員", "Name": "魏俊丞", "Tag": "宿"},
    {"Category": "左班", "Name": "卓士傑", "Tag": "宿"},
    {"Category": "左班", "Name": "呂培民", "Tag": "散"},
    {"Category": "右班", "Name": "徐偉閎", "Tag": "宿"},
    {"Category": "右班", "Name": "湯頂瑤", "Tag": "散"},
    {"Category": "義務役", "Name": "林子祥", "Tag": "散"},
]

def get_taiwan_time():
    """取得台灣時間 (UTC+8)"""
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).replace(tzinfo=None)

def load_data():
    """讀取資料，並具備自動修復欄位的功能"""
    try:
        df = conn.read(ttl=0)
        
        # 1. 若資料庫全空，載入預設值
        if df is None or df.empty or "Name" not in df.columns:
            df = pd.DataFrame(DEFAULT_ROSTER)
            df["Schedule"] = "[]"
            conn.update(data=df)
            return df
        
        # 2. 自動升級：若缺少 Schedule 欄位，自動補上 (保護舊資料)
        if "Schedule" not in df.columns:
            df["Schedule"] = "[]"
            
        # 3. 確保有 Tag 欄位
        if "Tag" not in df.columns:
            df["Tag"] = "無"
            
        return df.fillna("")
    except Exception as e:
        st.error(f"⚠️ 資料庫讀取錯誤: {e}")
        return pd.DataFrame(columns=["Category", "Name", "Tag", "Schedule"])

def save_data(df):
    """回寫資料到 Google Sheets"""
    try:
        conn.update(data=df)
        st.toast("✅ 資料已同步雲端", icon="☁️")
    except Exception as e:
        st.error(f"寫入失敗: {e}")

raw_df = load_data()

# ------------------------------------------
# 核心邏輯 A：解析人員狀態 (Status)
# ------------------------------------------
def get_person_status(schedule_json):
    """
    解析 JSON 排程，回傳：(狀態代碼, 原因, 顯示文字, 當前事件物件)
    """
    now = get_taiwan_time()
    try:
        events = json.loads(str(schedule_json))
        if not isinstance(events, list): events = []
    except:
        events = []
    
    # 1. 檢查「現在」是否在某個事件中
    current_event = None
    for event in events:
        try:
            s = datetime.datetime.fromisoformat(event['start'])
            e = datetime.datetime.fromisoformat(event['end'])
            if s <= now <= e:
                current_event = event
                break
        except: continue
        
    if current_event:
        s_str = datetime.datetime.fromisoformat(current_event['start']).strftime('%m/%d %H:%M')
        reason = current_event.get('reason', '休假')
        return "leave", reason, f"🟡 {reason} ({s_str}~)", current_event

    # 2. 若現在沒事，找「最近的未來」預告
    future_event = None
    min_diff = float('inf')
    for event in events:
        try:
            s = datetime.datetime.fromisoformat(event['start'])
            if s > now:
                diff = (s - now).total_seconds()
                if diff < min_diff:
                    min_diff = diff
                    future_event = event
        except: continue
        
    if future_event:
        s_str = datetime.datetime.fromisoformat(future_event['start']).strftime('%m/%d %H:%M')
        reason = future_event.get('reason', '預劃')
        return "camp", "在營", f"🟢 在營 (下個休假: {s_str} {reason})", None
        
    return "camp", "在營", "🟢 在營", None

# ------------------------------------------
# 核心邏輯 B：多重事故批次解析
# ------------------------------------------
def parse_multi_incident_input(text_input, current_df):
    """解析 名字+多行時間 的輸入格式"""
    lines = text_input.strip().split('\n')
    updated_count = 0
    now = get_taiwan_time()
    current_year = now.year
    
    current_target_name = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # 1. 判斷是否為名字行
        is_name_line = False
        found_name_in_line = None
        for name in current_df['Name'].values:
            if line == name or line.startswith(name): 
                found_name_in_line = name
                is_name_line = True
                break
        
        if is_name_line:
            current_target_name = found_name_in_line
            # 去除名字，若後面還有字則繼續解析
            line = line.replace(current_target_name, "").strip()
            if not line: continue 

        if not current_target_name: continue

        # 2. 解析時間 (支援 11/19 1600-11/21 1600 理由)
        pattern = r"(\d{1,2})[./](\d{1,2})\s*(\d{4})\s*[-~至]\s*(\d{1,2})[./](\d{1,2})\s*(\d{4})(.*)"
        match = re.search(pattern, line)
        
        if match:
            m1, d1, t1, m2, d2, t2, reason_raw = match.groups()
            
            # 跨年邏輯
            y1 = current_year + 1 if (now.month >= 11 and int(m1) <= 2) else current_year
            y2 = current_year + 1 if (now.month >= 11 and int(m2) <= 2) else current_year
            
            try:
                start_dt = datetime.datetime.strptime(f"{y1}-{m1}-{d1} {t1}", "%Y-%m-%d %H%M")
                end_dt = datetime.datetime.strptime(f"{y2}-{m2}-{d2} {t2}", "%Y-%m-%d %H%M")
                
                if end_dt < start_dt: end_dt = end_dt.replace(year=end_dt.year + 1)

                reason = reason_raw.strip()
                if not reason: reason = "休假"
                
                # 寫入 Schedule
                idx = current_df[current_df['Name'] == current_target_name].index[0]
                try:
                    old_schedule = json.loads(current_df.at[idx, 'Schedule'])
                    if not isinstance(old_schedule, list): old_schedule = []
                except: old_schedule = []
                
                new_event = {
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    "reason": reason,
                    "created_at": now.isoformat()
                }
                
                # 簡單去重
                is_duplicate = False
                for evt in old_schedule:
                    if evt['start'] == new_event['start'] and evt['end'] == new_event['end']:
                        is_duplicate = True
                
                if not is_duplicate:
                    old_schedule.append(new_event)
                    old_schedule.sort(key=lambda x: x['start'])
                    current_df.at[idx, 'Schedule'] = json.dumps(old_schedule, ensure_ascii=False)
                    updated_count += 1
            except: pass
                
    return current_df, updated_count

# ------------------------------------------
# 核心邏輯 C：智慧放假 (支援多選疊加)
# ------------------------------------------
def apply_routine_leave(target_categories_list, current_df):
    """
    針對選定的「多個類別」 (list)，依照標籤自動給假：
    Tag="散" -> 當日 1700 - 2359
    Tag="宿" -> 當日 1700 - 隔日 0730
    """
    count = 0
    now = get_taiwan_time()
    today_date = now.date()
    
    start_time = datetime.datetime.combine(today_date, datetime.time(17, 0)) # 17:00
    
    for i, row in current_df.iterrows():
        # 1. 檢查是否在選定名單內
        if row['Category'] not in target_categories_list:
            continue
        
        # 2. 判斷 Tag
        tag = row.get('Tag', '')
        if tag == '散':
            end_time = datetime.datetime.combine(today_date, datetime.time(23, 59))
            reason = "外散"
        elif tag == '宿':
            tomorrow = today_date + datetime.timedelta(days=1)
            end_time = datetime.datetime.combine(tomorrow, datetime.time(7, 30))
            reason = "外宿"
        else:
            continue

        # 3. 衝突檢查
        try:
            schedule = json.loads(row['Schedule'])
            if not isinstance(schedule, list): schedule = []
        except: schedule = []
        
        is_free = True
        for event in schedule:
            e_start = datetime.datetime.fromisoformat(event['start'])
            e_end = datetime.datetime.fromisoformat(event['end'])
            # 若時間重疊則不放
            if max(start_time, e_start) < min(end_time, e_end):
                is_free = False
                break
        
        if is_free:
            new_event = {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "reason": reason,
                "created_at": now.isoformat()
            }
            schedule.append(new_event)
            schedule.sort(key=lambda x: x['start'])
            current_df.at[i, 'Schedule'] = json.dumps(schedule, ensure_ascii=False)
            count += 1
            
    return current_df, count

def apply_batch_leave_manual(categories, start_dt, end_dt, reason, current_df):
    """手動自訂時間的放假 (給 '進階功能' 用)"""
    count = 0
    now = get_taiwan_time()
    
    for i, row in current_df.iterrows():
        if row['Category'] not in categories: continue
        try:
            schedule = json.loads(row['Schedule'])
            if not isinstance(schedule, list): schedule = []
        except: schedule = []
        
        is_free = True
        for event in schedule:
            e_start = datetime.datetime.fromisoformat(event['start'])
            e_end = datetime.datetime.fromisoformat(event['end'])
            if max(start_dt, e_start) < min(end_dt, e_end):
                is_free = False
                break
        
        if is_free:
            new_event = {"start": start_dt.isoformat(), "end": end_dt.isoformat(), "reason": reason, "created_at": now.isoformat()}
            schedule.append(new_event)
            schedule.sort(key=lambda x: x['start'])
            current_df.at[i, 'Schedule'] = json.dumps(schedule, ensure_ascii=False)
            count += 1
    return current_df, count

# ==========================================
# 3. 主畫面 UI
# ==========================================
st.title(f"☀️ 部隊點名簿 ({get_taiwan_time().strftime('%H:%M')})")

tab1, tab2, tab3 = st.tabs(["📋 現況總覽", "✍️ 批次輸入事故", "🚀 智慧一鍵放假"])

# --- Tab 1: 總覽與統計 ---
with tab1:
    col_refresh, _ = st.columns([1, 4])
    if col_refresh.button("🔄 刷新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if not raw_df.empty:
        # 統計
        total_should = len(raw_df)
        leave_reasons = []
        left_conscript_leave_count = 0
        
        for _, row in raw_df.iterrows():
            status, reason, _, _ = get_person_status(row['Schedule'])
            if status == "leave":
                leave_reasons.append(reason)
                # 統計左班+義務役的休假數
                if row['Category'] in ["左班", "義務役"]:
                    left_conscript_leave_count += 1
        
        current_absent = len(leave_reasons)
        current_present = total_should - current_absent
        reason_counts = Counter(leave_reasons)
        
        # 統計看板
        st.markdown(f"""
        <div class="stats-container">
            <div class="stats-title">📊 即時現員統計</div>
            <div style="margin-bottom: 15px; font-size: 1rem; color: #D6CEC3;">
                <span style="color:#8FBC8F; font-weight:bold;">🌲 實到：{current_present}</span> &nbsp;|&nbsp; 
                <span style="color:#D99E6B; font-weight:bold;">🏠 休假總數：{current_absent}</span>
            </div>
            <div style="background:#4A4540; padding:8px; border-radius:8px; margin-bottom:10px; border:1px solid #D99E6B;">
                🔥 <b>左班+義務役 休假人數：{left_conscript_leave_count} 員</b>
            </div>
            <div class="stats-grid">
                {''.join([f'<div class="stat-item">{k}: <b>{v}</b></div>' for k, v in reason_counts.items()])}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 人員卡片
        cats = ["官員", "左班", "右班", "義務役"]
        for category in cats:
            group_df = raw_df[raw_df['Category'] == category]
            if group_df.empty: continue
            
            st.markdown(f"### {category}")
            cols = st.columns(3)
            for i, (idx, row) in enumerate(group_df.iterrows()):
                status_code, reason, status_text, curr_evt = get_person_status(row['Schedule'])
                css_class = "status-leave" if status_code == "leave" else "status-camp"
                
                with cols[i % 3]:
                    st.markdown(f"""
                    <div class="person-card {css_class}">
                        <div class="card-header">
                            <div class="card-name">{row['Name']} <span class="tag-badge">{row.get('Tag','')}</span></div>
                            <div style="font-size:1.4rem;">{'🏠' if status_code=='leave' else '🌲'}</div>
                        </div>
                        <div class="card-details">{status_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.popover(f"管理 {row['Name']}"):
                        st.write(f"**{row['Name']} 的行程**")
                        try:
                            schedule = json.loads(row['Schedule'])
                            if st.button("🧹 清除過期行程", key=f"cl_{idx}"):
                                new_sched = [e for e in schedule if datetime.datetime.fromisoformat(e['end']) > get_taiwan_time()]
                                raw_df.at[idx, 'Schedule'] = json.dumps(new_sched)
                                save_data(raw_df)
                                st.rerun()
                            
                            if not schedule: st.info("無行程")
                            for s_idx, evt in enumerate(schedule):
                                s_t = datetime.datetime.fromisoformat(evt['start']).strftime('%m/%d %H:%M')
                                e_t = datetime.datetime.fromisoformat(evt['end']).strftime('%m/%d %H:%M')
                                c1, c2 = st.columns([3, 1])
                                c1.text(f"{s_t}~{e_t}\n{evt['reason']}")
                                if c2.button("刪", key=f"del_{idx}_{s_idx}"):
                                    schedule.pop(s_idx)
                                    raw_df.at[idx, 'Schedule'] = json.dumps(schedule)
                                    save_data(raw_df)
                                    st.rerun()
                        except: st.error("行程資料異常")

# --- Tab 2: 批次輸入 ---
with tab2:
    st.info("""
    **💡 批次輸入說明**
    輸入姓名後換行，接著輸入多行時間。系統會自動解析。
    
    **範例：**
    曾夢婷
    11/19 1600-11/21 1600 慰休
    11/24 0730-11/25 0730 補假
    
    林子祥
    11/20 1800-11/21 0730 外散
    """)
    batch_text = st.text_area("在此貼上排程", height=300)
    
    if st.button("🚀 執行批次更新", type="primary"):
        if raw_df.empty: st.error("無資料")
        else:
            new_df, count = parse_multi_incident_input(batch_text, raw_df.copy())
            if count > 0:
                save_data(new_df)
                st.success(f"已新增 {count} 筆行程！")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("無有效更新 (請檢查格式)")

# --- Tab 3: 智慧放假 (疊加版) ---
with tab3:
    st.header("🚀 智慧一鍵放假 (外散/宿)")
    st.info("💡 說明：勾選要放假的群組，系統會依據人員標籤 (散/宿) 自動設定今日 17:00 起的假單。")
    
    today_str = datetime.date.today().strftime("%m/%d")
    st.markdown(f"""
    <div style="background-color:#2D2A26; padding:15px; border-radius:10px; border:1px solid #555; margin-bottom:20px;">
        <div style="color:#C2B8AD; font-size:0.9rem;">📅 <b>今日 ({today_str}) 規則：</b></div>
        <ul style="margin-bottom:0; color:#E3DED5;">
            <li>🏷️ <b>標籤 [散]</b>：17:00 ~ 23:59 (外散)</li>
            <li>🏷️ <b>標籤 [宿]</b>：17:00 ~ 明日 07:30 (外宿)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader("👇 步驟：選擇對象並執行")
        
        # 多選選單
        selected_groups = st.multiselect(
            "請勾選要放假的班隊 (可複選疊加)",
            options=["左班", "右班", "義務役", "官員"],
            default=["左班", "義務役"],
            help="選中的群組，其無事故人員將會一起被加入放假行程"
        )
        
        if st.button("⚡ 執行放假 (依選定對象)", type="primary", use_container_width=True):
            if not selected_groups:
                st.error("⚠️ 請至少勾選一個群組！")
            else:
                new_df, count = apply_routine_leave(selected_groups, raw_df.copy())
                if count > 0:
                    save_data(new_df)
                    st.balloons()
                    groups_str = "、".join(selected_groups)
                    st.success(f"成功！已將 [{groups_str}] 共 {count} 員設定為外散/宿。")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.warning("⚠️ 沒有變更：可能群組無人，或所有人都已有事故。")

    st.divider()
    with st.expander("🛠️ 進階：自訂特定時間放假"):
        with st.form("custom_leave"):
            st.write("設定非例行性放假")
            cc1, cc2 = st.columns(2)
            tg_cats = cc1.multiselect("對象", ["左班", "右班", "義務役", "官員"], default=["左班"])
            cus_r = cc2.text_input("假別", "榮譽假")
            
            cd1, cd2 = st.columns(2)
            ds = cd1.date_input("開始", datetime.date.today())
            ts = cd1.time_input("時間", datetime.time(8, 0))
            de = cd2.date_input("結束", datetime.date.today())
            te = cd2.time_input("時間", datetime.time(21, 0))
            
            if st.form_submit_button("執行自訂"):
                dts = datetime.datetime.combine(ds, ts)
                dte = datetime.datetime.combine(de, te)
                if dte <= dts: st.error("結束時間錯誤")
                elif not tg_cats: st.error("請選對象")
                else:
                    ndf, c = apply_batch_leave_manual(tg_cats, dts, dte, cus_r, raw_df.copy())
                    if c > 0:
                        save_data(ndf)
                        st.success(f"已更新 {c} 筆")
                        time.sleep(1)
                        st.rerun()
                    else: st.warning("無變更")

# 側邊欄：新增人員
with st.sidebar:
    st.divider()
    with st.expander("➕ 新增人員"):
        with st.form("add_p"):
            nc = st.selectbox("類別", ["官員", "左班", "右班", "義務役"])
            nn = st.text_input("姓名")
            nt = st.selectbox("標籤", ["宿", "散", "無"])
            if st.form_submit_button("新增"):
                if nn and nn not in raw_df['Name'].values:
                    new_row = pd.DataFrame([{"Category": nc, "Name": nn, "Tag": nt, "Schedule": "[]"}])
                    save_data(pd.concat([raw_df, new_row], ignore_index=True))
                    st.rerun()
