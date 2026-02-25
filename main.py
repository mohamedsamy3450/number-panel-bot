import time
import re
import os
import requests
import json
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

# ====================== Configuration ======================
LOGIN_PAGE = "http://51.89.99.105/NumberPanel/login"
OTP_PAGE = "http://51.89.99.105/NumberPanel/agent/SMSCDRReports"

# Get credentials from environment variables
CHEKER_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GROUP_CHAT_IDS_STR = os.getenv("TELEGRAM_GROUP_CHAT_IDS", "")
GROUP_CHAT_IDS = [id.strip() for id in GROUP_CHAT_IDS_STR.split(",") if id.strip()]
USERNAME = os.getenv("LOGIN_USERNAME", "mohamedsamy").strip()
PASSWORD = os.getenv("LOGIN_PASSWORD", "0102068678Mm").strip()
TELEGRAM_CHANNEL_LINK = os.getenv("TELEGRAM_CHANNEL_LINK", "")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "")

POLL_INTERVAL_SECONDS = 20.0
MAX_LOGIN_RETRIES = 5
OTP_QUEUE_FILE = "otp_queue.json"

def open_driver(headless=True):
    chrome_options = Options()
    
    # Advanced Stealth settings
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Randomize User-Agent slightly to avoid static fingerprinting
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ]
    chrome_options.add_argument(f"user-agent={random.choice(user_agents)}")
    
    if headless:
        chrome_options.add_argument("--headless=new")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Stealth: Mask webdriver
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
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

def human_type(element, text):
    """Types text like a human with random delays"""
    element.clear()
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2))

def send_telegram_message(chat_id: str, text: str, reply_markup: dict | None = None):
    payload = {
        "chat_id": chat_id, 
        "text": text, 
        "parse_mode": "HTML", 
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        r = requests.post(f"https://api.telegram.org/bot{CHEKER_BOT_TOKEN}/sendMessage", data=payload, timeout=15)
        return r
    except Exception as e:
        print(f"⚠️ Error sending Telegram message: {e}")
        return None

def get_sms_rows(html: str):
    soup = BeautifulSoup(html, "html.parser")
    rows = []
    table = soup.find("table", {"id": "dt"})
    if not table: return rows
    tbody = table.find("tbody")
    if not tbody: return rows
    
    all_trs = tbody.find_all("tr")
    for tr in all_trs:
        tds = tr.find_all("td")
        if len(tds) < 6: continue
        date = tds[0].get_text(strip=True)
        number = tds[2].get_text(strip=True)
        cli = tds[3].get_text(strip=True)
        client = tds[4].get_text(strip=True)
        sms = tds[5].get_text("\n", strip=True)
        if not number or not sms or number=="0" or sms=="0": continue
        rows.append((date, number, cli, client, sms))
    return rows

def get_country_with_flag(number):
    country_flags = {'98':'🇮🇷','91':'🇮🇳','1':'🇺🇸','44':'🇬🇧','86':'🇨🇳','81':'🇯🇵','82':'🇰🇷','65':'🇸🇬','60':'🇲🇾','63':'🇵🇭','84':'🇻🇳','66':'🇹🇭','62':'🇮🇩','92':'🇵🇰','880':'🇧🇩','93':'🇦🇫','94':'🇱🇰','95':'🇲🇲','975':'🇧🇹','977':'🇳🇵','971':'🇦🇪','966':'🇸🇦','974':'🇶🇦','973':'🇧🇭','968':'🇴🇲','964':'🇮🇶','963':'🇸🇾','962':'🇯🇴','961':'🇱🇧','20':'🇪🇬','90':'🇹🇷','967':'🇾🇪','221':'🇸🇳','222':'🇲🇷','58':'🇻🇪','260':'🇿🇲','593':'🇪🇨'}
    for code, flag in country_flags.items():
        if number.startswith(code): return f"{flag} {get_country_name(code)}"
    return "🌐 Unknown Country"

def get_country_name(code):
    country_names = {'98':'Iran','91':'India','1':'USA','44':'UK','86':'China','81':'Japan','82':'South Korea','65':'Singapore','60':'Malaysia','63':'Philippines','84':'Vietnam','66':'Thailand','62':'Indonesia','92':'Pakistan','880':'Bangladesh','93':'Afghanistan','94':'Sri Lanka','95':'Myanmar','975':'Bhutan','977':'Nepal','971':'UAE','966':'Saudi Arabia','974':'Qatar','973':'Bahrain','968':'Oman','964':'Iraq','963':'Syria','962':'Jordan','961':'Lebanon','20':'Egypt','90':'Turkey','967':'Yemen','221':'Senegal','222':'Mauritania','58':'Venezuela','260':'Zambia','593':'Ecuador'}
    return country_names.get(code,'Unknown')

def extract_otp(sms_text):
    numbers = re.findall(r'\b\d{4,8}\b', sms_text)
    if numbers: return numbers[0]
    hyphen_otp = re.findall(r'\b\d{3,4}-\d{3,4}\b', sms_text)
    if hyphen_otp: return hyphen_otp[0]
    return None

def format_message(date, number, cli, client, sms):
    masked_number = number[:3] + '**' + number[5:] if len(number) > 5 else number
    country_with_flag = get_country_with_flag(number)
    service = cli if cli and cli.strip() and cli != "0" else "Verification"
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
    if op=='/': return a//b if b!=0 else None
    return None

def auto_login(driver, username, password):
    for attempt in range(1, MAX_LOGIN_RETRIES+1):
        try:
            print(f"🔄 Login attempt {attempt}/{MAX_LOGIN_RETRIES} for user: {username}")
            driver.get(LOGIN_PAGE)
            time.sleep(random.uniform(2, 4))
            
            # Find elements
            user_el = try_find_element(driver, [(By.NAME,"username"),(By.ID,"username"),(By.XPATH,"//input[@type='text']")])
            pass_el = try_find_element(driver, [(By.NAME,"password"),(By.ID,"password"),(By.XPATH,"//input[@type='password']")])
            
            # Human-like typing
            human_type(user_el, username)
            time.sleep(random.uniform(0.5, 1.5))
            human_type(pass_el, password)
            time.sleep(random.uniform(0.5, 1.5))
            
            # Solve Captcha
            captcha_text = ""
            try:
                lbl = driver.find_element(By.XPATH,"//label[contains(.,'What')]")
                captcha_text = lbl.text.strip()
            except:
                m = re.search(r'(-?\d+\s*[\+\-\*/xX]\s*-?\d+)', driver.page_source)
                if m: captcha_text = m.group(1)
            
            captcha_answer = parse_simple_math(captcha_text)
            if captcha_answer is not None:
                try:
                    cap_input = try_find_element(driver, [(By.NAME,"capt"),(By.XPATH,"//input[@placeholder='Your answer']")], timeout=3)
                    human_type(cap_input, str(captcha_answer))
                    print(f"✅ Captcha solved: {captcha_text} = {captcha_answer}")
                except:
                    print("⚠️ Captcha input not found")
            
            # Click Login
            login_btn = try_find_element(driver, [(By.XPATH,"//button[@type='submit']"),(By.ID,"login_btn")])
            ActionChains(driver).move_to_element(login_btn).click().perform()
            
            time.sleep(5)
            
            # Success Check
            curr_url = driver.current_url
            if any(x in curr_url for x in ["SMSDashboard", "SMSCDRReports", "agent"]):
                print(f"🎉 Login SUCCESSFUL (attempt {attempt})")
                return True
            
            # If still on login page, check for error messages
            print(f"❌ Login failed (attempt {attempt}). Current URL: {curr_url}")
            driver.save_screenshot(f"fail_attempt_{attempt}.png")
            
        except Exception as e:
            print(f"⚠️ Error during login attempt {attempt}: {e}")
        
        time.sleep(random.uniform(3, 6))
    return False

def check_for_new_otps(driver):
    try:
        driver.get(OTP_PAGE)
        time.sleep(3)
        html = driver.page_source
        rows = get_sms_rows(html)
        if not rows: return
        
        last_otp = ""
        if os.path.exists("last_otp_check.txt"):
            with open("last_otp_check.txt", "r") as f: last_otp = f.read().strip()
        
        new_rows = []
        for row in rows:
            row_id = f"{row[0]}_{row[1]}_{row[4]}"
            if row_id == last_otp: break
            new_rows.append(row)
        
        if not new_rows: return
        
        print(f"✨ Found {len(new_rows)} new OTPs!")
        with open("last_otp_check.txt", "w") as f:
            f.write(f"{new_rows[0][0]}_{new_rows[0][1]}_{new_rows[0][4]}")
        
        for row in reversed(new_rows):
            msg = format_message(*row)
            for cid in GROUP_CHAT_IDS: send_telegram_message(cid, msg)
            
    except Exception as e:
        print(f"⚠️ Error checking OTPs: {e}")

def main():
    print("🚀 Starting Number Panel Bot...")
    driver = None
    try:
        driver = open_driver(headless=True)
        if not auto_login(driver, USERNAME, PASSWORD):
            print("❌ Critical: Could not login. Exiting.")
            return
        
        while True:
            if "login" in driver.current_url.lower():
                print("⚠️ Session lost, re-logging in...")
                if not auto_login(driver, USERNAME, PASSWORD):
                    time.sleep(60); continue
            
            check_for_new_otps(driver)
            time.sleep(POLL_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        print("👋 Stopped.")
    finally:
        if driver: driver.quit()

if __name__ == "__main__":
    main()
