import requests
import seleniumwire
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

from ..exceptions import *

TOK_DELAY = 30
CAPTCHA_DELAY = 999999

class Base:

    def wait_for_content_or_captcha(self, content_tag):
        driver = self.parent._browser
        element = WebDriverWait(driver, TOK_DELAY).until(EC.any_of(EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-e2e={content_tag}]')), EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container'))))

        if driver.find_elements(By.CLASS_NAME, 'captcha_verify_container'):
            WebDriverWait(driver, CAPTCHA_DELAY).until_not(EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container')))
            element = WebDriverWait(driver, TOK_DELAY).until(EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-e2e={content_tag}]')))

        return element

    def wait_for_requests(self, api_path):
        self.parent._browser.wait_for_request(api_path, timeout=TOK_DELAY)

    def get_requests(self, api_path):
        return [request for request in self.parent._browser.requests if api_path in request.url and request.response is not None]

    def get_response_body(self, request):
        body_bytes = seleniumwire.utils.decode(request.response.body, request.response.headers.get('Content-Encoding', 'identity'))
        return body_bytes.decode('utf-8')

    def scroll_to_bottom(self):
        self.parent._browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def wait_until_not_skeleton_or_captcha(self, skeleton_tag):
        driver = self.parent._browser
        try:
            WebDriverWait(driver, TOK_DELAY).until_not(EC.presence_of_element_located((By.CSS_SELECTOR, f'[data-e2e={skeleton_tag}]')))
        except TimeoutException:
            if driver.find_elements(By.CLASS_NAME, 'captcha_verify_container'):
                WebDriverWait(driver, CAPTCHA_DELAY).until_not(EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container')))
            else:
                raise

    def check_and_wait_for_captcha(self):
        driver = self.parent._browser
        if driver.find_elements(By.CLASS_NAME, 'captcha_verify_container'):
            WebDriverWait(driver, CAPTCHA_DELAY).until_not(EC.presence_of_element_located((By.CLASS_NAME, 'captcha_verify_container')))