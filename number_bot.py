import os
import json
import time
import requests
from threading import Thread
import pandas as pd
import io

# Configuration
BOT_TOKEN = os.getenv("NUMBER_BOT_TOKEN", "")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
OTP_GROUP_LINK = os.getenv("OTP_GROUP_LINK", "https://t.me/+QTWTG1P443I5YmJk")
OTP_QUEUE_FILE = "otp_queue.json"
USER_ASSIGNMENTS_FILE = "user_assignments.json"
COUNTRIES_FILE = "countries.json"
LAST_OTP_CHECK_FILE = "last_otp_check.txt"

# Admin states for file upload workflow
admin_states = {}

# Initialize data files
def init_files():
    if not os.path.exists(USER_ASSIGNMENTS_FILE):
        with open(USER_ASSIGNMENTS_FILE, "w") as f:
            json.dump({}, f)
    
    if not os.path.exists(COUNTRIES_FILE):
        with open(COUNTRIES_FILE, "w") as f:
            json.dump({}, f)
    
    if not os.path.exists(LAST_OTP_CHECK_FILE):
        with open(LAST_OTP_CHECK_FILE, "w") as f:
            f.write("0")
    
    # Clean up: Remove already assigned numbers from countries list
    cleanup_assigned_numbers()

def cleanup_assigned_numbers():
    """Remove numbers that are already assigned from the available pool"""
    countries = load_json(COUNTRIES_FILE)
    assignments = load_json(USER_ASSIGNMENTS_FILE)
    
    # Get all assigned numbers
    assigned_numbers = set()
    for user_data in assignments.values():
        if "number" in user_data:
            assigned_numbers.add(user_data["number"])
    
    if not assigned_numbers:
        return
    
    # Remove assigned numbers from countries
    modified = False
    for country, data in countries.items():
        if "numbers" in data:
            original_count = len(data["numbers"])
            data["numbers"] = [num for num in data["numbers"] if num not in assigned_numbers]
            removed = original_count - len(data["numbers"])
            if removed > 0:
                print(f"🧹 Cleaned {removed} assigned numbers from {country}")
                modified = True
    
    if modified:
        save_json(COUNTRIES_FILE, countries)
        print("✅ Cleanup complete")

def load_json(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return None

def answer_callback(callback_query_id, text=""):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id, "text": text}
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def get_admin_menu():
    """Admin keyboard menu"""
    return {
        "keyboard": [
            ["➕ Add Country", "📤 Upload Numbers"],
            ["🗑️ Delete Country", "🧹 Clear Numbers"],
            ["📋 View List", "📊 Statistics"],
            ["👥 Active Users", "📢 Broadcast"]
        ],
        "resize_keyboard": True
    }

def get_user_menu():
    """User keyboard menu - Removed, using command menu instead"""
    return None

# Admin Commands
def handle_admin_add_country(chat_id, message):
    """
    Usage: /addcountry <country_name> <flag_emoji>
    Example: /addcountry Venezuela 🇻🇪
    """
    parts = message.split(maxsplit=2)
    if len(parts) < 3:
        send_message(chat_id, "❌ Usage: /addcountry <country_name> <flag_emoji>\n\nExample: /addcountry Venezuela 🇻🇪")
        return
    
    country_name = parts[1]
    flag = parts[2]
    
    countries = load_json(COUNTRIES_FILE)
    if country_name not in countries:
        countries[country_name] = {"flag": flag, "numbers": []}
        save_json(COUNTRIES_FILE, countries)
        send_message(chat_id, f"✅ Country added: {flag} {country_name}")
    else:
        send_message(chat_id, f"⚠️ Country {country_name} already exists!")

def handle_admin_add_number(chat_id, message):
    """
    Usage: /addnumber <country_name> <phone_number>
    Example: /addnumber Venezuela 584122402006
    """
    parts = message.split()
    if len(parts) < 3:
        send_message(chat_id, "❌ Usage: /addnumber <country_name> <phone_number>\n\nExample: /addnumber Venezuela 584122402006")
        return
    
    country_name = parts[1]
    number = parts[2]
    
    countries = load_json(COUNTRIES_FILE)
    if country_name not in countries:
        send_message(chat_id, f"❌ Country '{country_name}' not found! Add it first with /addcountry")
        return
    
    if number not in countries[country_name]["numbers"]:
        countries[country_name]["numbers"].append(number)
        save_json(COUNTRIES_FILE, countries)
        send_message(chat_id, f"✅ Number added to {countries[country_name]['flag']} {country_name}: +{number}")
    else:
        send_message(chat_id, f"⚠️ Number already exists in {country_name}!")

def download_file(file_id):
    """Download file from Telegram"""
    try:
        # Get file path
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile"
        response = requests.get(url, params={"file_id": file_id}, timeout=10)
        result = response.json()
        
        if not result.get("ok"):
            return None
        
        file_path = result["result"]["file_path"]
        
        # Download file
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        file_response = requests.get(file_url, timeout=30)
        
        return file_response.content
    except Exception as e:
        print(f"❌ Error downloading file: {e}")
        return None

def parse_numbers_from_file(file_content, filename):
    """Parse numbers from Excel, CSV, or Text file"""
    numbers = []
    
    try:
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            # Excel file - read as string to avoid float conversion
            df = pd.read_excel(io.BytesIO(file_content), dtype=str)
            # Get all rows from first column (pandas already skips header)
            if len(df.columns) > 0:
                numbers = df.iloc[:, 0].tolist()
        
        elif filename.endswith('.csv'):
            # Try reading with header first
            try:
                df = pd.read_csv(io.BytesIO(file_content), dtype=str)
                if len(df.columns) > 0:
                    numbers = df.iloc[:, 0].tolist()
            except:
                # If fails, try without header
                df = pd.read_csv(io.BytesIO(file_content), header=None, dtype=str)
                if len(df.columns) > 0:
                    numbers = df.iloc[:, 0].tolist()
        
        else:
            # Text file
            text = file_content.decode('utf-8')
            # Split by newlines and clean
            numbers = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Clean numbers: remove spaces, dashes, plus signs, and .0 suffix
        cleaned_numbers = []
        for num in numbers:
            cleaned = str(num).strip()
            
            # Skip if it's NaN or empty
            if cleaned.lower() in ['nan', 'none', '']:
                continue
            
            # Remove .0 suffix from Excel float conversion
            if cleaned.endswith('.0'):
                cleaned = cleaned[:-2]
            
            # Remove formatting
            cleaned = cleaned.replace(' ', '').replace('-', '').replace('+', '')
            
            # Only add if it looks like a phone number (digits only, reasonable length)
            if cleaned.isdigit() and 8 <= len(cleaned) <= 15:
                cleaned_numbers.append(cleaned)
        
        return cleaned_numbers
    
    except Exception as e:
        print(f"❌ Error parsing file: {e}")
        return []

def show_country_selection_for_upload(chat_id):
    """Show country selection for uploading numbers"""
    countries = load_json(COUNTRIES_FILE)
    
    if not countries:
        send_message(chat_id, "⚠️ No countries available. Add a country first with /addcountry")
        return
    
    keyboard = {"inline_keyboard": []}
    for country, data in countries.items():
        keyboard["inline_keyboard"].append([
            {"text": f"{data['flag']} {country}", "callback_data": f"upload_{country}"}
        ])
    
    send_message(chat_id, "🌍 <b>Select country to upload numbers:</b>", reply_markup=keyboard)

def handle_upload_numbers(chat_id, user_id):
    """Handle upload numbers button"""
    show_country_selection_for_upload(chat_id)

def handle_admin_list(chat_id):
    countries = load_json(COUNTRIES_FILE)
    if not countries:
        send_message(chat_id, "📋 No countries added yet.\n\nUse /addcountry to add countries.")
        return
    
    msg = "📋 <b>Available Countries & Numbers:</b>\n\n"
    for country, data in countries.items():
        msg += f"{data['flag']} <b>{country}</b>\n"
        if data['numbers']:
            msg += f"   📱 Numbers: {len(data['numbers'])}\n"
            for num in data['numbers'][:5]:
                msg += f"      • +{num}\n"
            if len(data['numbers']) > 5:
                msg += f"      ... and {len(data['numbers']) - 5} more\n"
        else:
            msg += "   ⚠️ No numbers available\n"
        msg += "\n"
    
    send_message(chat_id, msg)

# User Commands
def handle_start(chat_id, user_id):
    # Send appropriate menu based on user role
    if user_id == ADMIN_USER_ID:
        send_message(
            chat_id,
            "👋 <b>Welcome Admin!</b>\n\nUse the menu below to manage countries and numbers.",
            reply_markup=get_admin_menu()
        )
    else:
        send_message(
            chat_id,
            "👋 <b>Welcome to Number Bot!</b>\n\nUse the menu button (≡) or commands:\n• /getnumber - Get a number\n• /status - View your OTP\n• /help - How to use"
        )

def show_country_selection(chat_id, user_id):
    countries = load_json(COUNTRIES_FILE)
    assignments = load_json(USER_ASSIGNMENTS_FILE)
    
    # Get all currently assigned numbers
    all_assigned_numbers = set()
    for user_data in assignments.values():
        if "number" in user_data:
            all_assigned_numbers.add(user_data["number"])
    
    # Filter countries that have available (unassigned) numbers
    available_countries = {}
    for country, data in countries.items():
        if "numbers" in data:
            # Count how many numbers are truly available (not assigned)
            available_nums = [num for num in data["numbers"] if num not in all_assigned_numbers]
            if available_nums:
                available_countries[country] = data
    
    if not available_countries:
        send_message(chat_id, "⚠️ No numbers available. Please try again later.")
        return
    
    keyboard = {"inline_keyboard": []}
    for country, data in available_countries.items():
        # Show count of available numbers
        available_count = len([num for num in data["numbers"] if num not in all_assigned_numbers])
        keyboard["inline_keyboard"].append([
            {"text": f"{data['flag']} {country} ({available_count} available)", "callback_data": f"select_{country}"}
        ])
    
    send_message(chat_id, "🌍 <b>Select a Country:</b>", reply_markup=keyboard)

def assign_number_to_user(user_id, country):
    countries = load_json(COUNTRIES_FILE)
    assignments = load_json(USER_ASSIGNMENTS_FILE)
    
    if country not in countries or not countries[country]["numbers"]:
        return None
    
    user_key = str(user_id)
    
    # Get all currently assigned numbers across all users
    all_assigned_numbers = set()
    for uid, data in assignments.items():
        if "number" in data:
            all_assigned_numbers.add(data["number"])
    
    # Get list of available numbers (excluding already assigned ones)
    available_numbers = [
        num for num in countries[country]["numbers"] 
        if num not in all_assigned_numbers
    ]
    
    if not available_numbers:
        print(f"⚠️ No available numbers left in {country}")
        return None
    
    # Check if user is changing number (already has one)
    if user_key in assignments:
        old_number = assignments[user_key]["number"]
        old_country = assignments[user_key]["country"]
        
        # Remove old number permanently (don't add back to list)
        if old_country in countries and old_number in countries[old_country]["numbers"]:
            countries[old_country]["numbers"].remove(old_number)
            print(f"🗑️ Removed old number {old_number} from {old_country}")
    
    # Take first available number from the list
    selected_number = available_numbers[0]
    
    # Sanity check: Make sure number is not already assigned
    if selected_number in all_assigned_numbers:
        print(f"❌ ERROR: Number {selected_number} is already assigned!")
        return None
    
    # Remove the selected number from available numbers
    if selected_number in countries[country]["numbers"]:
        countries[country]["numbers"].remove(selected_number)
    save_json(COUNTRIES_FILE, countries)
    
    # Assign to user
    assignments[user_key] = {
        "number": selected_number,
        "country": country,
        "timestamp": time.time()
    }
    save_json(USER_ASSIGNMENTS_FILE, assignments)
    
    print(f"✅ Assigned {selected_number} from {country} to user {user_id}")
    print(f"📊 Remaining numbers in {country}: {len(countries[country]['numbers'])}")
    
    return selected_number

def handle_status(chat_id, user_id):
    assignments = load_json(USER_ASSIGNMENTS_FILE)
    user_key = str(user_id)
    
    if user_key not in assignments:
        send_message(chat_id, "❌ You don't have a number assigned yet. Use /start to get one.")
        return
    
    number = assignments[user_key]["number"]
    country = assignments[user_key]["country"]
    
    countries = load_json(COUNTRIES_FILE)
    country_data = countries.get(country, {})
    flag = country_data.get("flag", "🌍")
    
    # Get recent OTPs for this number
    recent_otps = get_recent_otps_for_number(number)
    
    msg = f"🌍 <b>Country:</b> {flag} {country}\n"
    msg += f"📱 <b>Number:</b> {number}\n"
    msg += f"🔑 <b>OTP:</b> {recent_otps[0] if recent_otps else 'N/A'}\n"
    
    send_message(chat_id, msg)
    
    # Send recent OTPs
    if recent_otps:
        otp_msg = f"📬 <b>Recent OTPs for +{number}:</b>\n\n"
        for i, otp_info in enumerate(recent_otps[:5], 1):
            otp_msg += f"🔑 {otp_info}\n"
        otp_msg += f"\n📊 <b>Total:</b> {len(recent_otps)} OTPs for your number"
        send_message(chat_id, otp_msg)

def get_recent_otps_for_number(number):
    """Get recent OTPs from otp_queue.json for a specific number"""
    try:
        if not os.path.exists(OTP_QUEUE_FILE):
            return []
        
        otps = []
        with open(OTP_QUEUE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get("number") == number:
                        service = data.get("service", "Unknown")
                        otp = data.get("otp", "N/A")
                        otps.append(f"{otp} ({service})")
                except:
                    continue
        return otps[-10:]  # Return last 10
    except:
        return []

def handle_countries(chat_id):
    countries = load_json(COUNTRIES_FILE)
    
    if not countries:
        send_message(chat_id, "⚠️ No countries available yet.")
        return
    
    msg = "🌍 <b>Available Countries:</b>\n\n"
    for country, data in countries.items():
        available = len([n for n in data.get("numbers", [])])
        msg += f"{data.get('flag', '🌍')} {country}: {available} numbers\n"
    
    send_message(chat_id, msg)

def handle_get_number(chat_id, user_id):
    """Handle Get Number button click"""
    countries = load_json(COUNTRIES_FILE)
    
    if not countries:
        send_message(chat_id, "⚠️ No countries available yet. Please try again later.")
        return
    
    # Always show country selection when user clicks "Get Number"
    show_country_selection(chat_id, user_id)

def handle_help(chat_id):
    """Handle Help button click"""
    msg = "❓ <b>How to use this bot:</b>\n\n"
    msg += "1️⃣ Click '📱 Get Number' to receive a temporary phone number\n"
    msg += "2️⃣ Use the number for OTP verification on any service\n"
    msg += "3️⃣ The OTP will be automatically sent to you here\n"
    msg += "4️⃣ Use '🔄 Change Number' if you need a different number\n"
    msg += "5️⃣ Use '📊 My Status' to check your current number and recent OTPs\n\n"
    msg += "💡 <b>Tip:</b> Each number can be used multiple times for different services!"
    
    send_message(chat_id, msg)

def handle_admin_statistics(chat_id):
    """Handle admin statistics"""
    countries = load_json(COUNTRIES_FILE)
    assignments = load_json(USER_ASSIGNMENTS_FILE)
    
    total_countries = len(countries)
    total_numbers = sum(len(data.get("numbers", [])) for data in countries.values())
    total_users = len(assignments)
    active_numbers = len(set(a["number"] for a in assignments.values()))
    
    msg = "📊 <b>Bot Statistics:</b>\n\n"
    msg += f"🌍 Total Countries: {total_countries}\n"
    msg += f"📱 Total Numbers: {total_numbers}\n"
    msg += f"👥 Total Users: {total_users}\n"
    msg += f"🔥 Active Numbers: {active_numbers}\n"
    
    send_message(chat_id, msg)

def handle_admin_active_users(chat_id):
    """Handle admin active users list"""
    assignments = load_json(USER_ASSIGNMENTS_FILE)
    countries = load_json(COUNTRIES_FILE)
    
    if not assignments:
        send_message(chat_id, "👥 No active users yet.")
        return
    
    msg = "👥 <b>Active Users:</b>\n\n"
    for user_id, assignment in list(assignments.items())[:10]:
        country = assignment["country"]
        number = assignment["number"]
        flag = countries.get(country, {}).get("flag", "🌍")
        msg += f"• User {user_id}\n"
        msg += f"  {flag} {country}: +{number}\n\n"
    
    if len(assignments) > 10:
        msg += f"... and {len(assignments) - 10} more users"
    
    send_message(chat_id, msg)

def handle_admin_delete_country(chat_id, user_id):
    """Handle delete country"""
    countries = load_json(COUNTRIES_FILE)
    
    if not countries:
        send_message(chat_id, "⚠️ No countries available to delete.")
        return
    
    keyboard = {"inline_keyboard": []}
    for country, data in countries.items():
        keyboard["inline_keyboard"].append([
            {"text": f"🗑️ {data['flag']} {country}", "callback_data": f"delete_{country}"}
        ])
    
    send_message(chat_id, "🗑️ <b>Select country to delete:</b>", reply_markup=keyboard)

def handle_admin_clear_numbers(chat_id, user_id):
    """Handle clear numbers from a country"""
    countries = load_json(COUNTRIES_FILE)
    
    if not countries:
        send_message(chat_id, "⚠️ No countries available.")
        return
    
    keyboard = {"inline_keyboard": []}
    for country, data in countries.items():
        num_count = len(data.get("numbers", []))
        keyboard["inline_keyboard"].append([
            {"text": f"🧹 {data['flag']} {country} ({num_count} numbers)", "callback_data": f"clear_{country}"}
        ])
    
    send_message(chat_id, "🧹 <b>Select country to clear all numbers:</b>", reply_markup=keyboard)

def handle_admin_broadcast(chat_id, user_id):
    """Handle broadcast message"""
    admin_states[user_id] = {"action": "broadcast"}
    send_message(
        chat_id,
        "📢 <b>Broadcast Message</b>\n\n"
        "Send me the message you want to send to all active users.\n\n"
        "⚠️ This will be sent to ALL users who have a number assigned."
    )

# Callback Handler
def handle_callback(callback_query):
    query_id = callback_query["id"]
    data = callback_query["data"]
    user_id = callback_query["from"]["id"]
    chat_id = callback_query["message"]["chat"]["id"]
    message_id = callback_query["message"]["message_id"]
    
    # Admin: Upload numbers callback
    if data.startswith("upload_") and user_id == ADMIN_USER_ID:
        country = data.replace("upload_", "")
        admin_states[user_id] = {"action": "upload_numbers", "country": country}
        
        send_message(
            chat_id,
            f"📤 <b>Upload numbers for {country}</b>\n\n"
            f"Send me a file with phone numbers:\n"
            f"• Excel (.xlsx, .xls)\n"
            f"• CSV (.csv)\n"
            f"• Text file (.txt)\n\n"
            f"Numbers should be in the first column or one per line.\n"
            f"Example: 584122402006"
        )
        answer_callback(query_id, f"✅ Ready to receive file for {country}")
        return
    
    # Admin: Delete country callback
    if data.startswith("delete_") and user_id == ADMIN_USER_ID:
        country = data.replace("delete_", "")
        countries = load_json(COUNTRIES_FILE)
        
        if country in countries:
            del countries[country]
            save_json(COUNTRIES_FILE, countries)
            send_message(chat_id, f"✅ Country <b>{country}</b> has been deleted!")
            answer_callback(query_id, f"✅ {country} deleted!")
        else:
            answer_callback(query_id, "❌ Country not found!")
        return
    
    # Admin: Clear numbers callback
    if data.startswith("clear_") and user_id == ADMIN_USER_ID:
        country = data.replace("clear_", "")
        countries = load_json(COUNTRIES_FILE)
        
        if country in countries:
            num_count = len(countries[country].get("numbers", []))
            countries[country]["numbers"] = []
            save_json(COUNTRIES_FILE, countries)
            send_message(chat_id, f"✅ Cleared <b>{num_count}</b> numbers from <b>{country}</b>!")
            answer_callback(query_id, f"✅ {num_count} numbers cleared!")
        else:
            answer_callback(query_id, "❌ Country not found!")
        return
    
    if data == "change_number":
        assignments = load_json(USER_ASSIGNMENTS_FILE)
        user_key = str(user_id)
        
        if user_key in assignments:
            country = assignments[user_key]["country"]
            new_number = assign_number_to_user(user_id, country)
            
            if new_number:
                countries = load_json(COUNTRIES_FILE)
                flag = countries[country]["flag"]
                
                edit_message(
                    chat_id,
                    message_id,
                    f"{flag} <b>{country} Number Assigned:</b>\n+{new_number}\n\n⏳ Waiting for OTP...",
                    reply_markup={
                        "inline_keyboard": [
                            [{"text": "🔄 Change Number", "callback_data": "change_number"}],
                            [{"text": "🌍 Change Country", "callback_data": "change_country"}],
                            [{"text": "📱 OTP Group", "url": OTP_GROUP_LINK}]
                        ]
                    }
                )
                answer_callback(query_id, "✅ Number changed!")
            else:
                answer_callback(query_id, "❌ No numbers available!")
        
    elif data == "change_country":
        show_country_selection(chat_id, user_id)
        answer_callback(query_id)
    
    elif data.startswith("select_"):
        country = data.replace("select_", "")
        number = assign_number_to_user(user_id, country)
        
        if number:
            countries = load_json(COUNTRIES_FILE)
            flag = countries[country]["flag"]
            
            keyboard = {
                "inline_keyboard": [
                    [{"text": "🔄 Change Number", "callback_data": "change_number"}],
                    [{"text": "🌍 Change Country", "callback_data": "change_country"}],
                    [{"text": "📱 OTP Group", "url": OTP_GROUP_LINK}]
                ]
            }
            
            # Delete selection message and send new one with number
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
            requests.post(url, json={"chat_id": chat_id, "message_id": message_id}, timeout=5)

            send_message(
                chat_id,
                f"{flag} <b>{country} Number Assigned:</b>\n<code>+{number}</code>\n\n⏳ Waiting for OTP...",
                reply_markup=keyboard
            )
            answer_callback(query_id, f"✅ {country} number assigned!")
        else:
            answer_callback(query_id, "❌ No numbers available!")

# OTP Monitor (runs in background)
def monitor_otp_queue():
    """Monitor otp_queue.json and send OTPs to users"""
    print("🔍 OTP Monitor started...")
    
    while True:
        try:
            if not os.path.exists(OTP_QUEUE_FILE):
                time.sleep(5)
                continue
            
            # Get last check position
            try:
                with open(LAST_OTP_CHECK_FILE, "r") as f:
                    last_pos = int(f.read().strip() or "0")
            except:
                last_pos = 0
            
            assignments = load_json(USER_ASSIGNMENTS_FILE)
            
            # Read new OTP entries
            with open(OTP_QUEUE_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            if len(lines) > last_pos:
                new_lines = lines[last_pos:]
                
                for line in new_lines:
                    try:
                        otp_data = json.loads(line.strip())
                        number = otp_data.get("number")
                        otp = otp_data.get("otp")
                        service = otp_data.get("service", "Unknown")
                        
                        # Find user with this number
                        for user_id, assignment in assignments.items():
                            if assignment["number"] == number:
                                countries = load_json(COUNTRIES_FILE)
                                country = assignment["country"]
                                flag = countries.get(country, {}).get("flag", "🌍")
                                
                                msg = f"🌍 <b>Country:</b> {flag} {country}\n"
                                msg += f"🔢 <b>Number:</b> {number}\n"
                                msg += f"🔑 <b>OTP:</b> <code>{otp}</code>\n"
                                msg += f"⚙️ <b>Service:</b> {service}\n"
                                msg += f"💰 <b>Reward:</b> 0.0050\n"
                                msg += f"💵 <b>Balance:</b> 0.0100"
                                
                                send_message(user_id, msg)
                                print(f"✅ OTP sent to user {user_id}: {otp}")
                    except Exception as e:
                        print(f"⚠️ Error processing OTP: {e}")
                
                # Update last position
                with open(LAST_OTP_CHECK_FILE, "w") as f:
                    f.write(str(len(lines)))
        
        except Exception as e:
            print(f"⚠️ OTP Monitor error: {e}")
        
        time.sleep(2)

# Main Bot Loop
def handle_update(update):
    try:
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            user_id = message["from"]["id"]
            text = message.get("text", "")
            
            # Handle file uploads from admin
            if "document" in message and user_id == ADMIN_USER_ID:
                if user_id in admin_states and admin_states[user_id].get("action") == "upload_numbers":
                    document = message["document"]
                    file_id = document["file_id"]
                    filename = document.get("file_name", "file.txt")
                    country = admin_states[user_id]["country"]
                    
                    send_message(chat_id, "⏳ Processing file...")
                    
                    # Download and parse file
                    file_content = download_file(file_id)
                    if file_content:
                        print(f"📄 Processing file: {filename} ({len(file_content)} bytes)")
                        numbers = parse_numbers_from_file(file_content, filename)
                        print(f"📊 Parsed {len(numbers)} valid numbers from file")
                        
                        if numbers:
                            # Add numbers to country
                            countries = load_json(COUNTRIES_FILE)
                            if country in countries:
                                added = 0
                                duplicates = 0
                                
                                for number in numbers:
                                    if number not in countries[country]["numbers"]:
                                        countries[country]["numbers"].append(number)
                                        added += 1
                                    else:
                                        duplicates += 1
                                
                                save_json(COUNTRIES_FILE, countries)
                                
                                msg = f"✅ <b>Upload Complete!</b>\n\n"
                                msg += f"🌍 Country: {countries[country]['flag']} {country}\n"
                                msg += f"➕ Added: {added} numbers\n"
                                if duplicates > 0:
                                    msg += f"⚠️ Duplicates skipped: {duplicates}\n"
                                msg += f"📱 Total numbers: {len(countries[country]['numbers'])}"
                                
                                send_message(chat_id, msg)
                                
                                # Clear admin state
                                del admin_states[user_id]
                            else:
                                send_message(chat_id, f"❌ Country '{country}' not found!")
                        else:
                            send_message(chat_id, "❌ No valid phone numbers found in file!")
                    else:
                        send_message(chat_id, "❌ Failed to download file!")
                    
                    return
            
            # Admin commands
            if user_id == ADMIN_USER_ID:
                if text.startswith("/addcountry"):
                    handle_admin_add_country(chat_id, text)
                    return
                elif text.startswith("/addnumber"):
                    handle_admin_add_number(chat_id, text)
                    return
                elif text == "/list" or text == "📋 View List":
                    handle_admin_list(chat_id)
                    return
                elif text == "➕ Add Country":
                    send_message(chat_id, "📝 To add a country, use:\n\n<code>/addcountry CountryName Flag</code>\n\nExample:\n<code>/addcountry Venezuela 🇻🇪</code>")
                    return
                elif text == "📤 Upload Numbers":
                    handle_upload_numbers(chat_id, user_id)
                    return
                elif text == "📊 Statistics":
                    handle_admin_statistics(chat_id)
                    return
                elif text == "👥 Active Users":
                    handle_admin_active_users(chat_id)
                    return
                elif text == "🗑️ Delete Country":
                    handle_admin_delete_country(chat_id, user_id)
                    return
                elif text == "🧹 Clear Numbers":
                    handle_admin_clear_numbers(chat_id, user_id)
                    return
                elif text == "📢 Broadcast":
                    handle_admin_broadcast(chat_id, user_id)
                    return
                
                # Handle broadcast message
                if user_id in admin_states and admin_states[user_id].get("action") == "broadcast":
                    if text:
                        assignments = load_json(USER_ASSIGNMENTS_FILE)
                        sent_count = 0
                        
                        for uid in assignments.keys():
                            try:
                                send_message(uid, text)
                                sent_count += 1
                            except:
                                pass
                        
                        send_message(chat_id, f"✅ Broadcast sent to {sent_count} users!")
                        del admin_states[user_id]
                    return
            
            # User commands
            if text == "/start":
                handle_start(chat_id, user_id)
            elif text == "/status":
                handle_status(chat_id, user_id)
            elif text == "/countries":
                handle_countries(chat_id)
            elif text == "/getnumber":
                handle_get_number(chat_id, user_id)
            elif text == "/help":
                handle_help(chat_id)
        
        elif "callback_query" in update:
            handle_callback(update["callback_query"])
    
    except Exception as e:
        print(f"❌ Error handling update: {e}")

def get_updates(offset=0):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": offset, "timeout": 30}
    try:
        response = requests.get(url, params=params, timeout=35)
        return response.json()
    except:
        return {"ok": False}

def set_bot_commands():
    """Set bot commands menu"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMyCommands"
    commands = [
        {"command": "getnumber", "description": "📱 Get a temporary number"},
        {"command": "status", "description": "🔑 View your number and OTP"},
        {"command": "countries", "description": "🌍 View available countries"},
        {"command": "help", "description": "❓ How to use the bot"}
    ]
    try:
        response = requests.post(url, json={"commands": commands}, timeout=10)
        if response.json().get("ok"):
            print("✅ Bot commands menu set successfully")
    except:
        print("⚠️ Failed to set bot commands menu")
    
    # Set menu button (three lines ≡)
    menu_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setChatMenuButton"
    menu_button = {
        "menu_button": {
            "type": "commands"
        }
    }
    try:
        response = requests.post(menu_url, json=menu_button, timeout=10)
        if response.json().get("ok"):
            print("✅ Menu button (≡) set successfully")
    except:
        print("⚠️ Failed to set menu button")

def main():
    print("🤖 Number Bot started!")
    init_files()
    
    # Set bot commands menu
    set_bot_commands()
    
    # Start OTP monitor in background
    otp_thread = Thread(target=monitor_otp_queue, daemon=True)
    otp_thread.start()
    
    offset = 0
    while True:
        updates = get_updates(offset)
        if updates.get("ok"):
            for update in updates.get("result", []):
                handle_update(update)
                offset = update["update_id"] + 1
        time.sleep(1)

if __name__ == "__main__":
    main()
