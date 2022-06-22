import time

from selenium import webdriver

def main():
    driver = webdriver.Chrome()

    driver.get("https://us.tiktok.com/")

    SCROLL_PAUSE_TIME = 3

    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        html = driver.page_source
        if 'tiktok-verify-page' in html:
            input('Please bypass captcha and enter any character to continue:')

        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    driver.close()
    driver.quit()

if __name__ == '__main__':
    main()