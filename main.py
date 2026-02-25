import time
import re
import os
import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

# ====================== Configuration ======================
LOGIN_PAGE = "http://51.89.99.105/NumberPanel/login"
OTP_PAGE = "http://51.89.99.105/NumberPanel/agent/SMSCDRReports"

# Get credentials from environment variables
CHEKER_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GROUP_CHAT_IDS_STR = os.getenv("TELEGRAM_GROUP_CHAT_IDS", "")
GROUP_CHAT_IDS = [id.strip() for id in GROUP_CHAT_IDS_STR.split(",") if id.strip()]
USERNAME = os.getenv("LOGIN_USERNAME", "").strip()
PASSWORD = os.getenv("LOGIN_PASSWORD", "").strip()
TELEGRAM_CHANNEL_LINK = os.getenv("TELEGRAM_CHANNEL_LINK", "")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "")

POLL_INTERVAL_SECONDS = 20.0
MAX_LOGIN_RETRIES = 3
OTP_QUEUE_FILE = "otp_queue.json"

def open_driver(headless=True):
    chrome_options = Options()
    
    # الإعدادات الأساسية المطلوبة لـ Railway
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--window-size=1920,1080")
    
    if headless:
        chrome_options.add_argument("--headless")
    
    # استخدام webdriver-manager علشان يدير الـ Driver تلقائياً
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    driver.set_page_load_timeout(120)
    driver.implicitly_wait(10)
    return driver

def try_find_element(driver, locators, timeout=10):
    for by, sel in locators:
        try:
            return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, sel)))
        except Exception:
            continue
    raise Exception(f"Element not found for any of: {locators}")

def send_telegram_message(chat_id: str, text: str, reply_markup: dict | None = None):
    """
    টেলিগ্রাম মেসেজ পাঠায় এবং ইনলাইন বাটন যোগ করার জন্য reply_markup সমর্থন করে।
    """
    payload = {
        "chat_id": chat_id, 
        "text": text, 
        "parse_mode": "HTML", 
        "disable_web_page_preview": True
    }
    
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = requests.post(f"https://api.telegram.org/bot{CHEKER_BOT_TOKEN}/sendMessage", data=payload, timeout=15)
            if r.status_code == 200 and r.json().get('ok'):
                print(f"✅ Message sent to group {chat_id}")
                return r
            elif r.status_code == 429:
                response_data = r.json()
                retry_after = response_data.get('parameters', {}).get('retry_after', 5)
                print(f"⚠️ Rate limit hit! Waiting {retry_after} seconds...")
                time.sleep(retry_after + 1)
            else:
                print(f"⚠️ Failed to send to {chat_id}: {r.status_code} - {r.text[:100]}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        except Exception as e:
            print(f"⚠️ Exception sending to {chat_id} (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
    print(f"❌ Failed to send message to {chat_id} after {max_retries} attempts")
    return None

def get_sms_rows(html: str):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    table = soup.find("table", {"id": "dt"})
    if not table: 
        print("⚠️ Table with id='dt' not found")
        return rows
    tbody = table.find("tbody")
    if not tbody: 
        print("⚠️ Table body not found")
        return rows
    
    all_trs = tbody.find_all("tr")
    
    filtered_count = 0
    for idx, tr in enumerate(all_trs):
        tds = tr.find_all("td")
        
        if len(tds) < 6:
            filtered_count += 1
            continue
            
        date = tds[0].get_text(strip=True)
        number = tds[2].get_text(strip=True)
        cli = tds[3].get_text(strip=True)
        client = tds[4].get_text(strip=True)
        sms = tds[5].get_text("\n", strip=True)
        
        # Skip empty rows or system messages
        if not number or not sms or number=="0" or sms=="0": 
            filtered_count += 1
            continue
        
        # Skip rows that look like system messages
        if "CDR Data" in date or "Refresh" in date:
            filtered_count += 1
            continue
        
        rows.append((date, number, cli, client, sms))
    
    return rows

def get_country_with_flag(number):
    country_flags = {
        '98':'🇮🇷','91':'🇮🇳','1':'🇺🇸','44':'🇬🇧','86':'🇨🇳','81':'🇯🇵','82':'🇰🇷','65':'🇸🇬','60':'🇲🇾','63':'🇵🇭',
        '84':'🇻🇳','66':'🇹🇭','62':'🇮🇩','92':'🇵🇰','880':'🇧🇩','93':'🇦🇫','94':'🇱🇰','95':'🇲🇲','975':'🇧🇹','977':'🇳🇵',
        '971':'🇦🇪','966':'🇸🇦','974':'🇶🇦','973':'🇧🇭','968':'🇴🇲','964':'🇮🇶','963':'🇸🇾','962':'🇯🇴','961':'🇱🇧',
        '20':'🇪🇬','90':'🇹🇷','967':'🇾🇪','221':'🇸🇳','222':'🇲🇷','58':'🇻🇪','260':'🇿🇲','593':'🇪🇨'
    }
    for code, flag in country_flags.items():
        if number.startswith(code):
            return f"{flag} {get_country_name(code)}"
    return "🌐 Unknown Country"

def get_country_name(code):
    country_names = {
        '98':'Iran','91':'India','1':'USA','44':'UK','86':'China','81':'Japan','82':'South Korea','65':'Singapore','60':'Malaysia','63':'Philippines',
        '84':'Vietnam','66':'Thailand','62':'Indonesia','92':'Pakistan','880':'Bangladesh','93':'Afghanistan','94':'Sri Lanka','95':'Myanmar',
        '975':'Bhutan','977':'Nepal','971':'UAE','966':'Saudi Arabia','974':'Qatar','973':'Bahrain','968':'Oman','964':'Iraq','963':'Syria',
        '962':'Jordan','961':'Lebanon','20':'Egypt','90':'Turkey','967':'Yemen','221':'Senegal','222':'Mauritania','58':'Venezuela','260':'Zambia','593':'Ecuador'
    }
    return country_names.get(code,'Unknown')

def get_country_name_from_number(number):
    country_flags = {
        '98':'Iran','91':'India','1':'USA','44':'UK','86':'China','81':'Japan','82':'South Korea','65':'Singapore','60':'Malaysia','63':'Philippines',
        '84':'Vietnam','66':'Thailand','62':'Indonesia','92':'Pakistan','880':'Bangladesh','93':'Afghanistan','94':'Sri Lanka','95':'Myanmar',
        '975':'Bhutan','977':'Nepal','971':'UAE','966':'Saudi Arabia','974':'Qatar','973':'Bahrain','968':'Oman','964':'Iraq','963':'Syria',
        '962':'Jordan','961':'Lebanon','20':'Egypt','90':'Turkey','967':'Yemen','221':'Senegal','222':'Mauritania','58':'Venezuela','260':'Zambia','593':'Ecuador'
    }
    for code, name in country_flags.items():
        if number.startswith(code):
            return name
    return "Unknown"

def detect_service(sms_text):
    text_lower = sms_text.lower()
    services = {'whatsapp':'WhatsApp','telegram':'Telegram','facebook':'Facebook','google':'Google','apple':'Apple','instagram':'Instagram','twitter':'Twitter','amazon':'Amazon','microsoft':'Microsoft',
                'netflix':'Netflix','bank':'Bank','paypal':'PayPal','binance':'Binance','grab':'Grab','gojek':'Gojek','line':'Line','wechat':'WeChat','viber':'Viber','signal':'Signal','discord':'Discord'}
    for k,v in services.items():
        if k in text_lower: return v
    return "Unknown Service"

def extract_otp(sms_text):
    numbers = re.findall(r'\b\d{4,8}\b', sms_text)
    if numbers: return numbers[0]
    hyphen_otp = re.findall(r'\b\d{3,4}-\d{3,4}\b', sms_text)
    if hyphen_otp: return hyphen_otp[0]
    return None

def format_message(date, number, cli, client, sms):
    if len(number) > 5:
        masked_number = number[:3] + '**' + number[5:]
    else:
        masked_number = number
    country_with_flag = get_country_with_flag(number)
    country_name = get_country_name_from_number(number)
    # استخدم الـ CLI (80088) كاسم للخدمة
    service = cli if cli and cli.strip() and cli != "0" else detect_service(sms)
    otp_code = extract_otp(sms)
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    
    return f"""🎯 <b>NEW VERIFICATION CODE</b> 🎯

<b>📍 Location:</b> {country_with_flag}
<b>🔰 Service:</b> <code>{service}</code>
<b>📞 Number:</b> <code>{masked_number}</code>

<b>┏━━━━━━━━━━━━━━━━┓</b>
<b>┃  🔐 CODE: </b><code><b><u>{otp_code if otp_code else 'N/A'}</u></b></code><b>  ┃</b>
<b>┗━━━━━━━━━━━━━━━━┛</b>

<b>⏰ Received:</b> <i>{current_time}</i>

<b>📨 Full Message:</b>
<blockquote expandable>{sms}</blockquote>

👨‍💻 <b>Developer:</b> @XxXxDeVxXxX"""

def parse_simple_math(text):
    if not text: return None
    m = re.search(r'(-?\d+)\s*([\+\-\*/xX])\s*(-?\d+)', text)
    if not m: return None
    a=int(m.group(1)); op=m.group(2); b=int(m.group(3))
    if op=='+': return a+b
    if op=='-': return a-b
    if op in ['*','x','X']: return a*b
    if op=='/':
        try: return a//b
        except: return None
    return None

def auto_login(driver, username, password):
    for attempt in range(1, MAX_LOGIN_RETRIES+1):
        try:
            driver.get(LOGIN_PAGE)
            time.sleep(1)
            username_el = try_find_element(driver, [(By.NAME,"username"),(By.ID,"username"),(By.NAME,"user"),(By.XPATH,"//input[@type='text']")])
            password_el = try_find_element(driver, [(By.NAME,"password"),(By.ID,"password"),(By.NAME,"pass"),(By.XPATH,"//input[@type='password']")])
            
            print(f"DEBUG: FULL DATA - Username: '{username}', Password: '{password}'")
            
            username_el.clear()
            for char in username:
                username_el.send_keys(char)
                time.sleep(0.1)
                
            password_el.clear()
            for char in password:
                password_el.send_keys(char)
                time.sleep(0.1)
            time.sleep(0.3)
            captcha_text=""
            try:
                lbl = driver.find_element(By.XPATH,"//label[contains(.,'What')]")
                captcha_text=lbl.text.strip()
            except:
                page_txt=driver.page_source
                m=re.search(r'(-?\d+\s*[\+\-\*/xX]\s*-?\d+)', page_txt)
                if m: captcha_text=m.group(1)
            captcha_answer = parse_simple_math(captcha_text)
            if captcha_answer is not None:
                try:
                    captcha_input = try_find_element(driver, [(By.NAME,"capt"),(By.XPATH,"//input[@placeholder='Your answer']"),(By.NAME,"answer"),(By.NAME,"captcha")], timeout=3)
                    captcha_input.clear(); captcha_input.send_keys(str(captcha_answer))
                    print("✅ Captcha auto-filled:", captcha_answer)
                except Exception as e:
                    print(f"⚠️ Captcha field not found, continuing without it...")
            login_btn = try_find_element(driver, [(By.XPATH,"//button[@type='submit']"),(By.XPATH,"//button[contains(text(),'LOGIN')]"),(By.XPATH,"//button[contains(.,'Sign In') or contains(.,'Login')]"),(By.XPATH,"//input[@type='submit']"),(By.ID,"login_btn")])
            login_btn.click()
            time.sleep(3)
            
            # التحقق من نجاح تسجيل الدخول
            current_url = driver.current_url
            page_source = driver.page_source.lower()
            
            # فحص رسائل الخطأ الشائعة
            error_indicators = ['invalid', 'incorrect', 'wrong', 'failed', 'error', 'خطأ', 'غير صحيح']
            has_error = any(indicator in page_source for indicator in error_indicators)
            
            # إذا لا يوجد خطأ، جرب الذهاب لصفحة OTP
            if not has_error:
                try:
                    driver.get(OTP_PAGE)
                    time.sleep(2)
                    
                    # تحقق من أننا في الصفحة الصحيحة
                    if "SMSCDRStats" in driver.current_url or "dt" in driver.page_source:
                        print(f"✅ Auto-login successful (attempt {attempt})")
                        return True
                    else:
                        print(f"⚠️ Could not access OTP page (attempt {attempt})")
                except:
                    pass
            else:
                print(f"❌ Login failed: Invalid credentials detected (attempt {attempt}). Current URL: {driver.current_url}")
            
        except Exception as e:
            print(f"⚠️ Login attempt {attempt} failed: {e}")
        
        time.sleep(3)
    
    return False

def get_otp_page_html(driver):
    driver.refresh()
    
    # Handle any alerts that may appear
    try:
        alert = driver.switch_to.alert
        alert.accept()
        time.sleep(0.3)
    except:
        pass
    
    # Wait longer for DataTables to load via JavaScript/AJAX
    time.sleep(3)
    
    # Wait for table to have actual data rows (not just loading row)
    max_wait = 10
    for i in range(max_wait):
        try:
            # Check if table has loaded with data
            soup = BeautifulSoup(driver.page_source, "html.parser")
            table = soup.find("table", {"id": "dt"})
            if table:
                tbody = table.find("tbody")
                if tbody:
                    rows = tbody.find_all("tr")
                    if rows and len(rows) > 0:
                        first_row_tds = rows[0].find_all("td")
                        # If first row has more than 1 column, data is loaded
                        if len(first_row_tds) > 1:
                            break
        except:
            pass
        time.sleep(1)
    
    return driver.page_source

def main_loop():
    driver = open_driver(headless=True)
    if not auto_login(driver, USERNAME, PASSWORD):
        print("❌ Login failed after retries.")
        driver.quit()
        return

    sent_ids = set()
    print("🚀 SMS forwarding started")
    
    loop_count = 0

    try:
        while True:
            loop_count += 1
            html = get_otp_page_html(driver)
            rows = get_sms_rows(html)
            
            # عكس ترتيب الرسائل عشان نبدأ بالأحدث (الأول في الجدول)
            rows = list(reversed(rows))
            
            new_messages = 0
            for date, number, cli, client, sms in rows:
                # ডুপ্লিকেট প্রতিরোধের জন্য ইউনিক আইডি তৈরি
                unique_id = f"{date}|{number}|{sms[:30]}"
                if unique_id not in sent_ids:
                    new_messages += 1
                    msg = format_message(date, number, cli, client, sms)
                    print(f"📩 New SMS #{new_messages}: {number} - {sms[:40]}...")
                    
                    # --- টেলিগ্রাম ইনলাইন বাটন তৈরি করা হচ্ছে ---
                    # 1. মেইন চ্যানেল বাটন (Channel Link)
                    # 2. নাম্বার বট বাটন (Bot User Name Link)
                    inline_keyboard_markup = {
                        "inline_keyboard": [
                            [
                                {"text": "📢 Channel", "url": TELEGRAM_CHANNEL_LINK}
                            ],
                            [
                                {"text": "🤖 Get Your Number", "url": f"https://t.me/{TELEGRAM_BOT_USERNAME.lstrip('@')}"}
                            ]
                        ]
                    }
                    # --- বাটন ডেটা تৈরি শেষ ---
                    
                    # গ্রুপে মেসেজ পাঠানো হচ্ছে
                    for chat_id in GROUP_CHAT_IDS:
                        send_telegram_message(chat_id, msg, reply_markup=inline_keyboard_markup)
                        time.sleep(0.5)
                    
                    # OTP ডেটা ফাইলে সংরক্ষণ করা হচ্ছে
                    otp_data = {
                        "number": number,
                        "otp": extract_otp(sms),
                        "service": detect_service(sms)
                    }
                    try:
                        with open(OTP_QUEUE_FILE, "a", encoding="utf-8") as f:
                            json.dump(otp_data, f)
                            f.write('\n')
                        print(f"✅ OTP data queued for number: {number}")
                    except Exception as e:
                        print(f"⚠️ Failed to write to OTP file: {e}")
                    
                    sent_ids.add(unique_id)
            
            if new_messages > 0:
                print(f"✅ Sent {new_messages} new messages to Telegram")
            
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("❌ Stopped by user.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main_loop()
