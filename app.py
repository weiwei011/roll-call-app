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
LOGIN_PASSWORD = "1234" 

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
# 1. 頁面設定與「喧囂的夜晚」主題 CSS
# ==========================================
st.set_page_config(page_title="部隊電子點名簿 Pro", layout="wide", page_icon="🌃")

st.markdown("""
    <style>
    /* --- 🌌 全局主題：喧囂的夜晚 (Noisy Night) --- */
    .stApp { 
        background-color: #050505; 
        color: #E0E0E0; 
        background-image: linear-gradient(to bottom, #050505, #141414);
    }
    section[data-testid="stSidebar"] {
        background-color: #0A0A0A !important;
        border-right: 1px solid #333;
    }
    section[data-testid="stSidebar"] * { color: #AAA !important; }
    
    div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="base-input"], textarea {
        background-color: #1A1A1A !important;
        border: 1px solid #333 !important;
        color: #00FFC2 !important; 
        border-radius: 8px !important;
    }
    
    .person-card { 
        padding: 16px; 
        border-radius: 12px; 
        margin-bottom: 14px; 
        background-color: #161618; 
        border: 1px solid #333; 
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.5);
        transition: all 0.3s ease;
    }
    .person-card:hover { 
        transform: translateY(-3px); 
        box-shadow: 0 0 15px rgba(0, 255, 194, 0.1);
        border-color: #555;
    }
    
    .status-camp { border-left: 4px solid #39FF14; } 
    .status-leave { border-left: 4px solid #FF3131; } 
    
    .card-header { display: flex; justify-content: space-between; align-items: center; }
    .card-name { font-size: 1.3rem; font-weight: 700; color: #FFF; letter-spacing: 1px; }
    .card-details { font-size: 0.9rem; color: #888; margin-top: 6px; font-weight: 400; }
    
    .tag-badge { 
        font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; 
        background-color: #333; color: #DDD; margin-left: 8px;
        border: 1px solid #555; vertical-align: middle;
    }
    
    .stats-container {
        background: linear-gradient(135deg, #1A1A1A 0%, #0D0D0D 100%);
        padding: 20px; 
        border-radius: 16px;
        box-shadow: 0 0 20px rgba(0,0,0,0.8); 
        margin-bottom: 25px;
        border: 1px solid #333;
        position: relative;
        overflow: hidden;
    }
    .stats-container::before {
        content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 2px;
        background: linear-gradient(90deg, #FF3131, #39FF14, #00FFC2);
    }
    
    .stat-item { 
        background-color: #222; padding: 8px 15px; border-radius: 6px; 
        color: #BBB; font-size: 0.9rem; border: 1px solid #444;
        display: inline-block; margin-right: 8px; margin-bottom: 8px;
    }
    
    .stButton button { 
        background-color: #222 !important; 
        color: #EEE !important; 
        border: 1px solid #444 !important;
    }
    .stButton button:hover {
        border-color: #00FFC2 !important;
        color: #00FFC2 !important;
        box-shadow: 0 0 8px rgba(0, 255, 194, 0.4);
    }
    .stButton button[kind="primary"] {
        background-color: #004d40 !important;
        border-color: #00FFC2 !important;
        color: #00FFC2 !important;
    }

    [data-testid="stPopover"] > div > button {
        background-color: transparent !important;
        border: 1px solid #444 !important;
        color: #666 !important;
        font-size: 0.8rem !important;
        height: 2rem !important;
    }
    [data-testid="stPopover"] > div > button:hover {
        border-color: #888 !important;
        color: #FFF !important;
        background-color: #222 !important;
    }

    [data-testid="stSidebarCollapsedControl"] {
        background-color: #111 !important; border: 1px solid #FF5F1F !important;
        color: #FF5F1F !important;
    }
    </style>
""", unsafe_allow_html=True)

if not check_password():
    st.stop()

# ==========================================
# 2. 資料庫與預設名單
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

# 🟢 您的完整預設名單
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
    {"Category": "右班", "Name": "羅榆琇", "Tag": "宿"},
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
    {"Category": "義務役", "Name": "張育勝", "Tag": "散"},
    {"Category": "義務役", "Name": "夏文凱", "Tag": "散"},
    {"Category": "義務役", "Name": "張朕中", "Tag": "散"},
]

def get_taiwan_time():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).replace(tzinfo=None)

def load_data():
    try:
        df = conn.read(ttl=0)
        # 🟢 邏輯：如果資料庫是空的，或沒有欄位，就直接寫入上面的預設名單
        if df is None or df.empty or "Name" not in df.columns:
            df = pd.DataFrame(DEFAULT_ROSTER)
            df["Schedule"] = "[]"
            # 寫入雲端
            conn.update(data=df)
            return df
        
        # 保護舊資料
        if "Schedule" not in df.columns: df["Schedule"] = "[]"
        if "Tag" not in df.columns: df["Tag"] = "無"
        return df.fillna("")
    except:
        # 萬一連線失敗，至少先顯示預設名單
        df = pd.DataFrame(DEFAULT_ROSTER)
        df["Schedule"] = "[]"
        return df

def save_data(df):
    try:
        conn.update(data=df)
        st.toast("✅ 雲端同步完成", icon="📶")
    except Exception as e:
        st.error(f"寫入失敗: {e}")

raw_df = load_data()

# --- 邏輯 A: 狀態解析 ---
def get_person_status(schedule_json):
    now = get_taiwan_time()
    try: events = json.loads(str(schedule_json))
    except: events = []
    if not isinstance(events, list): events = []
    
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
        s_str = datetime.datetime.fromisoformat(current_event['start']).strftime('%d日 %H%M')
        reason = current_event.get('reason', '休假')
        return "leave", reason, f"🔴 {reason} ({s_str}~)", current_event

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
        s_str = datetime.datetime.fromisoformat(future_event['start']).strftime('%d日 %H%M')
        r = future_event.get('reason', '')
        return "camp", "在營", f"🟢 在營 (預: {s_str} {r})", None
        
    return "camp", "在營", "🟢 在營", None

# ==========================================
# 🟢 邏輯 B: 增強版批次解析 (已修正: 支援理由在前、自動年份)
# ==========================================
def parse_multi_incident_input(text_input, current_df):
    lines = text_input.strip().split('\n')
    updated_count = 0
    now = get_taiwan_time()
    current_year = now.year
    
    # 用來記住上一行的名字 (處理像 "病假 11/25..." 這種沒寫名字接續上一行的狀況)
    last_target_name = None 
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # 1. 先嘗試在這一行找名字
        current_target_name = None
        for name in current_df['Name'].values:
            if name in line:
                current_target_name = name
                # 把名字從字串中拿掉，避免干擾後面解析
                line = line.replace(name, "").strip()
                break
        
        # 2. 如果這行沒名字，就用上一行的名字 (支援連續輸入)
        if not current_target_name:
            if last_target_name:
                current_target_name = last_target_name
            else:
                continue # 沒名字也沒上一行，跳過
        else:
            last_target_name = current_target_name # 更新上一行名字

        # 3. 超強 Regex：抓取 "月/日 時間" ~ "月/日 時間" (年份可有可無)
        # 格式支援：11/17 0730 - 12/4 1800 (中間符號支援 - ~ 至)
        pattern = r"(\d{1,2})[./](\d{1,2})\s*(\d{4})?\s*(\d{4})\s*[-~至]\s*(\d{1,2})[./](\d{1,2})\s*(\d{4})?\s*(\d{4})"
        match = re.search(pattern, line)
        
        if match:
            # 抓出原本的時間字串，從 line 裡面扣掉，剩下的就是「理由」
            time_str = match.group(0)
            reason = line.replace(time_str, "").strip()
            
            # 如果理由是空的，預設為休假
            if not reason: reason = "休假"
            
            # 解析時間群組
            m1, d1, y1, t1, m2, d2, y2, t2 = match.groups()
            
            # 自動判斷年份 logic (如果沒寫年份，或跨年)
            # 假設：如果現在11月，輸入1月，那應該是明年
            real_y1 = int(y1) if y1 else current_year
            if not y1 and now.month >= 11 and int(m1) <= 2: real_y1 += 1
            
            real_y2 = int(y2) if y2 else real_y1 # 結束年份預設跟開始一樣
            # 如果結束月份比開始月份小 (例如 12月跨到1月)，結束年份+1
            if int(m2) < int(m1): real_y2 = real_y1 + 1
            if not y2 and now.month >= 11 and int(m2) <= 2: real_y2 = current_year + 1

            try:
                start_dt = datetime.datetime.strptime(f"{real_y1}-{m1}-{d1} {t1}", "%Y-%m-%d %H%M")
                end_dt = datetime.datetime.strptime(f"{real_y2}-{m2}-{d2} {t2}", "%Y-%m-%d %H%M")
                
                # 防呆：結束時間不能早於開始時間
                if end_dt < start_dt: 
                    end_dt = end_dt.replace(year=end_dt.year + 1)
                
                # 寫入資料
                idx = current_df[current_df['Name'] == current_target_name].index[0]
                
                # 讀取舊行程
                try: old_schedule = json.loads(current_df.at[idx, 'Schedule'])
                except: old_schedule = []
                if not isinstance(old_schedule, list): old_schedule = []
                
                new_event = {
                    "start": start_dt.isoformat(), 
                    "end": end_dt.isoformat(), 
                    "reason": reason  # 這裡會正確存入 "聯結車訓" 或 "公假"
                }
                
                # 避免重複加入完全一樣的行程
                is_duplicate = False
                for e in old_schedule:
                    if e['start'] == new_event['start'] and e['end'] == new_event['end']:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    old_schedule.append(new_event)
                    old_schedule.sort(key=lambda x: x['start'])
                    current_df.at[idx, 'Schedule'] = json.dumps(old_schedule, ensure_ascii=False)
                    updated_count += 1
            except Exception as e:
                # print(f"解析錯誤: {e}") 
                pass
                
    return current_df, updated_count

# --- 邏輯 C: 智慧放假 ---
def apply_routine_leave(target_cats, current_df):
    count = 0
    now = get_taiwan_time()
    today_date = now.date()
    start_time = datetime.datetime.combine(today_date, datetime.time(17, 0))
    
    for i, row in current_df.iterrows():
        if row['Category'] not in target_cats: continue
        tag = row.get('Tag', '')
        if tag == '散':
            end_time = datetime.datetime.combine(today_date, datetime.time(23, 59))
            reason = "外散"
        elif tag == '宿':
            tomorrow = today_date + datetime.timedelta(days=1)
            end_time = datetime.datetime.combine(tomorrow, datetime.time(7, 30))
            reason = "外宿"
        else: continue

        try: schedule = json.loads(row['Schedule'])
        except: schedule = []
        if not isinstance(schedule, list): schedule = []
        
        is_free = True
        for event in schedule:
            e_start = datetime.datetime.fromisoformat(event['start'])
            e_end = datetime.datetime.fromisoformat(event['end'])
            if max(start_time, e_start) < min(end_time, e_end):
                is_free = False
                break
        
        if is_free:
            schedule.append({"start": start_time.isoformat(), "end": end_time.isoformat(), "reason": reason})
            schedule.sort(key=lambda x: x['start'])
            current_df.at[i, 'Schedule'] = json.dumps(schedule, ensure_ascii=False)
            count += 1
    return current_df, count

def apply_batch_leave_manual(cats, start_dt, end_dt, reason, current_df):
    count = 0
    for i, row in current_df.iterrows():
        if row['Category'] not in cats: continue
        try: schedule = json.loads(row['Schedule'])
        except: schedule = []
        if not isinstance(schedule, list): schedule = []
        
        if all(max(start_dt, datetime.datetime.fromisoformat(e['start'])) < min(end_dt, datetime.datetime.fromisoformat(e['end'])) for e in schedule):
            schedule.append({"start": start_dt.isoformat(), "end": end_dt.isoformat(), "reason": reason})
            schedule.sort(key=lambda x: x['start'])
            current_df.at[i, 'Schedule'] = json.dumps(schedule, ensure_ascii=False)
            count += 1
    return current_df, count

# ==========================================
# 3. 主畫面
# ==========================================
st.title(f"🌃 點名簿 ({get_taiwan_time().strftime('%H:%M')})")

tab1, tab2, tab3 = st.tabs(["📊 現況總覽", "📝 批次輸入", "🚀 智慧放假"])

with tab1:
    if st.button("🔄 刷新狀態", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if not raw_df.empty:
        total_should = len(raw_df)
        leave_reasons = []
        
        for _, row in raw_df.iterrows():
            status, reason, _, _ = get_person_status(row['Schedule'])
            if status == "leave":
                leave_reasons.append(reason)
        
        current_absent = len(leave_reasons)
        current_present = total_should - current_absent
        reason_counts = Counter(leave_reasons)
        
        # 統計看板
        stats_html = f"""
        <div class="stats-container">
            <div style="font-size: 1.2rem; font-weight: bold; color: #FFF; margin-bottom: 10px;">
                📡 即時戰情看板
            </div>
            <div style="margin-bottom: 20px; font-size: 1rem; color: #BBB;">
                <span style="color:#888;">應到: <b>{total_should}</b></span> &nbsp;|&nbsp; 
                <span style="color:#39FF14;">🟢 實到: <b>{current_present}</b></span> &nbsp;|&nbsp; 
                <span style="color:#FF3131;">🔴 休假: <b>{current_absent}</b></span>
            </div>
            <div style="display:flex; flex-wrap:wrap;">
        """
        for r, c in reason_counts.items():
            stats_html += f'<div class="stat-item">{r}: <b style="color:#FFF">{c}</b></div>'
        if not reason_counts:
            stats_html += '<div class="stat-item">目前全員在營</div>'
        stats_html += "</div></div>"
        
        st.markdown(stats_html, unsafe_allow_html=True)
        
        # 人員列表
        cats = ["官員", "左班", "右班", "義務役"]
        for category in cats:
            group_df = raw_df[raw_df['Category'] == category]
            if group_df.empty: continue
            
            st.markdown(f"<h3 style='color:#00FFC2; border-bottom:1px solid #333; padding-bottom:5px;'>{category}</h3>", unsafe_allow_html=True)
            cols = st.columns(3)
            for i, (idx, row) in enumerate(group_df.iterrows()):
                status_code, reason, status_text, curr_evt = get_person_status(row['Schedule'])
                css_class = "status-leave" if status_code == "leave" else "status-camp"
                
                with cols[i % 3]:
                    st.markdown(f"""
                    <div class="person-card {css_class}">
                        <div class="card-header">
                            <div class="card-name">{row['Name']} <span class="tag-badge">{row.get('Tag','')}</span></div>
                            <div style="font-size:1.2rem;">{'🔴' if status_code=='leave' else '🟢'}</div>
                        </div>
                        <div class="card-details">{status_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.popover(f"管理 {row['Name']}"):
                        st.write(f"⚙️ **{row['Name']} 行程管理**")
                        try:
                            schedule = json.loads(row['Schedule'])
                            if st.button("🧹 清除過期", key=f"cl_{idx}"):
                                new_sched = [e for e in schedule if datetime.datetime.fromisoformat(e['end']) > get_taiwan_time()]
                                raw_df.at[idx, 'Schedule'] = json.dumps(new_sched)
                                save_data(raw_df)
                                st.rerun()
                            
                            if not schedule: st.caption("目前無行程")
                            for s_idx, evt in enumerate(schedule):
                                st.divider()
                                s_t = datetime.datetime.fromisoformat(evt['start']).strftime('%m/%d %H:%M')
                                e_t = datetime.datetime.fromisoformat(evt['end']).strftime('%m/%d %H:%M')
                                st.text(f"{evt['reason']}\n{s_t} ~ {e_t}")
                                if st.button("刪除此筆", key=f"del_{idx}_{s_idx}"):
                                    schedule.pop(s_idx)
                                    raw_df.at[idx, 'Schedule'] = json.dumps(schedule)
                                    save_data(raw_df)
                                    st.rerun()
                        except: st.error("資料異常")

with tab2:
    st.info("💡 格式：姓名 (換行) 時間 理由")
    batch_text = st.text_area("排程輸入區", height=200)
    if st.button("🚀 批次更新", type="primary"):
        if raw_df.empty: st.error("無資料")
        else:
            new_df, count = parse_multi_incident_input(batch_text, raw_df.copy())
            if count > 0: save_data(new_df); st.success(f"已新增 {count} 筆"); time.sleep(1); st.rerun()
            else: st.warning("無更新")

with tab3:
    st.header("🚀 智慧一鍵放假")
    st.caption("自動依據 [散/宿] 標籤設定今日假單")
    
    with st.container(border=True):
        selected_groups = st.multiselect("對象 (可複選)", ["左班", "右班", "義務役", "官員"], default=["左班", "義務役"])
        if st.button("⚡ 執行放假", type="primary", use_container_width=True):
            if not selected_groups: st.error("請選擇群組")
            else:
                new_df, count = apply_routine_leave(selected_groups, raw_df.copy())
                if count > 0: save_data(new_df); st.success(f"已設定 {count} 員"); time.sleep(1); st.rerun()
                else: st.warning("無變更")

    st.divider()
    with st.expander("🛠️ 自訂時間放假"):
        with st.form("custom"):
            c1, c2 = st.columns(2)
            cats = c1.multiselect("對象", ["左班", "右班", "義務役", "官員"], default=["左班"])
            rsn = c2.text_input("假別", "榮譽假")
            d1, d2 = st.columns(2)
            ds = d1.date_input("起", datetime.date.today())
            ts = d1.time_input("時", datetime.time(8,0))
            de = d2.date_input("迄", datetime.date.today())
            te = d2.time_input("時", datetime.time(21,0))
            if st.form_submit_button("執行"):
                dts, dte = datetime.datetime.combine(ds, ts), datetime.datetime.combine(de, te)
                if dte<=dts: st.error("時間錯誤")
                else:
                    ndf, c = apply_batch_leave_manual(cats, dts, dte, rsn, raw_df.copy())
                    if c>0: save_data(ndf); st.success(f"已更新 {c} 筆"); time.sleep(1); st.rerun()
                    else: st.warning("無變更")

with st.sidebar:
    st.divider()
    with st.expander("➕ 新增人員"):
        with st.form("add"):
            nc = st.selectbox("類別", ["官員", "左班", "右班", "義務役"])
            nn = st.text_input("姓名")
            nt = st.selectbox("標籤", ["宿", "散", "無"])
            if st.form_submit_button("新增"):
                if nn and nn not in raw_df['Name'].values:
                    save_data(pd.concat([raw_df, pd.DataFrame([{"Category": nc, "Name": nn, "Tag": nt, "Schedule": "[]"}])], ignore_index=True))
                    st.rerun()
    st.divider()
    with st.expander("🔴 危險操作 (重置)"):
        if st.button("🧹 清空所有假單"):
            raw_df['Schedule'] = "[]"
            save_data(raw_df); st.rerun()
        st.warning("👇 若人員名單錯誤，請點此按鈕，系統會刪除舊資料並自動載入【預設完整名單】。")
        if st.button("🗑️ 刪除全部並載入預設名單", type="primary"):
            # 存入空資料表，讓下次 load_data 自動填入 DEFAULT_ROSTER
            save_data(pd.DataFrame(columns=["Category", "Name", "Tag", "Schedule"]))
            time.sleep(1)
            st.rerun()
