from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1400, "height": 900})
    
    logs = []
    page.on("console", lambda m: logs.append(f"CONSOLE [{m.type}]: {m.text}"))
    page.on("pageerror", lambda err: logs.append(f"PAGE ERROR: {err}"))
    page.on("dialog", lambda d: (logs.append(f"ALERT: {d.message}"), d.dismiss()))
    
    print("Navigating...")
    page.goto("http://localhost:8000")
    time.sleep(2)
    page.screenshot(path="debug_0_initial.png")
    
    test_url = "https://suno.com/song/6090ddec-8493-428a-beae-bd185fe3ef73"
    print("Clicking input and pressing paste...")
    page.locator("#suno-url-input").click()
    page.keyboard.press("Control+v") # Or fill
    page.locator("#suno-url-input").fill(test_url)
    page.locator("#suno-url-input").dispatch_event("input")
    
    time.sleep(2)
    page.screenshot(path="debug_1_after_input.png")
    
    time.sleep(5)
    page.screenshot(path="debug_2_after_5s.png")
    
    time.sleep(8)
    page.screenshot(path="debug_3_after_13s.png")
    
    print("Logs:")
    for l in logs:
        print(l)
        
    browser.close()
