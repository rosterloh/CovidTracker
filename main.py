import argparse
import asyncio
import board
import datetime as dt
import digitalio
import json
import logging
import requests
from systemd import journal

from adafruit_rgb_display.rgb import color565
import adafruit_rgb_display.st7789 as st7789
from PIL import Image, ImageDraw, ImageFont
from stats import CovidStats

#COVID_19_API = "https://covid19api.herokuapp.com/"
# https://github.com/ExpDev07/coronavirus-tracker-api
COVID_19_API = "https://coronavirus-tracker-api.herokuapp.com/v2/"
HEADER = "COVID-19"

class CovidTracker:

    def __init__(self, refresh_rate=600, width=240, height=240):
        self.get_stats_interval_sec = refresh_rate
        self.width = width
        self.height = height
        
        self.logger = logging.getLogger(__name__)
        self.logger.propagate = False
        self.logger.addHandler(journal.JournaldLogHandler())
        self.logger.setLevel(logging.INFO)

        cs_pin = digitalio.DigitalInOut(board.CE0)
        dc_pin = digitalio.DigitalInOut(board.D25)
        reset_pin = None
        BAUDRATE = 64000000

        self.display = st7789.ST7789(
            board.SPI(),
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=BAUDRATE,
            width=width,
            height=height,
            y_offset=80,
            rotation=180
        )
        
        backlight = digitalio.DigitalInOut(board.D22)
        backlight.switch_to_output()
        backlight.value = True
        self.buttonA = digitalio.DigitalInOut(board.D23)
        self.buttonB = digitalio.DigitalInOut(board.D24)
        self.buttonA.switch_to_input()
        self.buttonB.switch_to_input()
        self._button_hold_time = 2.0

        self.image = Image.new("RGB", (width, height))
        self.draw = ImageDraw.Draw(self.image)
        self.draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0))
        self.display.image(self.image)#, rotation)
        self.dejavu = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        self.roboto = ImageFont.truetype("/usr/share/fonts/truetype/roboto/unhinted/Roboto-Black.ttf", 24)

        self.blue = "#007bff"
        self.indigo = "#6610f2"
        self.purple = "#6f42c1"
        self.pink = "#e83e8c"
        self.red = "#dc3545"
        self.orange = "#fd7e14"
        self.yellow = "#ffc107"
        self.green = "#28a745"
        self.teal = "#20c997"
        self.cyan = "#17a2b8"
        self.gray = "#6c757d"
        self.gray_dark = "#343a40"

        self.stats = CovidStats()

        loop = asyncio.get_event_loop()
        loop.create_task(self.update_loop())
        # loop.create_task(self.button_loop())

    def update_display(self):
        if self.stats.new_data:
            self.logger.info('New data at ' + self.stats.last_updated.strftime('%d-%b-%Y (%H:%M)'))
            self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
            hoffest = (240 - self.roboto.getsize(HEADER)[0]) / 2
            cases_header = "Confirmed: {0}".format(self.stats.data["world"]["cases"])
            cases_uk = "  UK: {0} ({1})".format(self.stats.data["uk"]["cases"], self.stats.data["uk"]["recent_cases"])
            cases_sa = "  SA: {0} ({1})".format(self.stats.data["sa"]["cases"], self.stats.data["sa"]["recent_cases"])
            deaths_header = "Deaths: {0}".format(self.stats.data["world"]["deaths"])
            deaths_uk = "  UK: {0} ({1})".format(self.stats.data["uk"]["deaths"], self.stats.data["uk"]["recent_deaths"])
            deaths_sa = "  SA: {0} ({1})".format(self.stats.data["sa"]["deaths"], self.stats.data["sa"]["recent_deaths"])
            
            padding = 10
            x = 0
            y = padding
            self.draw.text((hoffest, y), HEADER, font=self.roboto, fill="#FFFFFF")
            y += self.roboto.getsize(HEADER)[1]+padding
            
            self.draw.text((x, y), cases_header, font=self.roboto, fill="#F7F7F7")
            y += self.roboto.getsize(cases_header)[1]
            self.draw.text((x, y), cases_uk, font=self.roboto, fill=self.cyan)
            y += self.roboto.getsize(cases_uk)[1]
            self.draw.text((x, y), cases_sa, font=self.roboto, fill=self.teal)
            y += self.roboto.getsize(cases_sa)[1] + padding
            
            self.draw.text((x, y), deaths_header, font=self.roboto, fill="#F7F7F7")
            y += self.roboto.getsize(deaths_header)[1]
            self.draw.text((x, y), deaths_uk, font=self.roboto, fill=self.cyan)
            y += self.roboto.getsize(deaths_uk)[1]
            self.draw.text((x, y), deaths_sa, font=self.roboto, fill=self.teal)

            self.display.image(self.image)#, rotation)

    async def get_stats_from_server(self) -> None:
        self.logger.debug("Fetching update")
        r = requests.get(COVID_19_API + 'latest')
        if r.status_code == 200:
            data = json.loads(r.content)
            self.stats.update_world(data)
        else:
            self.logger.error("Error {0} fetching world data".format(r.status_code))
        
        r = requests.get(COVID_19_API + 'locations/223')
        if r.status_code == 200:
            data = json.loads(r.content)
            self.stats.update_country(data, "uk")
        else:
            self.logger.error("Error {0} fetching UK data".format(r.status_code))

        r = requests.get(COVID_19_API + 'locations/200') #?country_code=ZA;timelines=1')
        if r.status_code == 200:
            data = json.loads(r.content)
            self.stats.update_country(data, "sa")
        else:
            self.logger.error("Error {0} fetching SA data".format(r.status_code))

        self.update_display()

    async def update_loop(self) -> None:
        while True:
            await self.get_stats_from_server()
            await asyncio.sleep(self.get_stats_interval_sec)

    async def button_loop(self) -> None:
        last_a = True
        last_b = True

        while True:
            if last_a and not self.buttonA.value:
                self._t_a_pressed = time.time()
                self._hold_a_fired = False
                self._t_a_repeat = time.time()
                Thread(target=self._button_press_handler).start()
            
            if not last_a and self.buttonA.value:
                Thread(target=self._button_release_handler, args=(self._hold_a_fired,)).start()

            if not self.buttonA.value:
                if not self._hold_a_fired and (time.time() - self._t_a_pressed) > self._button_hold_time:
                    Thread(target=self._button_hold_handler).start()
                    self._hold_a_fired = True

            last_a = self.buttonA.value

            await asyncio.sleep(0.05)
 
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--update', type=float, default=600, help='Rate at which to update the data')
    args = parser.parse_args()
    
    try:
        ct = CovidTracker(refresh_rate=args.update)
        loop = asyncio.get_event_loop()
        loop.run_forever()
    except KeyboardInterrupt:
        pass
