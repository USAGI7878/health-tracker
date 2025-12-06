import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from twilio.rest import Client
import datetime
from PIL import Image
import pytesseract
import re
import requests

# 设置页面标题
st.set_page_config(page_title="血压 & 血糖趋势图Blood Pressure & Blood Sugar Graph", layout="centered")
st.subheader("📈 血压 & 血糖趋势图表Blood Pressure & Blood Sugar Graph")

# ✅ Google Sheets 授权
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)
client = gspread.authorize(creds)
gc = gspread.authorize(creds)

try:
    spreadsheet = gc.open("BP-Glucose-Tracker")
    st.success("✅ 成功连接 Google Sheet！")
except Exception as e:
    st.error(f"❌ 连接失败：{e}")

# ✅ Twilio 授权
account_sid = st.secrets["twilio"]["account_sid"]
auth_token = st.secrets["twilio"]["auth_token"]
twilio_client = Client(account_sid, auth_token)

# ✅ 打开 Google Sheet
spreadsheet = gc.open("BP-Glucose-Tracker")
worksheet = spreadsheet.worksheet("Sheet1")

# 转换为 DataFrame
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# 🧠 栏位映射
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

# ✅ 检查栏位是否存在
if "Date" in df.columns:
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.strftime('%Y-%m-%d')

# ✅ 样式美化
st.markdown("""
    <style>
        .big-font {
            font-size: 24px !important;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-font">📋 血压 & 血糖记录查看Blood Pressure and Blood Sugar Record</div>', unsafe_allow_html=True)

if st.checkbox("🔍 开启大字体 / High Contrast"):
    st.markdown('<style>body {font-size: 40px; background-color: #f8f9fa;}</style>', unsafe_allow_html=True)

# 📊 趋势图表
if st.toggle("📊 显示趋势图表Graph"):
    df_sorted = df.sort_values(by="Date")
    
    st.markdown("#### 🫀 血压趋势Blood Pressure（收缩压 / 舒张压）")
    st.line_chart(df_sorted[["Date", "Systolic", "Diastolic"]].set_index("Date"))

    st.markdown("#### 💓 脉搏趋势Pulse")
    st.line_chart(df_sorted[["Date", "Pulse"]].set_index("Date"))

    st.markdown("#### 🍬 血糖趋势Blood Sugar")
    st.line_chart(df_sorted[["Date", "Glucose(mmol/L)"]].set_index("Date"))

# 展示最近 5 笔记录
st.subheader("🕒 最近记录Latest Update")
st.dataframe(df.tail(5), use_container_width=True)

# 🤖 AI Health Assistant
st.markdown("---")
st.subheader("🤖 AI 健康助手 AI Health Assistant")
st.write("问我关于你的健康数据！Ask me about your health data!")

# Groq API 配置 (100% FREE!)
groq_api_key = st.secrets.get("groq", {}).get("api_key", "")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_question = st.text_input("💬 问问题Ask a question:", placeholder="例如Example：我的血压趋势如何？My blood pressure trend?")

if st.button("🚀 询问 AI Ask AI") and user_question:
    if not groq_api_key:
        st.warning("⚠️ 请在 secrets.toml 添加 Groq API key")
    else:
        with st.spinner("🤔 AI 正在分析中 Analyzing..."):
            # 准备健康数据摘要
            recent_data = df.tail(10).to_string()
            
            # 计算一些统计数据
            avg_systolic = df["Systolic"].mean() if "Systolic" in df.columns else 0
            avg_diastolic = df["Diastolic"].mean() if "Diastolic" in df.columns else 0
            avg_glucose = df["Glucose(mmol/L)"].mean() if "Glucose(mmol/L)" in df.columns else 0
            
            health_summary = f"""
用户最近的健康数据：
- 平均收缩压Average Systolic: {avg_systolic:.1f} mmHg
- 平均舒张压Average Diastolic: {avg_diastolic:.1f} mmHg
- 平均血糖Average Blood Sugar: {avg_glucose:.1f} mmol/L

最近10笔记录Recent 10 records：
{recent_data}
"""
            
            # 调用 Groq API (100% FREE!)
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",  # Fast & free model
                        "messages": [
                            {
                                "role": "system",
                                "content": "你是一个友善的健康助手，帮助老年人理解他们的血压和血糖数据。用简单易懂的语言回答，并给出实用的建议。You are a friendly health assistant helping elderly understand their blood pressure and blood sugar data. Answer in simple language with practical advice."
                            },
                            {
                                "role": "user",
                                "content": f"{health_summary}\n\n用户问题User Question: {user_question}"
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
                    st.error(f"❌ API 错误Error: {response.status_code}")
            except Exception as e:
                st.error(f"❌ 连接失败Failed: {e}")

# 显示聊天历史
if st.session_state.chat_history:
    with st.expander("📜 查看聊天记录View Chat History"):
        for chat in st.session_state.chat_history:
            st.markdown(f"**🙋 你You:** {chat['user']}")
            st.markdown(f"**🤖 AI:** {chat['ai']}")
            st.markdown("---")

st.markdown("---")

# 📸 OCR 功能
st.subheader("📸 拍照上传数据 Snap & Upload")
st.write("拍张照片，AI 自动识别数值！Take a photo, AI reads the numbers!")

uploaded_image = st.file_uploader("上传血压计或血糖仪照片Upload BP/Glucose meter photo", type=["jpg", "jpeg", "png"])

if uploaded_image:
    image = Image.open(uploaded_image)
    st.image(image, caption="上传的照片Uploaded Photo", use_container_width=True)
    
    if st.button("🔍 识别数值 Read Numbers"):
        with st.spinner("正在识别中 Reading..."):
            try:
                # 使用 Tesseract OCR
                text = pytesseract.image_to_string(image)
                st.write("**识别到的文字Detected Text:**")
                st.code(text)
                
                # 提取数字
                numbers = re.findall(r'\d+\.?\d*', text)
                st.write("**提取的数字Extracted Numbers:**", numbers)
                
                # 智能判断（简单逻辑）
                if len(numbers) >= 2:
                    systolic_ocr = int(float(numbers[0])) if float(numbers[0]) < 250 else None
                    diastolic_ocr = int(float(numbers[1])) if float(numbers[1]) < 150 else None
                    pulse_ocr = int(float(numbers[2])) if len(numbers) > 2 and float(numbers[2]) < 200 else None
                    
                    st.success("✅ 自动识别成功Auto detected！")
                    st.write(f"收缩压Systolic: {systolic_ocr}, 舒张压Diastolic: {diastolic_ocr}, 脉搏Pulse: {pulse_ocr}")
                    
                    # 保存到 session state 供表单使用
                    st.session_state.ocr_systolic = systolic_ocr
                    st.session_state.ocr_diastolic = diastolic_ocr
                    st.session_state.ocr_pulse = pulse_ocr
                else:
                    st.warning("⚠️ 无法识别，请手动输入Cannot detect, please input manually")
            except Exception as e:
                st.error(f"❌ OCR 错误Error: {e}")

st.markdown("---")

# 📝 新增记录
st.subheader("📝 新增记录New Record")

with st.form("record_form"):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("日期Date")
        time_of_day = st.selectbox("时间段Timing", ["早上AM", "中午NOON", "晚上PM"])
        took_med = st.radio("有吃药吗Taken Medication？", ["是Yes", "否NO"])
        medication = st.text_input("药物名称Medication", placeholder="例如：Amlo 或 Metformin")
        before_after = st.selectbox("饭前/饭后Meal", ["饭前Before", "饭后After"])
        dose = st.text_input("剂量Dose", placeholder="例如Example：5 mg")

    with col2:
        # 如果有 OCR 数据，自动填充
        systolic = st.number_input(
            "收缩压<（Systolic）", 
            min_value=50, 
            max_value=250, 
            value=st.session_state.get("ocr_systolic", 120)
        )
        diastolic = st.number_input(
            "舒张压>（Diastolic）", 
            min_value=30, 
            max_value=150, 
            value=st.session_state.get("ocr_diastolic", 80)
        )
        pulse = st.number_input(
            "脉搏（Pulse）", 
            min_value=30, 
            max_value=180, 
            value=st.session_state.get("ocr_pulse", 70)
        )
        glucose = st.number_input("血糖Blood Sugar（mmol/L）", min_value=1.0, max_value=20.0, format="%.1f")

    bp_note = st.text_input("血压备注Note for BP", placeholder="例如：感觉头晕、还好等")
    glucose_note = st.text_input("血糖备注Note for BS", placeholder="例如：空腹后测量、饭后两小时等")

    submitted = st.form_submit_button("✅ 提交记录Submit!")

    if submitted:
        bp_status = "高" if systolic > 140 or diastolic > 90 else "正常"
        glucose_status = "高" if glucose > 7.8 else ("低" if glucose < 3.9 else "正常")

        new_row = [
            str(date), time_of_day, took_med, medication, before_after, dose,
            systolic, diastolic, pulse, bp_status, bp_note, glucose, glucose_status, glucose_note
        ]
        worksheet.append_row(new_row)
        st.success("✅ 记录已成功提交！Done!")
        
        # 清除 OCR 数据
        if "ocr_systolic" in st.session_state:
            del st.session_state.ocr_systolic
            del st.session_state.ocr_diastolic
            del st.session_state.ocr_pulse

# 💊 药物库存提醒
st.markdown("---")
st.markdown("### 💊 药物库存提醒Medication Store")

stock_sheet = spreadsheet.worksheet("Medication Stock")
stock_data = stock_sheet.get_all_records()
stock_df = pd.DataFrame(stock_data)

stock_df['Refill Date'] = pd.to_datetime(stock_df['Refill Date'])
stock_df['Remaining Days'] = (stock_df['Total Given'] / stock_df['Dose Per Day']).astype(int)
stock_df['Estimated Finish Date'] = stock_df['Refill Date'] + pd.to_timedelta(stock_df['Remaining Days'], unit='d')

today = datetime.datetime.today()
stock_df['Warning'] = stock_df['Estimated Finish Date'].apply(lambda x: "⚠️ 快用完了！Going to finish!" if (x - today).days <= 7 else "")

st.dataframe(stock_df[['jie', 'Total Given', 'Dose Per Day', 'Estimated Finish Date', 'Warning']])

with st.expander("➕ 添加新药物记录Add Medication"):
    new_med_name = st.text_input("药物名称Medication Name")
    new_refill_date = st.date_input("补药日期Restock Date")
    new_total = st.number_input("药品总数Total amount left", min_value=0)
    new_dose = st.number_input("每日剂量Daily dose", min_value=0.0, step=0.1)
    new_note = st.text_input("备注Note", placeholder="例如：医生改剂量Dr change medication dose?")

    if st.button("添加药物Add Medication"):
        new_row = [new_med_name, new_refill_date.strftime("%Y-%m-%d"), new_total, new_dose, new_note]
        stock_sheet.append_row(new_row)
        st.success("✅ 药物记录已添加Done")

with st.expander("📝 修改药物剂量Edit dose"):
    med_options = stock_df['jie'].tolist()
    selected_med = st.selectbox("选择要修改的药物Choose to edit", med_options)
    new_dose_edit = st.number_input("新的每日剂量New medication dose", min_value=0.0, step=0.1)

    if st.button("更新剂量Update dose"):
        cell = stock_sheet.find(selected_med)
        if cell:
            row_num = cell.row
            stock_sheet.update_cell(row_num, 4, new_dose_edit)
            st.success(f"✅ {selected_med} 剂量已更新为 {new_dose_edit}")
