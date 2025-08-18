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
    
    # Check if we're in Railway environment
    is_railway = os.getenv('RAILWAY_ENVIRONMENT') is not None
    
    try:
        # Install playwright package if not already installed
        print("📦 Installing playwright package...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright"])
        
        # Install browsers (Chromium is sufficient for our needs)
        print("🌐 Installing Chromium browser...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        
        # Handle system dependencies based on environment
        if sys.platform.startswith('linux'):
            if is_railway:
                print("🚂 Railway environment detected - skipping system dependencies")
                print("💡 Railway containers should have necessary libs pre-installed")
            else:
                print("🐧 Attempting to install system dependencies for Linux...")
                try:
                    subprocess.check_call([sys.executable, "-m", "playwright", "install-deps", "chromium"])
                    print("✅ System dependencies installed successfully")
                except subprocess.CalledProcessError as e:
                    print(f"⚠️  System dependencies installation failed (code {e.returncode}), but continuing...")
                    print("💡 This is normal in some containerized environments")
                    print("🔧 Playwright will try to run without additional system packages")
        
        print("✅ Playwright setup complete!")
        
        # Skip test in Railway environment to avoid deployment issues
        if not is_railway:
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
        else:
            print("\n🚂 Skipping test in Railway environment")
            print("🎉 Playwright setup complete for Railway!")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error setting up Playwright: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_playwright()