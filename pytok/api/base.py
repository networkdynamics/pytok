import random

import requests

from playwright.async_api import expect

from .. import exceptions

TOK_DELAY = 30
CAPTCHA_DELAY = 999999

class Base:

    def check_initial_call(self, url):
        self.wait_for_requests(url)
        request = self.get_requests(url)[0]
        if request.response.status_code >= 300:
            raise exceptions.NotAvailableException("Content is not available")

    async def wait_for_content_or_captcha(self, content_tag):
        page = self.parent._page

        content_element = page.locator(f'[data-e2e={content_tag}]')
        captcha_element = page.locator('captcha_verify_container')
        try:
            await expect(content_element.or_(captcha_element)).to_be_visible()
            
        except TimeoutError as e:
            raise exceptions.TimeoutException(str(e))

        if captcha_element.is_visible():
            if self.parent._headless:
                raise exceptions.CaptchaException('Captcha was thrown, re-run with headless=False and solve the captcha.')
            else:
                try:
                    await expect(captcha_element).not_to_be_visible()
                    await expect(content_element).to_be_visible()
                except TimeoutError as e:
                    raise exceptions.TimeoutException(str(e))

        return content_element

    async def wait_for_content_or_unavailable_or_captcha(self, content_tag, unavailable_text):
        page = self.parent._page
        content_element = page.locator(f'[data-e2e={content_tag}]')
        captcha_element = page.locator('captcha_verify_container')
        unavailable_element = page.locator(f"//*[contains(text(), '{unavailable_text}')]")
        try:
            await expect(content_element.or_(captcha_element).or_(unavailable_element)).to_be_visible()
        except TimeoutError as e:
            raise exceptions.TimeoutException(str(e))
            
        if unavailable_element.is_visible():
            raise exceptions.NotAvailableException(f"Content is not available with message: '{unavailable_text}'")

        if captcha_element.is_visible():
            try:
                await expect(captcha_element).not_to_be_visible()
                await expect(content_element).to_be_visible()
            except TimeoutError as e:
                raise exceptions.TimeoutException(str(e))

        return content_element

    def wait_for_requests(self, api_path, timeout=TOK_DELAY):
        page = self.parent._page
        try:
            page.expect_request(api_path, timeout=timeout * 1000)
        except TimeoutError as e:
            raise exceptions.TimeoutException(str(e))

    def get_requests(self, api_path):
        return [request for request in self.parent._requests if api_path in request.url and request.response is not None]

    def get_response_body(self, request, decode=True):
        body_bytes = request.response.text()
        if decode:
            return body_bytes.decode('utf-8')
        else:
            return body_bytes

    async def scroll_to_bottom(self, speed=4):
        page = self.parent._page
        current_scroll_position = await page.evaluate("() => return document.documentElement.scrollTop || document.body.scrollTop;")
        new_height = current_scroll_position + 1
        while current_scroll_position <= new_height:
            current_scroll_position += speed + random.randint(-speed, speed)
            await page.evaluate(f"() => window.scrollTo(0, {current_scroll_position});")
            new_height = await page.evaluate("() => return document.body.scrollHeight;")

    async def scroll_to(self, position, speed=5):
        page = self.parent._page
        current_scroll_position = await page.evaluate("() => return document.documentElement.scrollTop || document.body.scrollTop;")
        new_height = current_scroll_position + 1
        while current_scroll_position <= new_height:
            current_scroll_position += speed + random.randint(-speed, speed)
            await page.evaluate(f"() => window.scrollTo(0, {current_scroll_position});")
            new_height = await page.evaluate("() => return document.body.scrollHeight;")
            if current_scroll_position > position:
                break

    async def slight_scroll_up(self, speed=4):
        page = self.parent._page
        desired_scroll = -500
        current_scroll = 0
        while current_scroll > desired_scroll:
            current_scroll -= speed + random.randint(-speed, speed)
            await page.evaluate(f"() => window.scrollBy(0, {-speed});")

    async def wait_until_not_skeleton_or_captcha(self, skeleton_tag):
        page = self.parent._page
        content = page.locator(f'[data-e2e={skeleton_tag}]')
        try:
            await expect(content).not_to_be_visible()
        except TimeoutError as e:
            if page.locator('captcha_verify_container').is_visible():
                if self.parent._headless:
                    raise exceptions.CaptchaException('Captcha was thrown, re-run with headless=False and solve the captcha.')
                else:
                    await expect(page.locator('captcha_verify_container')).not_to_be_visible()
            else:
                raise exceptions.TimeoutException(str(e))

    async def check_and_wait_for_captcha(self):
        page = self.parent._page
        if page.locator('captcha_verify_container').is_visible():
            if self.parent._headless:
                raise exceptions.CaptchaException('Captcha was thrown, re-run with headless=False and solve the captcha.')
            else:
                try:
                    await expect(page.locator('captcha_verify_container')).not_to_be_visible()
                except TimeoutError as e:
                    raise exceptions.TimeoutException(str(e))
