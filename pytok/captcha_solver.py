import asyncio
import random
from urllib.parse import urlparse

import cv2
import base64
import numpy as np
import requests


class CaptchaSolver:
    def __init__(self, response, puzzle, piece):
        self._request = response.request
        self._response = response
        self._client = requests.Session()
        self._puzzle = base64.b64encode(puzzle)
        self._piece = base64.b64encode(piece)

    def _host(self):
        return urlparse(self._request.url).netloc

    def _params(self):
        return urlparse(self._request.url).query

    def _headers(self) -> dict:
        return self._request.headers

    async def _get_challenge(self) -> dict:
        return await self._response.json()

    async def _solve_captcha(self) -> dict:
        if self._mode == "slide":
            solver = PuzzleSolver(self._puzzle, self._piece)
            maxloc = solver.get_position()
        elif self._mode == "whirl":
            maxloc = whirl_solver(self._puzzle, self._piece)
        randlength = round(
            random.random() * (100 - 50) + 50
        )
        await asyncio.sleep(1)  # don't remove delay or it will fail
        return {
            "maxloc": maxloc,
            "randlenght": randlength
        }

    def _post_captcha(self, solve: dict) -> dict:
        params = self._params()

        body = {
            "id": solve["id"],
            "mode": self._mode
        }
        if self._mode == "slide":
            body.update({
                "modified_img_width": 552,
                "reply": list(
                    {
                        "relative_time": i * solve["randlenght"],
                        "x": round(
                            solve["maxloc"] / (solve["randlenght"] / (i + 1))
                        ),
                        "y": solve["tip"],
                    }
                    for i in range(
                        solve["randlenght"]
                    )
                ),
            })
        elif self._mode == "whirl":
            body.update({
                "modified_img_width": 340,
                "drag_width": 271,
                "reply": list(
                    {
                        "relative_time": i * solve["randlenght"],
                        "x": round(
                            271 * solve["maxloc"] / (solve["randlenght"] / (i + 1))
                        ),
                        "y": solve["tip"],
                    }
                    for i in range(
                        solve["randlenght"]
                    )
                ),
            })

        host = self._host()
        headers = self._headers()

        resp = self._client.post(
            url=(
                    "https://"
                    + host
                    + "/captcha/verify?"
                    + params
            ),
            headers=headers.update(
                {
                    "content-type": "application/json"
                }
            ),
            json=body
        )

        if resp.status_code != 200:
            raise Exception("Captcha was not solved")
        else:
            # status code was 200, but perhaps the response was to say that the CAPTCHA failed.
            if resp.json()['code'] >= 500:
                raise Exception(f"CAPTCHA server responded 200 but said: {resp.json()['message']}")

        return resp.json()

    async def solve_captcha(self):
        # this method is called
        captcha_challenge = await self._get_challenge()

        if 'mode' in captcha_challenge["data"]:
            captcha_challenge = captcha_challenge["data"]
        elif 'challenges' in captcha_challenge["data"]:
            captcha_challenge = captcha_challenge["data"]["challenges"][0]
        captcha_id = captcha_challenge["id"]
        self._mode = captcha_challenge["mode"]

        solve = await self._solve_captcha()

        solve['id'] = captcha_id
        if captcha_challenge["mode"] == "slide":
            tip_y = captcha_challenge["question"]["tip_y"]
            solve['tip'] = tip_y
        elif captcha_challenge["mode"] == "whirl":
            solve['tip'] = 0
        return solve


class PuzzleSolver:
    def __init__(self, base64puzzle, base64piece):
        self.puzzle = base64puzzle
        self.piece = base64piece

    def get_position(self):
        puzzle = self._background_preprocessing()
        piece = self._piece_preprocessing()
        matched = cv2.matchTemplate(
            puzzle,
            piece,
            cv2.TM_CCOEFF_NORMED
        )
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(matched)
        return max_loc[0]

    def _background_preprocessing(self):
        img = self._img_to_grayscale(self.piece)
        background = self._sobel_operator(img)
        return background

    def _piece_preprocessing(self):
        img = self._img_to_grayscale(self.puzzle)
        template = self._sobel_operator(img)
        return template

    def _sobel_operator(self, img):
        scale = 1
        delta = 0
        ddepth = cv2.CV_16S

        img = cv2.GaussianBlur(img, (3, 3), 0)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        grad_x = cv2.Sobel(
            gray,
            ddepth,
            1,
            0,
            ksize=3,
            scale=scale,
            delta=delta,
            borderType=cv2.BORDER_DEFAULT,
        )
        grad_y = cv2.Sobel(
            gray,
            ddepth,
            0,
            1,
            ksize=3,
            scale=scale,
            delta=delta,
            borderType=cv2.BORDER_DEFAULT,
        )
        abs_grad_x = cv2.convertScaleAbs(grad_x)
        abs_grad_y = cv2.convertScaleAbs(grad_y)
        grad = cv2.addWeighted(abs_grad_x, 0.5, abs_grad_y, 0.5, 0)

        return grad

    def _img_to_grayscale(self, img):
        return cv2.imdecode(
            self._string_to_image(img),
            cv2.IMREAD_COLOR
        )

    def _string_to_image(self, base64_string):
        return np.frombuffer(
            base64.b64decode(base64_string),
            dtype="uint8"
        )


def _get_images_and_edges(b64_puzzle, b64_piece, resolution=300):
    puzzle = cv2.imdecode(np.frombuffer(base64.b64decode(b64_puzzle), dtype="uint8"), cv2.IMREAD_COLOR)
    piece = cv2.imdecode(np.frombuffer(base64.b64decode(b64_piece), dtype="uint8"), cv2.IMREAD_COLOR)

    # get inner edge of puzzle
    r = (piece.shape[0] / 2) + 1
    puzzle_edge = np.zeros((resolution, 3))
    for idx, theta in enumerate(np.linspace(0, 2 * np.pi, resolution)):
        x = int(puzzle.shape[0] / 2 + r * np.cos(theta))
        y = int(puzzle.shape[1] / 2 + r * np.sin(theta))
        puzzle_edge[idx] = puzzle[x, y]

    # get outer edge of piece
    r = (piece.shape[0] / 2) - 1
    piece_edge = np.zeros((resolution, 3))
    for idx, theta in enumerate(np.linspace(0, 2 * np.pi, resolution)):
        x = min(int(piece.shape[0] / 2 + r * np.cos(theta)), piece.shape[0] - 1)
        y = min(int(piece.shape[1] / 2 + r * np.sin(theta)), piece.shape[1] - 1)
        piece_edge[idx] = piece[x, y]

    return puzzle, piece, puzzle_edge, piece_edge


def whirl_solver(b64_puzzle, b64_piece):
    resolution = 300
    _, _, puzzle_edge, piece_edge = _get_images_and_edges(b64_puzzle, b64_piece, resolution=resolution)

    # find the best match
    best_match = 0
    best_angle = 0
    for angle in range(resolution):
        match = np.sum(puzzle_edge * np.roll(piece_edge, angle, axis=0))
        if match > best_match:
            best_match = match
            best_angle = angle

    return (resolution - best_angle) / resolution