import asyncio
from datetime import datetime
import random

from pyclick import HumanCurve

from playwright.async_api import expect

from .. import exceptions, captcha_solver

TOK_DELAY = 30
CAPTCHA_DELAY = 999999


def get_login_close_element(page):
    return page.get_by_text("Continue as guest", exact=True) \
        .or_(page.get_by_text("Continue without login", exact=True))


def get_captcha_element(page):
    return page.locator('Rotate the shapes') \
        .or_(page.get_by_text('Verify to continue:', exact=True)) \
        .or_(page.get_by_text('Click on the shapes with the same size', exact=True)) \
        .or_(page.get_by_text('Drag the slider to fit the puzzle', exact=True).first)


class Base:

    async def check_initial_call(self, url):
        async with self.wait_for_requests(url) as event:
            response = await event.value.response()
            if response.status >= 300:
                raise exceptions.NotAvailableException("Content is not available")

    async def wait_for_content_or_captcha(self, content_tag):
        page = self.parent._page

        content_element = page.locator(content_tag).first
        # content_element = page.get_by_text('Videos', exact=True)
        captcha_element = get_captcha_element(page)

        try:
            await expect(content_element.or_(captcha_element)).to_be_visible(timeout=TOK_DELAY * 1000)

        except TimeoutError as e:
            raise exceptions.TimeoutException(str(e))

        captcha_visible = await captcha_element.is_visible()
        if captcha_visible:
            await self.solve_captcha()
            asyncio.sleep(1)
            await expect(content_element).to_be_visible(timeout=TOK_DELAY * 1000)

        return content_element

    async def wait_for_content_or_unavailable_or_captcha(self, content_tag, unavailable_text, no_content_text=None):
        page = self.parent._page
        content_element = page.locator(content_tag).first
        captcha_element = get_captcha_element(page)
        unavailable_element = page.get_by_text(unavailable_text, exact=True)
        if no_content_text:
            no_content_element = page.get_by_text(no_content_text, exact=True)
        else:
            no_content_element = None
        # try:
        expected_elements = content_element.or_(captcha_element).or_(unavailable_element)
        if no_content_text:
            expected_elements = expected_elements.or_(no_content_element)
        # try:
        await expect(content_element.or_(captcha_element).or_(unavailable_element)).to_be_visible(
            timeout=TOK_DELAY * 1000)
        #     except Exception as e:
        #         print(
        #             e)  # TODO: playwright may throw a strict mode violation error here; handle it at top layer
        #         raise
        # except TimeoutError as e:
        #     raise exceptions.TimeoutException(str(e))

        if await captcha_element.is_visible():
            await self.solve_captcha()
            await asyncio.sleep(1)
            if await captcha_element.is_visible():
                raise exceptions.CaptchaException("Captcha is still visible after solving")
            expected_elements = content_element.or_(unavailable_element)
            if no_content_text:
                expected_elements = expected_elements.or_(no_content_element)
            await expect(expected_elements).to_be_visible(
                timeout=TOK_DELAY * 1000)  # waits TOK_DELAY seconds and launches new browser instance

        if await unavailable_element.is_visible():
            raise exceptions.NotAvailableException(f"Content is not available with message: '{unavailable_text}'")

        return content_element

    async def check_for_unavailable_or_captcha(self, unavailable_text):
        page = self.parent._page
        captcha_element = get_captcha_element(page)
        unavailable_element = page.get_by_text(unavailable_text, exact=True)

        captcha_visible = await captcha_element.is_visible()
        if captcha_visible:
            num_tries = 0
            max_tries = 3
            captcha_exceptions = []
            while num_tries < max_tries:
                num_tries += 1
                try:
                    await self.solve_captcha()
                    await asyncio.sleep(1)
                    captcha_is_visible = await captcha_element.is_visible()
                    if captcha_is_visible:
                        captcha_exceptions.append(exceptions.CaptchaException("Captcha is still visible after solving"))
                        continue
                    else:
                        break
                except Exception as e:
                    captcha_exceptions.append(e)
            else:
                print(
                    f"Failed to solve captcha after {max_tries} tries with errors: {captcha_exceptions}, continuing anyway...")

        login_element = get_login_close_element(page)
        login_visible = await login_element.is_visible()
        if login_visible:
            try:
                login_close = get_login_close_element(page)
                login_close_visible = await login_close.is_visible()
                if login_close_visible:
                    await login_close.click()
            except Exception as e:
                print(f"Failed to close login with error: {e}, continuing anyway...")

        if await unavailable_element.is_visible():
            raise exceptions.NotAvailableException(f"Content is not available with message: '{unavailable_text}'")

    async def check_for_unavailable(self, unavailable_text):
        page = self.parent._page
        unavailable_element = page.get_by_text(unavailable_text, exact=True)
        if await unavailable_element.is_visible():
            raise exceptions.NotAvailableException(f"Content is not available with message: '{unavailable_text}'")

    async def wait_for_requests(self, api_path, timeout=TOK_DELAY):
        page = self.parent._page
        try:
            async with page.expect_request(api_path, timeout=timeout * 1000) as first:
                return await first.value
        except Exception as e:
            raise exceptions.TimeoutException(str(e))

    def get_requests(self, api_path):
        """searches a list of all requests thus far issued by the Playwright browser instance"""
        return [request for request in self.parent._requests if api_path in request.url]

    def get_responses(self, api_path):
        return [response for response in self.parent._responses if api_path in response.url]

    async def get_response_body(self, response):
        return await response.body()

    async def scroll_to_bottom(self, speed=4):
        page = self.parent._page
        current_scroll_position = await page.evaluate(
            "() => document.documentElement.scrollTop || document.body.scrollTop;")
        new_height = current_scroll_position + 1
        while current_scroll_position <= new_height:
            current_scroll_position += speed + random.randint(-speed, speed)
            await page.evaluate(f"() => window.scrollTo(0, {current_scroll_position});")
            new_height = await page.evaluate("() => document.body.scrollHeight;")

    async def scroll_to(self, position, speed=5):
        page = self.parent._page
        current_scroll_position = await page.evaluate(
            "() => document.documentElement.scrollTop || document.body.scrollTop;")
        new_height = current_scroll_position + 1
        while current_scroll_position <= new_height:
            current_scroll_position += speed + random.randint(-speed, speed)
            await page.evaluate(f"() => window.scrollTo(0, {current_scroll_position});")
            new_height = await page.evaluate("() => document.body.scrollHeight;")
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
            captcha_element = get_captcha_element(page)
            if await captcha_element.is_visible():
                await self.solve_captcha()
                asyncio.sleep(1)
            else:
                raise exceptions.TimeoutException(str(e))

    async def check_and_wait_for_captcha(self):
        page = self.parent._page
        captcha_element = get_captcha_element(page)
        captcha_visible = await captcha_element.is_visible()
        if captcha_visible:
            await self.solve_captcha()
            await asyncio.sleep(1)

    async def check_and_close_signin(self):
        page = self.parent._page
        signin_element = get_login_close_element(page)
        signin_visible = await signin_element.is_visible()
        if signin_visible:
            await signin_element.click()

    async def solve_captcha(self):
        if self.parent._manual_captcha_solves:
            input("Press Enter to continue after solving CAPTCHA:")
            await asyncio.sleep(1)
            if self.parent._log_captcha_solves:
                request = self.get_requests('/captcha/verify')[0]
                body = request.post_data
                with open(f"manual_captcha_{datetime.now().isoformat()}.json", "w") as f:
                    f.write(body)
            return
        """
        this method not only calculates the CAPTCHA solution but also POSTs it to TikTok's server.
        """
        # get captcha data
        request = self.get_requests('/captcha/get')[0]
        captcha_response = await request.response()
        if captcha_response is not None:
            captcha_json = await captcha_response.json()
        else:
            raise exceptions.EmptyResponseException

        if 'mode' in captcha_json['data']:
            captcha_data = captcha_json['data']
        elif 'challenges' in captcha_json['data']:
            captcha_data = captcha_json['data']['challenges'][0]
        captcha_type = captcha_data['mode']
        if captcha_type not in ['slide', 'whirl']:
            raise exceptions.CaptchaException(f"Unsupported captcha type: {captcha_type}")

        """
        captcha_data['question']['url1'] is a URL from TikTok's content delivery network. If you copy-paste it into your
        web browser, you should GET the puzzle image. puzzle_response is the full response from the server, and
        puzzle is the image itself, returned as a sequence of bytes.
        """
        puzzle_req = self.get_requests(captcha_data['question']['url1'])[0]
        puzzle_response = await puzzle_req.response()
        puzzle = await puzzle_response.body()

        if not puzzle:
            raise exceptions.CaptchaException("Puzzle was not found in response")

        """
        captcha_data['question']['url2'] is a URL from TikTok's content delivery network. If you copy-paste it into your
        web browser, you should GET the puzzle piece that has to be moved to the correct position in the puzzle. 
        piece_response: the full Playwright/HTTP response object
        piece: the image of the puzzle piece, returned as a sequence of bytes
        """
        piece_req = self.get_requests(captcha_data['question']['url2'])[0]
        piece_response = await piece_req.response()
        piece = await piece_response.body()

        if not piece:
            raise exceptions.CaptchaException("Piece was not found in response")

        """
        -at this point in the code you have the puzzle image (puzzle) and the piece image (piece)
        -now a local CAPTCHA solver will decide how to place the piece in the puzzle
        -finally, the solution will be POSTed to TikTok, and the server's response will be obtained
        """
        solve = await captcha_solver.CaptchaSolver(captcha_response, puzzle, piece).solve_captcha()

        page = self.parent._page
        drag = page.locator('css=div.secsdk-captcha-drag-icon').first
        bar = page.locator('css=div.captcha_verify_slide--slidebar').first
        
        drag_bounding_box = await drag.bounding_box()
        bar_bounding_box = await bar.bounding_box()

        drag_centre = {
            'x': drag_bounding_box['x'] + drag_bounding_box['width'] / 2,
            'y': drag_bounding_box['y'] + drag_bounding_box['height'] / 2
        }

        bar_effective_width = bar_bounding_box['width'] - drag_bounding_box['width']
        distance_to_drag = bar_effective_width * solve['maxloc']

        curve_kwargs = {
            'knotsCount': 7, 
            'distortionMean': 14.3, 
            'distortionStdev': 22.7, 
            'distortionFrequency': 0.8, 
            'targetPoints': 500
        }
        points = HumanCurve(
            [0, 0], 
            [int(drag_centre['x']), int(drag_centre['y'])],
            **curve_kwargs
        ).points
        for point in points:
            await page.mouse.move(point[0], point[1])
        await page.mouse.down()
        points = HumanCurve(
            [int(drag_centre['x']), int(drag_centre['y'])], 
            [int(drag_centre['x'] + distance_to_drag), int(drag_centre['y'])],
            **curve_kwargs
        ).points
        for point in points:
            await page.mouse.move(point[0], point[1])
        await page.mouse.up()

        if self.parent._log_captcha_solves:
            await asyncio.sleep(1)
            request = self.get_requests('/captcha/verify')[0]
            body = request.post_data
            with open(f"automated_captcha_{datetime.now().isoformat()}.json", "w") as f:
                f.write(body)

