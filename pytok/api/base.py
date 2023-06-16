import requests
import seleniumwire
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from .. import exceptions

TOK_DELAY = 30
CAPTCHA_DELAY = 999999

class Base:

    def check_initial_call(self, url):
        self.wait_for_requests(url)
        request = self.get_requests(url)[0]
        if request.response.status_code >= 300:
            raise exceptions.NotAvailableException("Content is not available")

    def wait_for_content_or_captcha(self, content_tag):
        driver = self.parent._browser
        try:
            element = WebDriverWait(driver, TOK_DELAY).until(EC.any_of(EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-e2e={content_tag}]')), EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container'))))
        except TimeoutException as e:
            raise exceptions.TimeoutException(str(e))

        if driver.find_elements(By.CLASS_NAME, 'captcha_verify_container'):
            if self.parent._headless:
                raise exceptions.CaptchaException('Captcha was thrown, re-run with headless=False and solve the captcha.')
            else:
                try:
                    WebDriverWait(driver, CAPTCHA_DELAY).until_not(EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container')))
                    element = WebDriverWait(driver, TOK_DELAY).until(EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-e2e={content_tag}]')))
                except TimeoutException as e:
                    raise exceptions.TimeoutException(str(e))

        return element

    def wait_for_content_or_unavailable_or_captcha(self, content_tag, unavailable_text):
        driver = self.parent._browser
        try:
            element = WebDriverWait(driver, TOK_DELAY).until(EC.any_of(EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-e2e={content_tag}]')), 
                                                                    EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container'))))
        except TimeoutException as e:
            if driver.find_elements(By.XPATH, f"//*[contains(text(), '{unavailable_text}')]"):
                raise exceptions.NotAvailableException(f"Content is not available with message: '{unavailable_text}'")
            else:
                raise exceptions.TimeoutException(str(e))

        if driver.find_elements(By.CLASS_NAME, 'captcha_verify_container'):
            try:
                WebDriverWait(driver, CAPTCHA_DELAY).until_not(EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container')))
                element = WebDriverWait(driver, TOK_DELAY).until(EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-e2e={content_tag}]')))
            except TimeoutException as e:
                raise exceptions.TimeoutException(str(e))

        return element

    def wait_for_requests(self, api_path, timeout=TOK_DELAY):
        try:
            self.parent._browser.wait_for_request(api_path, timeout=timeout)
        except TimeoutException as e:
            raise exceptions.TimeoutException(str(e))

    def get_requests(self, api_path):
        return [request for request in self.parent._browser.requests if api_path in request.url and request.response is not None]

    def get_response_body(self, request):
        body_bytes = seleniumwire.utils.decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity'))
        return body_bytes.decode('utf-8')

    def scroll_to_bottom(self, speed=8):
        current_scroll_position = self.parent._browser.execute_script("return document.documentElement.scrollTop || document.body.scrollTop;")
        new_height = current_scroll_position + 1
        while current_scroll_position <= new_height:
            current_scroll_position += speed
            self.parent._browser.execute_script(f"window.scrollTo(0, {current_scroll_position});")
            new_height = self.parent._browser.execute_script("return document.body.scrollHeight;")

    def slight_scroll_up(self, speed=8):
        desired_scroll = -250
        current_scroll = 0
        while current_scroll > desired_scroll:
            current_scroll -= speed
            self.parent._browser.execute_script(f"window.scrollBy(0, {-speed});")

    def wait_until_not_skeleton_or_captcha(self, skeleton_tag):
        driver = self.parent._browser
        try:
            WebDriverWait(driver, TOK_DELAY).until_not(EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-e2e={skeleton_tag}]')))
        except TimeoutException as e:
            if driver.find_elements(By.CLASS_NAME, 'captcha_verify_container'):
                WebDriverWait(driver, CAPTCHA_DELAY).until_not(EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container')))
            else:
                raise exceptions.TimeoutException(str(e))

    def check_and_wait_for_captcha(self):
        driver = self.parent._browser
        if driver.find_elements(By.CLASS_NAME, 'captcha_verify_container'):
            try:
                WebDriverWait(driver, CAPTCHA_DELAY).until_not(EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container')))
            except TimeoutException as e:
                raise exceptions.TimeoutException(str(e))
        else:
            raise exceptions.TikTokException("Captcha requested but not found in browser")
