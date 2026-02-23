#!/usr/bin/env python3
"""
Runs SMS Forwarder Bot, Number Bot, and Health Server
"""
import os
import sys
from threading import Thread
import time

def run_sms_bot():
    """Run SMS Forwarder Bot"""
    print("🚀 Starting SMS Forwarder Bot...")
    os.system("python main.py")

def run_number_bot():
    """Run Number Bot"""
    print("🚀 Starting Number Bot...")
    os.system("python number_bot.py")

def run_health_server():
    """Run Flask Health Server"""
    print("🚀 Starting Health Server on port 5000...")
    os.system("python health_server.py")

if __name__ == '__main__':
    # Start all services in separate threads
    threads = [
        Thread(target=run_health_server, daemon=True),
        Thread(target=run_sms_bot, daemon=True),
        Thread(target=run_number_bot, daemon=True),
    ]
    
    for thread in threads:
        thread.start()
        time.sleep(2)  # Small delay between starts
    
    print("\n" + "="*50)
    print("✅ All services started successfully!")
    print("="*50)
    print("📊 Health Server: http://0.0.0.0:5000")
    print("🤖 SMS Forwarder Bot: Running")
    print("📱 Number Bot: Running")
    print("="*50 + "\n")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down all services...")
        sys.exit(0)
