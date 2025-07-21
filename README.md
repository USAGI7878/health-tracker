# Health Tracker
An elderly-friendly Streamlit web app to track blood pressure, glucose levels, and medication reminders, powered by Google Sheets and Twilio.

## 📌 Features
👵 Designed for elderly users – clean UI and large buttons

🩸 Blood pressure & glucose tracking – easy manual input, stored in Google Sheets

💊 Medication reminders – supports dose changes, low stock alerts

⏰ Twilio WhatsApp notifications – auto-send reminders at specific times

☁️ Cloud deployment – no need to install anything, just open the link

## 🧑‍💻 Tech Stack
Tech	Purpose
Streamlit	Web interface
gspread	Google Sheets API
Twilio	WhatsApp reminders
Python	Backend logic
Google Sheets	Cloud database

## 🔧 Setup
💡 Note: You need to have a Google service account key and a Twilio account for full functionality.

1：Clone this repo

bash：
git clone https://github.com/yourusername/health-tracker.git
cd health-tracker

2：Install dependencies

bash：
pip install -r requirements.txt

3：Add your .env or fill in your credentials in secrets.toml (if Streamlit Cloud)

4：Run the app

bash：
streamlit run main.py
## 📸 Screenshots

📍 Main Interface
📍 Medication reminder alert via WhatsApp
📍 Glucose trend line chart

## 📝 Future Improvements
 Admin dashboard for caregivers

 Add user login with Firebase

 Export reports to PDF

 Add multilingual support (e.g., 中文, BM)

## 🙋 About Me
Made by Peggy — a nurse with coding passion 👩‍⚕️💻

Interested in health tech & AI for elderly care.
Contact: peggy8526123@gmail.com
