# Health Tracker 健康追踪器
An elderly-friendly Streamlit web app to track blood pressure, glucose levels, and medication reminders, powered by Google Sheets, Twilio, OCR, and AI chat.

## 📌 Features
- 👵 **Elderly-friendly design** – Large fonts, clean UI, easy navigation
- 📸 **OCR Photo Upload** – Snap a photo of BP/glucose meters, auto-read numbers
- 🩸 **Health Tracking** – Blood pressure & glucose monitoring with trend charts
- 💊 **Medication Management** – Stock tracking, low inventory alerts, dose adjustments
- 🤖 **Free AI Health Assistant** – Powered by Groq API, analyzes trends and gives advice
- ⏰ **WhatsApp Reminders** – Twilio integration for medication alerts
- ☁️ **Cloud Deployment** – Access anywhere via web link
- 📊 **Multi-Page Layout** – Organized pages for data entry, charts, medications, and AI chat

## 🧑‍💻 Tech Stack
| Tech | Purpose |
|------|---------|
| Streamlit | Web interface |
| gspread | Google Sheets API |
| Twilio | WhatsApp reminders |
| Tesseract OCR | Photo text recognition |
| Groq API | Free AI chat assistant |
| Python | Backend logic |
| Google Sheets | Cloud database |

## 🔧 Setup

### Prerequisites
- Python 3.8+
- Google Service Account
- Twilio Account
- Groq API Key (free)
- Tesseract OCR installed

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/yourusername/health-tracker.git
cd health-tracker
```

### 2️⃣ Install Python Dependencies
```bash
pip install -r requirements.txt
```

**Your requirements.txt should include:**
```
streamlit
pandas
gspread
google-auth
google-cloud-vision
twilio
Pillow
requests
```

### 3️⃣ Enable Google Cloud Vision API

**Important:** You need to enable the Vision API in your Google Cloud Console:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (same one you used for Google Sheets)
3. Go to **APIs & Services** → **Library**
4. Search for **"Cloud Vision API"**
5. Click **Enable**
6. No new credentials needed - it uses your existing service account!

**For Streamlit Cloud:**
- Remove `packages.txt` (no longer need Tesseract)
- The Vision API works automatically with your existing Google credentials

### 4️⃣ Configure Secrets

**For Local Development:**
Create `.streamlit/secrets.toml`:
```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-key-id"
private_key = """-----BEGIN PRIVATE KEY-----
your-private-key-here
-----END PRIVATE KEY-----"""
client_email = "your-service-account@project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account"
universe_domain = "googleapis.com"

[twilio]
account_sid = "your-twilio-sid"
auth_token = "your-twilio-token"
from_number = "whatsapp:+14155238886"
to_number = "whatsapp:+your-number"

[groq]
api_key = "gsk_your_groq_api_key"
```

**For Streamlit Cloud:**
1. Go to your app settings
2. Navigate to "Secrets" section
3. Paste the same TOML content above

### 5️⃣ Setup Google Sheets
1. Create a Google Sheet named **"BP-Glucose-Tracker"**
2. Create two worksheets:
   - **Sheet1** (for health records)
   - **Medication Stock** (for medication tracking)

**Sheet1 Columns:**
```
日期 | 时间段 | 有吃药吗？ | 药物名称 | 饭前/饭后 | 剂量 | 收缩压 | 舒张压 | 脉搏 | 血压状态 | 血压备注 | 血糖（mmol/L） | 血糖状态 | 血糖备注
```

**Medication Stock Columns:**
```
jie | Refill Date | Total Given | Dose Per Day | Note
```

### 6️⃣ Get API Keys

**Google Service Account:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Sheets API and Google Drive API
4. Create Service Account → Download JSON key
5. Share your Google Sheet with the service account email

**Twilio (WhatsApp):**
1. Sign up at [Twilio](https://www.twilio.com/)
2. Get a WhatsApp sandbox number
3. Copy Account SID and Auth Token

**Groq API (FREE!):**
1. Sign up at [Groq Console](https://console.groq.com/)
2. Get your free API key (14,400 requests/day!)

### 7️⃣ Run the App
```bash
streamlit run main.py
```

## 📸 OCR Tips for Best Results
- ✅ Use **good lighting** (natural daylight is best)
- ✅ Write numbers **clearly and large**
- ✅ Use **dark markers** (black/blue, avoid red/yellow)
- ✅ Hold camera **straight above** (not angled)
- ✅ Avoid **shadows and glare**
- ✅ For whiteboard: use **matte finish** to reduce glare

## 🚀 Deployment

### Deploy to Streamlit Cloud
1. Push your code to GitHub
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Connect your GitHub repo
4. Add secrets in the app settings
5. Deploy!

**Important Files for Deployment:**
- `requirements.txt` - Python packages
- `packages.txt` - System packages (Tesseract)
- `.streamlit/secrets.toml` - API keys (add via Streamlit Cloud UI)

## 📱 App Pages

### 📝 Data Entry
- Upload photos with OCR
- Manual data entry form
- View recent records

### 📊 Charts & Trends
- Blood pressure trends
- Pulse monitoring
- Glucose level tracking
- Statistical summaries
- Date range filtering

### 💊 Medication Management
- Stock inventory
- Low stock warnings
- Add new medications
- Update dosages

### 🤖 AI Health Assistant
- Ask questions about health data
- Get trend analysis
- Receive personalized advice
- Chat history

## 📝 Future Improvements
- [ ] PDF report export for doctors
- [ ] Multi-user support with login
- [ ] Printable tracking templates
- [ ] Email notifications
- [ ] Voice input for data entry
- [ ] Integration with fitness trackers
- [ ] Multilingual support expansion

## 🙋 About
Made by **Peggy** — a nurse passionate about health tech 👩‍⚕️💻

Helping elderly manage their health with simple, accessible technology.

**Contact:** peggy8526123@gmail.com

## 📄 License
MIT License - Feel free to use and modify!

## 🆘 Troubleshooting

### Tesseract not found
```
❌ OCR 错误: tesseract is not installed or it's not in your PATH
```
**Solution:** Install Tesseract (see step 3 above) and ensure it's in your PATH

### Google Sheets connection failed
**Solution:** 
- Check service account email has access to the sheet
- Verify credentials in secrets.toml
- Enable Google Sheets API in Google Cloud Console

### Groq API not working
**Solution:**
- Check API key is correct in secrets.toml
- Verify you haven't exceeded rate limits (14,400/day free tier)
- Check internet connection

### OCR not reading numbers correctly
**Solution:**
- Improve lighting conditions
- Write numbers larger and clearer
- Use darker markers
- Take photo from directly above

---

⭐ If you find this helpful, please star the repo!

🐛 Found a bug? Open an issue on GitHub!
