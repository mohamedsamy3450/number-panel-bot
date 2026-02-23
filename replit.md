# Telegram SMS System with Number Bot

## Overview
This project consists of two interconnected Telegram bots:
1. **SMS Forwarder Bot** (main.py): Monitors SMS messages from a web panel and forwards them to Telegram groups
2. **Number Bot** (number_bot.py): Provides temporary phone numbers to users and forwards OTPs automatically

## Recent Changes (November 10, 2025)
- **REMOVED: Setup Bot and Checker Bot**
  - Removed setup_bot.py and telegram_checker_bot.py
  - Simplified project to focus on core SMS forwarding and number distribution functionality
  - Updated run_all.py to only start SMS Forwarder Bot and Number Bot
- **FIXED: Login Page Structure Changed - Updated Selectors**
  - Issue: Login page HTML structure was updated by the panel, causing authentication failures
  - CAPTCHA field changed from `name="answer"` to `name="capt"`
  - LOGIN button changed to `<button type="submit">LOGIN</button>`
  - Updated selectors to match new structure while maintaining backward compatibility
  - Bot now successfully logs in on first attempt with CAPTCHA auto-solving
  - Added fallback selectors for resilience against future UI changes

## Previous Changes (November 9, 2025)
- **FIXED: SMS Forwarder Bot Not Sending Messages**
  - Issue: Bot was reading page HTML before JavaScript/AJAX loaded the data
  - Solution: Added proper wait time (3+ seconds) for DataTables to load via JavaScript
  - Added intelligent waiting loop that checks when table data is fully loaded
  - Bot now successfully sends SMS messages to Telegram groups
  - Reduced verbose logging to keep logs clean

## Previous Changes (November 8, 2025)
- **NEW: File Upload Feature for Number Bot**
  - Admin can now upload phone numbers via Excel (.xlsx, .xls), CSV, or Text files
  - Country selection via inline keyboard before file upload
  - Automatic duplicate detection and skipping
  - Support for numeric cells in Excel (fixed float conversion issue)
  - Bulk number addition (upload hundreds of numbers at once)
- Created new Number Bot with admin and user menu systems
- Implemented number rotation system (users get different numbers when changing)
- Added OTP monitoring and automatic forwarding to users
- Fixed message ordering to prioritize newest messages first
- Updated message formatting to show service from CLI column
- Added Ecuador 🇪🇨 (593) to country list

## Previous Changes (November 7, 2025)
- Fixed syntax error on line 25 (removed invalid "!" character)
- Converted from Edge WebDriver to Chrome headless for compatibility with Replit
- Migrated all sensitive credentials to environment variables
- Updated panel URLs from 94.23.120.156/ints to 51.89.99.105/NumberPanel
- Added proper login verification (checks for errors and OTP page access)
- Implemented automatic alert handling for DataTables warnings
- Added filtering for empty rows and system messages
- Installed required packages: selenium, beautifulsoup4, requests, lxml
- Installed system dependencies: chromium, chromedriver
- Configured workflow to run the bot automatically
- Fixed Windows line endings (CRLF to LF)

## Project Architecture

### Main Components

**1. SMS Forwarder Bot (main.py)**
  - Web scraping using Selenium (Chrome headless)
  - SMS parsing and OTP extraction
  - Telegram message formatting and sending
  - Country detection with flags
  - Service detection from CLI column
  - Writes OTP data to otp_queue.json

**2. Number Bot (number_bot.py)**
  - Admin panel for managing countries and numbers
  - User interface for requesting numbers
  - Number assignment with rotation system
  - OTP monitoring from otp_queue.json
  - Automatic OTP forwarding to users
  - Statistics and user management

### Environment Variables (Secrets)
**SMS Forwarder Bot:**
- `TELEGRAM_BOT_TOKEN`: Bot token from @BotFather (for group bot)
- `TELEGRAM_GROUP_CHAT_IDS`: Comma-separated group IDs
- `LOGIN_USERNAME`: Website login username
- `LOGIN_PASSWORD`: Website login password
- `TELEGRAM_CHANNEL_LINK`: Main Telegram channel link
- `TELEGRAM_BOT_USERNAME`: Bot username for inline buttons

**Number Bot:**
- `NUMBER_BOT_TOKEN`: Bot token for number distribution bot
- `ADMIN_USER_ID`: Telegram user ID for admin access

### Dependencies
**Python packages:**
- selenium: Web automation
- beautifulsoup4: HTML parsing
- requests: HTTP requests for Telegram API
- lxml: XML/HTML parser
- pandas: Excel/CSV file processing
- openpyxl: Excel file handling

**System packages:**
- chromium: Headless browser
- chromedriver: Chrome WebDriver

## Features

**SMS Forwarder Bot:**
- Automatic login with CAPTCHA solving
- SMS monitoring and extraction
- OTP code detection
- Service identification from CLI
- Country flag detection (including Ecuador)
- Duplicate message prevention
- Inline keyboard buttons (Channel + Bot links)
- OTP data queuing to otp_queue.json
- Reversed message order (newest first)

**Number Bot:**
- Admin menu with keyboard buttons
- User menu with keyboard buttons
- Country and number management (admin only)
- **Bulk number upload via file (Excel/CSV/Text)**
- Number assignment with rotation
- OTP monitoring and auto-forwarding
- User statistics and active user tracking
- Change number/country functionality
- Help system

## Data Files
- `otp_queue.json`: OTP data from SMS bot (shared between bots)
- `countries.json`: Available countries and numbers (Number Bot)
- `user_assignments.json`: User-to-number mappings (Number Bot)
- `last_otp_check.txt`: OTP queue position tracker (Number Bot)

## Bot Status
✅ Both bots are ready to run:
  - SMS Forwarder Bot: Monitors SMS panel and forwards to Telegram
  - Number Bot: Distributes numbers and forwards OTPs
