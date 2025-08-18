#!/usr/bin/env python3
"""
🎭 Playwright Setup Script for UmrahCheck
Installs Playwright browsers for web scraping
"""
import subprocess
import sys
import os

def setup_playwright():
    """Install Playwright and required browsers"""
    print("🎭 Setting up Playwright for UmrahCheck...")
    
    try:
        # Install playwright package if not already installed
        print("📦 Installing playwright package...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        
        # Install browsers (Chromium is sufficient for our needs)
        print("🌐 Installing Chromium browser...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        
        # Install system dependencies for Linux (Railway uses Linux)
        if sys.platform.startswith('linux'):
            print("🐧 Installing system dependencies for Linux...")
            subprocess.check_call([sys.executable, "-m", "playwright", "install-deps", "chromium"])
        
        print("✅ Playwright setup complete!")
        
        # Test the installation
        print("\n🧪 Testing Playwright installation...")
        test_code = """
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://example.com')
        title = await page.title()
        print(f"✅ Test successful! Page title: {title}")
        await browser.close()

asyncio.run(test())
"""
        
        subprocess.check_call([sys.executable, "-c", test_code])
        
        print("\n🎉 Playwright is ready for web scraping!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error setting up Playwright: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_playwright()