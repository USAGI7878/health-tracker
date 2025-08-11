import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from twilio.rest import Client
import datetime

# 设置页面标题
st.set_page_config(page_title="血压 & 血糖趋势图", layout="centered")
st.subheader("📈 血压 & 血糖趋势图表")

# ✅ 用 Streamlit 的 secrets.toml 做 Google Sheets 授权
# 从 st.secrets 读取认证信息

creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)
client = gspread.authorize(creds)
# 连接 Google Sheet
gc = gspread.authorize(creds)
# 替换成以下这段
try:
    spreadsheet = gc.open("BP-Glucose-Tracker")
    st.success("✅ 成功连接 Google Sheet！")
except Exception as e:
    st.error(f"❌ 连接失败：{e}")


# ✅ Twilio 授权（记得填入 secrets.toml）
account_sid = st.secrets["twilio"]["account_sid"]
auth_token = st.secrets["twilio"]["auth_token"]
twilio_client = Client(account_sid, auth_token)

# ✅ 打开 Google Sheet（推荐用 sheet name + worksheet name）
spreadsheet = gc.open("BP-Glucose-Tracker")  # Google Sheet 名字
worksheet = spreadsheet.worksheet("Sheet1")  # 第一个 Sheet

# 转换为 DataFrame
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# 自动识别日期栏位名
date_col = "Date" if "Date" in df.columns else ("日期" if "日期" in df.columns else None)

if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df["Date"] = df[date_col].dt.strftime('%Y-%m-%d')  # 格式标准化

    if st.toggle("📊 显示趋势图表"):
        df_sorted = df.sort_values(by="Date")
        
        # 血压趋势图
        st.markdown("#### 🫀 血压趋势（收缩压 / 舒张压）")
        st.line_chart(df_sorted[["Date", "Systolic", "Diastolic"]].set_index("Date"))

        # 脉搏趋势图
        st.markdown("#### 💓 脉搏趋势")
        st.line_chart(df_sorted[["Date", "Pulse"]].set_index("Date"))

        # 血糖趋势图
        st.markdown("#### 🍬 血糖趋势")
        st.line_chart(df_sorted[["Date", "Glucose(mmol/L)"]].set_index("Date"))

    # ✅ 显示表格
    st.subheader("🩺 血压和血糖记录表格")
    st.dataframe(df)

    # ✅ 筛选器
    with st.expander("🔍 数据筛选"):
        date_filter = st.date_input("选择日期查看记录")
        filtered_df = df[df["Date"] == date_filter.strftime("%Y-%m-%d")]
        st.dataframe(filtered_df)
else:
    st.warning("⚠️ 没有找到 Date 或 日期 栏位，无法筛选与绘图。")


# 选择 Sheet1（血压血糖）
worksheet = spreadsheet.worksheet("Sheet1")
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# 🧠 1. 栏位映射（先做）
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

# ✅ 2. 检查栏位是否存在
if "Date" in df.columns:
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.strftime('%Y-%m-%d')
else:
    st.warning("⚠️ 没有找到日期栏位，图表和筛选功能将无法使用。")

# ✅ 3. 样式美化
st.markdown("""
    <style>
        .big-font {
            font-size: 24px !important;
        }
        .contrast-mode {
            background-color: black !important;
            color: white !important;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-font">📋 血压 & 血糖记录查看</div>', unsafe_allow_html=True)


if st.checkbox("🔍 开启大字体 / High Contrast"):
    st.markdown('<style>body {font-size: 24px; background-color: #f8f9fa;}</style>', unsafe_allow_html=True)

# 展示最近 5 笔记录
st.subheader("🕒 最近记录")
st.dataframe(df.tail(5), use_container_width=True)

st.subheader("📝 新增记录")

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
        systolic = st.number_input("收缩压（Systolic）", min_value=50, max_value=250)
        diastolic = st.number_input("舒张压（Diastolic）", min_value=30, max_value=150)
        pulse = st.number_input("脉搏（Pulse）", min_value=30, max_value=180)
        glucose = st.number_input("血糖（mmol/L）", min_value=1.0, max_value=20.0, format="%.1f")

    bp_note = st.text_input("血压备注", placeholder="例如：感觉头晕、还好等")
    glucose_note = st.text_input("血糖备注", placeholder="例如：空腹后测量、饭后两小时等")

    submitted = st.form_submit_button("✅ 提交记录")

    if submitted:
        bp_status = "高" if systolic > 140 or diastolic > 90 else "正常"
        glucose_status = "高" if glucose > 7.8 else ("低" if glucose < 3.9 else "正常")

        # 插入数据到 Google Sheet
        new_row = [
            str(date), time_of_day, took_med, medication, before_after, dose,
            systolic, diastolic, pulse, bp_status, bp_note, glucose, glucose_status, glucose_note
        ]
        worksheet.append_row(new_row)
        st.success("✅ 记录已成功提交！")

st.markdown("### 💊 药物库存提醒")

# 读取第二个 worksheet
stock_sheet = spreadsheet.worksheet("Medication Stock")
stock_data = stock_sheet.get_all_records()
stock_df = pd.DataFrame(stock_data)

# 添加剩余天数的估算
stock_df['Refill Date'] = pd.to_datetime(stock_df['Refill Date'])
stock_df['Remaining Days'] = (stock_df['Total Given'] / stock_df['Dose Per Day']).astype(int)
stock_df['Estimated Finish Date'] = stock_df['Refill Date'] + pd.to_timedelta(stock_df['Remaining Days'], unit='d')

# 判断是否少于7天
today = datetime.datetime.today()
stock_df['Warning'] = stock_df['Estimated Finish Date'].apply(lambda x: "⚠️ 快用完了！" if (x - today).days <= 7 else "")

# 显示提醒
st.dataframe(stock_df[['jie', 'Total Given', 'Dose Per Day', 'Estimated Finish Date', 'Warning']])

with st.expander("➕ 添加新药物记录"):
    new_med_name = st.text_input("药物名称")
    new_refill_date = st.date_input("补药日期")
    new_total = st.number_input("药品总数", min_value=0)
    new_dose = st.number_input("每日剂量", min_value=0.0, step=0.1)
    new_note = st.text_input("备注", placeholder="例如：医生改剂量")

    if st.button("添加药物"):
        new_row = [new_med_name, new_refill_date.strftime("%Y-%m-%d"), new_total, new_dose, new_note]
        stock_sheet.append_row(new_row)
        st.success("✅ 药物记录已添加")

with st.expander("📝 修改药物剂量"):
    med_options = stock_df['jie'].tolist()
    selected_med = st.selectbox("选择要修改的药物", med_options)
    new_dose = st.number_input("新的每日剂量", min_value=0.0, step=0.1)

    if st.button("更新剂量"):
        # 找到对应行
        cell = stock_sheet.find(selected_med)
        if cell:
            row_num = cell.row
            stock_sheet.update_cell(row_num, 4, new_dose)  # 第4列是 Dose Per Day
            st.success(f"✅ {selected_med} 剂量已更新为 {new_dose}")

from twilio.rest import Client

client = Client(account_sid, auth_token)

from_number = st.secrets["twilio"]["from_number"]
to_number = st.secrets["twilio"]["to_number"]

message = client.messages.create(
    body="提醒：妈咪要吃药咯～💊",
    from_=from_number,
    to=to_number
)

print(message.sid)
