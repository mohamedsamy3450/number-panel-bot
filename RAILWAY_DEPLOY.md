# 🚂 Railway Deployment Guide

## 📋 الملفات المطلوبة (تم إنشاؤها ✅)

1. **requirements.txt** - المكتبات المطلوبة
2. **Procfile** - أوامر التشغيل
3. **runtime.txt** - نسخة Python
4. **railway.json** - إعدادات Railway
5. **nixpacks.toml** - تثبيت Chromium و ChromeDriver

---

## 🚀 خطوات النشر على Railway

### 1️⃣ إنشاء مشروع جديد
1. اذهب إلى [railway.app](https://railway.app)
2. اضغط **New Project**
3. اختر **Deploy from GitHub repo**
4. اختر repository المشروع

### 2️⃣ إضافة Environment Variables

اذهب إلى **Variables** وأضف المتغيرات التالية:

**للـ SMS Forwarder Bot:**
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_GROUP_CHAT_IDS=-1003206460580
LOGIN_USERNAME=your_panel_username
LOGIN_PASSWORD=your_panel_password
TELEGRAM_CHANNEL_LINK=https://t.me/yourchannel
TELEGRAM_BOT_USERNAME=@YourBot
```

**للـ Number Bot:**
```
NUMBER_BOT_TOKEN=your_number_bot_token
ADMIN_USER_ID=123456789
```

### 3️⃣ Deploy!
- Railway هيشتغل تلقائيًا ويثبت المكتبات
- هيبدأ تشغيل البوتات عبر `run_all.py`

---

## ⚙️ الإعدادات المهمة

### Port Configuration
- Railway بيوفر port تلقائي عبر `$PORT`
- Health server شغال على port 5000 (داخلي)

### Chromium & ChromeDriver
- تم إضافتهم في `nixpacks.toml`
- Railway هيثبتهم تلقائيًا

---

## 🔍 استكشاف الأخطاء

### 1. Chromium not found
**الحل:**
تأكد إن `nixpacks.toml` موجود وفيه:
```toml
[phases.setup]
nixPkgs = ["python311", "chromium", "chromedriver"]
```

### 2. Bot لا يستجيب
**الحل:**
- تحقق من الـ Environment Variables
- شوف الـ Logs في Railway Dashboard

### 3. Rate Limit من Telegram
**الحل:**
- البوت عنده retry mechanism تلقائي
- هينتظر الوقت المطلوب ويحاول تاني

---

## 📊 مراقبة البوت

**View Logs:**
- اذهب إلى Railway Dashboard
- اضغط على المشروع → Deployments → View Logs

**Check Health:**
- افتح الـ URL اللي Railway بيديهولك
- هتشوف "All services are running!" ✅

---

## 💡 نصائح

1. **استخدم Railway Environment Groups** لتنظيم المتغيرات
2. **فعّل Auto Deploy** عشان كل push يتنشر تلقائيًا
3. **راقب الـ Logs** بانتظام
4. **استخدم Railway CLI** للـ debugging المحلي

---

## 🆘 Support

لو واجهتك مشكلة:
1. شوف الـ Railway Logs
2. تحقق من Environment Variables
3. تأكد إن كل الملفات اتنسخت صح

---

**✅ كل حاجة جاهزة للنشر على Railway!**
