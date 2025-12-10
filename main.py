import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from twilio.rest import Client
import datetime
from PIL import Image
import re
import requests
import io
from google.cloud import vision

# 设置页面
st.set_page_config(page_title="健康追踪器 Health Tracker", layout="wide")

# ✅ Google Sheets 授权
@st.cache_resource
def init_google_sheets():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)
    return client

# ✅ Google Cloud Vision 授权
@st.cache_resource
def init_vision_client():
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    return vision.ImageAnnotatorClient(credentials=creds)

try:
    gc = init_google_sheets()
    spreadsheet = gc.open("BP-Glucose-Tracker")
    vision_client = init_vision_client()
except Exception as e:
    st.error(f"❌ 连接失败：{e}")
    st.stop()

# ✅ Twilio 授权
account_sid = st.secrets["twilio"]["account_sid"]
auth_token = st.secrets["twilio"]["auth_token"]
twilio_client = Client(account_sid, auth_token)

# ✅ Groq API 配置
groq_api_key = st.secrets.get("groq", {}).get("api_key", "")

# 读取数据
@st.cache_data(ttl=60)
def load_health_data():
    worksheet = spreadsheet.worksheet("Sheet1")
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    
    column_mapping = {
        "日期": "Date",
        "时间段": "Time Period",
        "收缩压": "Systolic",
        "舒张压": "Diastolic",
        "血糖（mmol/L）": "Glucose(mmol/L)",
        "脉搏": "Pulse",
        "有吃药吗？": "Took Medication",
        "药物名称": "Medication",
        "饭前/饭后": "Before/After",
        "剂量": "Dose",
        "血压备注": "BP Note",
        "血糖备注": "Glucose Note"
    }
    df.rename(columns=column_mapping, inplace=True)
    
    # Clean up the data
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        df = df.dropna(subset=["Date"])
        df["Date"] = df["Date"].dt.strftime('%Y-%m-%d')
    
    # Convert numeric columns and handle empty strings
    numeric_cols = ["Systolic", "Diastolic", "Pulse", "Glucose(mmol/L)"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(how='all')
    
    return df

@st.cache_data(ttl=60)
def load_medication_stock():
    stock_sheet = spreadsheet.worksheet("Medication Stock")
    stock_data = stock_sheet.get_all_records()
    stock_df = pd.DataFrame(stock_data)
    
    stock_df['Refill Date'] = pd.to_datetime(stock_df['Refill Date'])
    stock_df['Remaining Days'] = (stock_df['Total Given'] / stock_df['Dose Per Day']).astype(int)
    stock_df['Estimated Finish Date'] = stock_df['Refill Date'] + pd.to_timedelta(stock_df['Remaining Days'], unit='d')
    
    today = datetime.datetime.today()
    stock_df['Warning'] = stock_df['Estimated Finish Date'].apply(
        lambda x: "⚠️ 快用完了！Going to finish!" if (x - today).days <= 7 else ""
    )
    
    return stock_df

# 侧边栏导航
st.sidebar.title("📱 导航 Navigation")
page = st.sidebar.radio(
    "选择页面 Choose Page:",
    ["📝 数据输入 Data Entry", "📊 趋势图表 Charts", "💊 药物管理 Medication", "🤖 AI 助手 AI Assistant"]
)

if st.sidebar.checkbox("🔍 开启大字体 Large Font"):
    st.markdown('<style>body {font-size: 20px;}</style>', unsafe_allow_html=True)

# ==================== 页面 1: 数据输入 ====================
if page == "📝 数据输入 Data Entry":
    st.title("📝 健康数据输入 Health Data Entry")
    
    df = load_health_data()
    worksheet = spreadsheet.worksheet("Sheet1")
    
    # Load medication list from stock
    stock_df = load_medication_stock()
    medication_list = ["无 None"] + stock_df['jie'].tolist() if not stock_df.empty else ["无 None"]
    
    # 显示最近记录
    st.subheader("🕒 最近记录 Latest Records")
    st.dataframe(df.tail(5), use_container_width=True)
    
    st.markdown("---")
    
    # 📸 OCR 功能
    st.subheader("📸 拍照上传 Snap & Upload")
    st.info("💡 **OCR 使用说明 How to use:**\n1. 上传照片 Upload photo\n2. 点击识别按钮 Click Read button\n3. 检查识别结果 Check results\n4. 滚动到下方表单查看数值 Scroll down to see values in form")
    
    col_a, col_b = st.columns([1, 1])
    
    with col_a:
        uploaded_image = st.file_uploader(
            "上传血压计或血糖仪照片 Upload photo", 
            type=["jpg", "jpeg", "png"],
            key="image_uploader"
        )
        
        if uploaded_image:
            image = Image.open(uploaded_image)
            st.image(image, caption="上传的照片 Uploaded Photo", use_container_width=True)
            
            if st.button("🔍 识别数值 Read Numbers", use_container_width=True, key="ocr_button"):
                with st.spinner("正在识别中 Reading..."):
                    try:
                        # Convert image to base64 for AI analysis
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format='PNG')
                        img_byte_arr = img_byte_arr.getvalue()
                        
                        import base64
                        image_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
                        
                        # Use Groq Vision to analyze the image
                        if groq_api_key:
                            ai_response = requests.post(
                                "https://api.groq.com/openai/v1/chat/completions",
                                headers={
                                    "Authorization": f"Bearer {groq_api_key}",
                                    "Content-Type": "application/json"
                                },
                                json={
                                    "model": "llama-3.2-90b-vision-preview",
                                    "messages": [
                                        {
                                            "role": "user",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": """Look at this blood pressure or glucose monitor photo carefully. 
Extract ONLY the numbers for:
1. Systolic (top number, usually 90-200)
2. Diastolic (bottom number, usually 50-110)  
3. Pulse/Heart Rate (usually 40-150)

Respond ONLY in this exact JSON format, nothing else:
{"systolic": number, "diastolic": number, "pulse": number}

If you can't find a value, use 0."""
                                                },
                                                {
                                                    "type": "image_url",
                                                    "image_url": {
                                                        "url": f"data:image/png;base64,{image_base64}"
                                                    }
                                                }
                                            ]
                                        }
                                    ],
                                    "temperature": 0.1,
                                    "max_tokens": 100
                                }
                            )
                            
                            if ai_response.status_code == 200:
                                ai_text = ai_response.json()["choices"][0]["message"]["content"]
                                
                                with st.expander("🔍 查看识别结果 View Detection Results", expanded=True):
                                    st.write("**AI 分析结果 AI Analysis:**")
                                    st.code(ai_text)
                                
                                # Parse JSON response
                                import json
                                # Extract JSON from response
                                json_match = re.search(r'\{[^}]+\}', ai_text)
                                if json_match:
                                    data = json.loads(json_match.group())
                                    
                                    systolic_val = data.get('systolic', 120)
                                    diastolic_val = data.get('diastolic', 80)
                                    pulse_val = data.get('pulse', 70)
                                    
                                    # Validate ranges
                                    if 50 <= systolic_val <= 250:
                                        st.session_state.ocr_systolic = systolic_val
                                    if 30 <= diastolic_val <= 150:
                                        st.session_state.ocr_diastolic = diastolic_val
                                    if 30 <= pulse_val <= 180:
                                        st.session_state.ocr_pulse = pulse_val
                                    
                                    st.success(f"""✅ AI 识别成功 AI Success! 
                                    
收缩压 Systolic: **{st.session_state.get('ocr_systolic', 120)}** mmHg
舒张压 Diastolic: **{st.session_state.get('ocr_diastolic', 80)}** mmHg  
脉搏 Pulse: **{st.session_state.get('ocr_pulse', 70)}** bpm""")
                                    st.warning("⚠️ 请向下滚动到表单检查数值 Please scroll down to verify!")
                                else:
                                    st.warning("⚠️ AI 无法识别数字 AI cannot detect numbers")
                            else:
                                st.error(f"AI 错误: {ai_response.status_code}")
                                raise Exception("AI analysis failed, falling back to Vision API")
                        else:
                            raise Exception("No Groq API key, using Vision API fallback")
                            
                    except Exception as e:
                        # Fallback to Google Vision API
                        st.info("🔄 使用备用识别方法 Using backup OCR...")
                        try:
                            vision_image = vision.Image(content=img_byte_arr)
                            response = vision_client.text_detection(image=vision_image)
                            texts = response.text_annotations
                            
                            if response.error.message:
                                raise Exception(response.error.message)
                            
                            full_text = texts[0].description if texts else ""
                            
                            with st.expander("🔍 备用识别结果 Backup OCR Results", expanded=True):
                                st.write("**识别到的文字:**")
                                st.code(full_text if full_text.strip() else "未检测到文字")
                                
                                numbers = re.findall(r'\d+', full_text)
                                st.write("**数字列表:**", numbers if numbers else "无")
                            
                            if numbers and len(numbers) >= 2:
                                num_list = [int(n) for n in numbers if n.isdigit() and len(n) <= 3]
                                num_list.sort(reverse=True)
                                
                                systolic_val = 120
                                diastolic_val = 80
                                pulse_val = 70
                                
                                for num in num_list:
                                    if 90 <= num <= 200 and systolic_val == 120:
                                        systolic_val = num
                                    elif 50 <= num <= 110 and diastolic_val == 80 and num < systolic_val:
                                        diastolic_val = num
                                    elif 40 <= num <= 150 and pulse_val == 70:
                                        pulse_val = num
                                
                                st.session_state.ocr_systolic = systolic_val
                                st.session_state.ocr_diastolic = diastolic_val
                                st.session_state.ocr_pulse = pulse_val
                                
                                st.success(f"✅ 识别成功！Systolic: {systolic_val}, Diastolic: {diastolic_val}, Pulse: {pulse_val}")
                            else:
                                st.warning("⚠️ 无法识别足够的数字")
                                st.info("建议手动输入 Please enter manually")
                        except Exception as vision_error:
                            st.error(f"❌ 所有识别方法失败 All OCR methods failed: {str(vision_error)}")
                            st.info("💡 请使用手动输入 Please use manual entry below")
    
    with col_b:
        st.info("💡 **拍照小贴士 Photo Tips:**\n- 光线充足 Good lighting\n- 数字清晰 Clear numbers\n- 避免反光 No glare\n- 填满屏幕 Fill the frame")
    
    st.markdown("---")
    
    # 手动输入表单
    st.subheader("✍️ 手动输入 Manual Entry")
    
    # Initialize default values if OCR data doesn't exist or is invalid
    default_systolic = st.session_state.get("ocr_systolic", 120)
    default_diastolic = st.session_state.get("ocr_diastolic", 80)
    default_pulse = st.session_state.get("ocr_pulse", 70)
    
    # Ensure defaults are within valid range
    default_systolic = max(50, min(250, default_systolic))
    default_diastolic = max(30, min(150, default_diastolic))
    default_pulse = max(30, min(180, default_pulse))
    
    with st.form("record_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Auto-capture current date and time
            current_datetime = datetime.datetime.now()
            date = st.date_input("日期 Date", value=current_datetime.date(), disabled=True)
            time_display = st.text_input("时间 Time", value=current_datetime.strftime("%H:%M:%S"), disabled=True)
            
            took_med = st.radio("有吃药吗 Taken Medication?", ["是 Yes", "否 NO"])
            
            # Medication dropdown with stock list
            medication = st.selectbox(
                "药物名称 Medication", 
                medication_list,
                help="从药物库存中选择 Select from medication stock"
            )
            
            before_after = st.selectbox("饭前/饭后 Meal", ["饭前 Before", "饭后 After"])
            dose = st.text_input("剂量 Dose", placeholder="例如：5 mg")
        
        with col2:
            systolic = st.number_input(
                "收缩压 Systolic", 
                min_value=50, 
                max_value=250, 
                value=default_systolic
            )
            diastolic = st.number_input(
                "舒张压 Diastolic", 
                min_value=30, 
                max_value=150, 
                value=default_diastolic
            )
            pulse = st.number_input(
                "脉搏 Pulse", 
                min_value=30, 
                max_value=180, 
                value=default_pulse
            )
            glucose = st.number_input("血糖 Blood Sugar (mmol/L)", min_value=1.0, max_value=20.0, format="%.1f", value=5.0)
        
        bp_note = st.text_input("血压备注 BP Note", placeholder="例如：感觉头晕、还好等")
        glucose_note = st.text_input("血糖备注 Glucose Note", placeholder="例如：空腹后测量、饭后两小时等")
        
        submitted = st.form_submit_button("✅ 提交记录 Submit", use_container_width=True)
        
        if submitted:
            bp_status = "高" if systolic > 140 or diastolic > 90 else "正常"
            glucose_status = "高" if glucose > 7.8 else ("低" if glucose < 3.9 else "正常")
            
            # Capture exact submission time
            submission_time = datetime.datetime.now()
            
            new_row = [
                submission_time.strftime("%Y-%m-%d"),
                submission_time.strftime("%H:%M:%S"),
                took_med, medication, before_after, dose,
                systolic, diastolic, pulse, bp_status, bp_note, glucose, glucose_status, glucose_note
            ]
            worksheet.append_row(new_row)
            st.success(f"✅ 记录已成功提交！Submitted at {submission_time.strftime('%H:%M:%S')}")
            
            # Clear cache and refresh
            st.cache_data.clear()
            
            # 清除 OCR 数据
            for key in ['ocr_systolic', 'ocr_diastolic', 'ocr_pulse']:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Force page refresh to show new data
            st.rerun()

# ==================== 页面 2: 趋势图表 ====================
elif page == "📊 趋势图表 Charts":
    st.title("📊 健康趋势图表 Health Trends")
    
    df = load_health_data()
    
    if "Date" not in df.columns or df.empty:
        st.warning("⚠️ 没有数据可显示")
        st.stop()
    
    df_sorted = df.sort_values(by="Date")
    
    # 统计卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_systolic = df["Systolic"].dropna().mean() if "Systolic" in df.columns and not df["Systolic"].dropna().empty else 0
        st.metric("平均收缩压 Avg Systolic", f"{avg_systolic:.1f} mmHg")
    
    with col2:
        avg_diastolic = df["Diastolic"].dropna().mean() if "Diastolic" in df.columns and not df["Diastolic"].dropna().empty else 0
        st.metric("平均舒张压 Avg Diastolic", f"{avg_diastolic:.1f} mmHg")
    
    with col3:
        avg_pulse = df["Pulse"].dropna().mean() if "Pulse" in df.columns and not df["Pulse"].dropna().empty else 0
        st.metric("平均脉搏 Avg Pulse", f"{avg_pulse:.0f} bpm")
    
    with col4:
        avg_glucose = df["Glucose(mmol/L)"].dropna().mean() if "Glucose(mmol/L)" in df.columns and not df["Glucose(mmol/L)"].dropna().empty else 0
        st.metric("平均血糖 Avg Glucose", f"{avg_glucose:.1f} mmol/L")
    
    st.markdown("---")
    
    # 图表
    st.subheader("🫀 血压趋势 Blood Pressure Trend")
    chart_df = df_sorted[["Date", "Systolic", "Diastolic"]].dropna()
    if not chart_df.empty:
        st.line_chart(chart_df.set_index("Date"))
    else:
        st.info("📊 暂无数据 No data available")
    
    st.subheader("💓 脉搏趋势 Pulse Trend")
    pulse_df = df_sorted[["Date", "Pulse"]].dropna()
    if not pulse_df.empty:
        st.line_chart(pulse_df.set_index("Date"))
    else:
        st.info("📊 暂无数据 No data available")
    
    st.subheader("🍬 血糖趋势 Blood Sugar Trend")
    glucose_df = df_sorted[["Date", "Glucose(mmol/L)"]].dropna()
    if not glucose_df.empty:
        st.line_chart(glucose_df.set_index("Date"))
    else:
        st.info("📊 暂无数据 No data available")
    
    # 完整数据表
    st.markdown("---")
    st.subheader("📋 完整记录 Full Records")
    
    # 日期筛选
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        start_date = st.date_input("开始日期 Start Date", value=pd.to_datetime(df["Date"].min()))
    with col_filter2:
        end_date = st.date_input("结束日期 End Date", value=pd.to_datetime(df["Date"].max()))
    
    filtered_df = df[
        (pd.to_datetime(df["Date"]) >= pd.to_datetime(start_date)) & 
        (pd.to_datetime(df["Date"]) <= pd.to_datetime(end_date))
    ]
    
    st.dataframe(filtered_df, use_container_width=True)

# ==================== 页面 3: 药物管理 ====================
elif page == "💊 药物管理 Medication":
    st.title("💊 药物库存管理 Medication Management")
    
    stock_df = load_medication_stock()
    stock_sheet = spreadsheet.worksheet("Medication Stock")
    
    # 显示库存
    st.subheader("📦 当前库存 Current Stock")
    st.dataframe(
        stock_df[['jie', 'Total Given', 'Dose Per Day', 'Estimated Finish Date', 'Warning']], 
        use_container_width=True
    )
    
    # 快用完提醒
    urgent_meds = stock_df[stock_df['Warning'] != ""]
    if not urgent_meds.empty:
        st.error("⚠️ 以下药物快用完了！These medications are running low!")
        st.dataframe(urgent_meds[['jie', 'Estimated Finish Date']], use_container_width=True)
    
    st.markdown("---")
    
    col_med1, col_med2 = st.columns(2)
    
    # 添加新药物
    with col_med1:
        with st.expander("➕ 添加新药物 Add New Medication"):
            new_med_name = st.text_input("药物名称 Medication Name")
            new_refill_date = st.date_input("补药日期 Restock Date")
            new_total = st.number_input("药品总数 Total Amount", min_value=0)
            new_dose = st.number_input("每日剂量 Daily Dose", min_value=0.0, step=0.1)
            new_note = st.text_input("备注 Note")
            
            if st.button("添加 Add", use_container_width=True):
                new_row = [new_med_name, new_refill_date.strftime("%Y-%m-%d"), new_total, new_dose, new_note]
                stock_sheet.append_row(new_row)
                st.success("✅ 药物记录已添加 Done!")
                st.cache_data.clear()
                st.rerun()
    
    # 修改剂量
    with col_med2:
        with st.expander("📝 修改药物剂量 Edit Dose"):
            med_options = stock_df['jie'].tolist()
            selected_med = st.selectbox("选择药物 Select Medication", med_options)
            new_dose_edit = st.number_input("新的每日剂量 New Daily Dose", min_value=0.0, step=0.1)
            
            if st.button("更新剂量 Update", use_container_width=True):
                cell = stock_sheet.find(selected_med)
                if cell:
                    row_num = cell.row
                    stock_sheet.update_cell(row_num, 4, new_dose_edit)
                    st.success(f"✅ {selected_med} 剂量已更新 Dose updated!")
                    st.cache_data.clear()
                    st.rerun()

# ==================== 页面 4: AI 助手 ====================
elif page == "🤖 AI 助手 AI Assistant":
    st.title("🤖 AI 健康助手 AI Health Assistant")
    st.write("问我关于你的健康数据！Ask me about your health data!")
    
    df = load_health_data()
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # 问答区
    user_question = st.text_input(
        "💬 问问题 Ask a question:", 
        placeholder="例如：我的血压趋势如何？My blood pressure trend?"
    )
    
    if st.button("🚀 询问 AI Ask AI", use_container_width=True) and user_question:
        if not groq_api_key:
            st.warning("⚠️ 请在 secrets.toml 添加 Groq API key")
        else:
            with st.spinner("🤔 AI 正在分析中 Analyzing..."):
                # 准备健康数据摘要
                recent_data = df.tail(10).to_string()
                
                avg_systolic = df["Systolic"].dropna().mean() if "Systolic" in df.columns and not df["Systolic"].dropna().empty else 0
                avg_diastolic = df["Diastolic"].dropna().mean() if "Diastolic" in df.columns and not df["Diastolic"].dropna().empty else 0
                avg_glucose = df["Glucose(mmol/L)"].dropna().mean() if "Glucose(mmol/L)" in df.columns and not df["Glucose(mmol/L)"].dropna().empty else 0
                
                health_summary = f"""
用户最近的健康数据：
- 平均收缩压 Avg Systolic: {avg_systolic:.1f} mmHg
- 平均舒张压 Avg Diastolic: {avg_diastolic:.1f} mmHg
- 平均血糖 Avg Blood Sugar: {avg_glucose:.1f} mmol/L

最近10笔记录 Recent 10 records：
{recent_data}
"""
                
                try:
                    response = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {groq_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "llama-3.3-70b-versatile",
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "You are a friendly health assistant helping elderly people understand their blood pressure and blood sugar data. Always respond in the SAME LANGUAGE the user asks in (English or Chinese). Use simple, easy-to-understand language and give practical advice. 你是一个友善的健康助手，帮助老年人理解他们的血压和血糖数据。请用用户提问的语言回答（英文或中文）。用简单易懂的语言，并给出实用的建议。"
                                },
                                {
                                    "role": "user",
                                    "content": f"{health_summary}\n\nUser Question: {user_question}"
                                }
                            ],
                            "temperature": 0.7,
                            "max_tokens": 1024
                        }
                    )
                    
                    if response.status_code == 200:
                        ai_response = response.json()["choices"][0]["message"]["content"]
                        st.session_state.chat_history.append({"user": user_question, "ai": ai_response})
                        st.success("✅ AI 回答 AI Response:")
                        st.write(ai_response)
                    else:
                        st.error(f"❌ API 错误 Error: {response.status_code}")
                except Exception as e:
                    st.error(f"❌ 连接失败 Failed: {e}")
    
    # 显示聊天历史
    if st.session_state.chat_history:
        st.markdown("---")
        st.subheader("📜 聊天记录 Chat History")
        
        for i, chat in enumerate(reversed(st.session_state.chat_history)):
            with st.container():
                st.markdown(f"**🙋 你 You:** {chat['user']}")
                st.markdown(f"**🤖 AI:** {chat['ai']}")
                st.markdown("---")
        
        if st.button("🗑️ 清除历史 Clear History"):
            st.session_state.chat_history = []
            st.rerun()
