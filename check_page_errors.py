from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page()
    
    console_logs = []
    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
    page.on("pageerror", lambda err: console_logs.append(f"[PAGE ERROR] {err}"))
    
    responses = []
    page.on("response", lambda resp: responses.append(f"{resp.status} {resp.request.method} {resp.url}"))
    
    print("Navigating to http://localhost:8000...")
    page.goto("http://localhost:8000")
    time.sleep(2)
    
    print("ALL RESPONSES ON PAGE LOAD:")
    for r in responses:
        if "200" not in r:
            print(r)
            
    print("\nALL CONSOLE LOGS ON PAGE LOAD:")
    for l in console_logs:
        print(l)
        
    browser.close()
