import time
#import argparse
import subprocess
import logging
import select
from PIL import Image
from io import BytesIO

# import Queue
# import threading


# class AsynchronousFileReader(threading.Thread):
#     '''
#     Helper class to implement asynchronous reading of a file
#     in a separate thread. Pushes read lines on a queue to
#     be consumed in another thread.
#     '''

#     def __init__(self, fd, queue):
#         assert isinstance(queue, Queue.Queue)
#         assert callable(fd.readline)
#         threading.Thread.__init__(self)
#         self._fd = fd
#         self._queue = queue

#     def run(self):
#         '''The body of the tread: read lines and put them on the queue.'''
#         for line in iter(self._fd.readline, ''):
#             self._queue.put(line)

#     def eof(self):
#         '''Check whether there is no more content to expect.'''
#         return not self.is_alive() and self._queue.empty()


logger = logging.getLogger('PokemonGo')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class CalcyIVError(Exception):
    pass


class RedBarError(Exception):
    pass


class PhoneNotConnectedError(Exception):
    pass


class PokemonGo(object):
    def __init__(self, device_id):
        devices = self.get_devices()
        if devices == [] or (device_id is not None and device_id not in devices):
            raise PhoneNotConnectedError
        if device_id is None:
            self.device_id = devices[0]
        else:
            self.device_id = device_id
        self.use_fallback_screenshots = False
        self.resolution = None

    def run(self, args):
        logger.debug("Running %s", args)
        p = subprocess.Popen([str(arg) for arg in args], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        logger.debug("Return code %d", p.returncode)
        return (p.returncode, stdout, stderr)

    def screencap(self):
        if not self.use_fallback_screenshots:
            return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "exec-out", "screencap", "-p"])
            try:
                return Image.open(BytesIO(stdout))
            except (OSError, IOError):
                logger.debug("Screenshot failed, using fallback method")
                self.use_fallback_screenshots = True
        return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "shell", "screencap", "-p", "/sdcard/screen.png"])
        return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "pull", "/sdcard/screen.png", "."])
        image = Image.open("screen.png")
        return image

    def determine_resolution(self):
        image = self.screencap()
        # Try and detect software nav bar
        rgb_image = image.convert('RGB')
        i = 1
        bar_color = rgb_image.getpixel((0, image.size[1] - i))
        color = bar_color
        while color == bar_color and i < image.size[0]:
            i = i + 1
            color = rgb_image.getpixel((0, image.size[1] - i))
        # If we have the same color covering 5-10% of the total height, it's probably a nav bar
        if i > image.size[1] / 25 and i < image.size[1] / 10:
            logger.info("Detected Navbar")
            size = (image.size[0], image.size[1] - i)
        else:
            logger.info("No Navbar detected")
            size = image.size
        logger.info("Determined device resolution as %s", size)
        return size

    def get_resolution(self):
        if self.resolution is None:
            self.resolution = self.determine_resolution()
        return self.resolution

    def get_x(self, percent):
        width, height = self.get_resolution()
        return int((width / 100.0) * percent)

    def get_y(self, percent):
        width, height = self.get_resolution()
        return int((height / 100.0) * percent)

    def tap(self, x, y, sleep):
        self.run(["adb", "-s", self.device_id, "shell", "input", "tap", self.get_x(x), self.get_y(y)])
        time.sleep(sleep)

    def key(self, key, sleep):
        self.run(["adb", "-s", self.device_id, "shell", "input", "keyevent", key])
        time.sleep(sleep)

    def swipe(self, x1, y1, x2, y2, sleep, duration=None):
        width, height = self.get_resolution()
        args = [
            "adb",
            "-s",
            self.device_id,
            "shell",
            "input",
            "swipe",
            self.get_x(x1),
            self.get_y(y1),
            self.get_x(x2),
            self.get_y(y2)
        ]
        if duration:
            args.append(duration)
        self.run(args)
        time.sleep(sleep)

    def check_pixel(self, rgb_image, x, y, rgb):
        img_rgb = rgb_image.getpixel((self.get_x(x), self.get_y(y)))
        logger.debug("Checking pixel. %dx%d image is %s, want %s. Returning %s", self.get_x(x), self.get_y(y), img_rgb, rgb, img_rgb == rgb)
        return img_rgb == rgb

    def check_calcy_iv_img(self, rgb_image):
        x1 = self.get_x(22.22)
        y1 = self.get_y(82.29)
        x2 = self.get_x(77.78)
        y2 = self.get_y(87.50)
        search_colors = [
            (0xA9, 0xA9, 0xA9),
            (0xB4, 0xB4, 0xB4),
            (0x64, 0x64, 0x64),
            (0x66, 0x66, 0x66)
        ]
        for x in range(x1, x2):
            for y in range(y1, y2):
                img_rgb = rgb_image.getpixel((x, y))
                if img_rgb in search_colors:
                    search_colors.remove(img_rgb)
                    if search_colors == []:
                        return True
        return False

    def check_calcy_iv(self):
        image = self.screencap()
        rgb_image = image.convert('RGB')
        if self.check_calcy_iv_img(rgb_image) is False:  # Calcy IV Failed?
            if self.check_pixel(rgb_image, 4.62, 6.77, (0xF0, 0x4B, 0x5F)) is True:
                raise RedBarError
            else:
                raise CalcyIVError

    def get_devices(self):
        code, stdout, stderr = self.run(["adb", "devices"])
        devices = []
        for line in stdout.decode('utf-8').splitlines()[1:-1]:
            device_id, name = line.split('\t')
            devices.append(device_id)
        return devices

    def send_intent(self, intent, package, sleep):
        return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "shell", "am broadcast -a {} -n {}".format(intent, package)])
        time.sleep(sleep)

    def read_logcat(self):
        # stdout_reader = AsynchronousFileReader(self.logcat_task.stdout, stdout_queue)


        lines = []
        i = 0
        self.logcat_task.stdout.flush()
        while select.select([self.logcat_task.stdout], [], [], 3)[0] != []:
            i = i + 1
            line = self.logcat_task.stdout.readline()
            if line != '':
                lines.append(line)
            if i >= 1000:
                break
        return lines

    def start_logcat(self):
        return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "shell", "pidof", "-s", "tesmath.calcy"])
        pid = stdout.decode('utf-8').strip()
        self.logcat_task = subprocess.Popen(["adb", "-s", self.device_id, "logcat", "--pid={}".format(pid)], stdout=subprocess.PIPE)

        # stdout_queue = Queue.Queue()
        # stdout_reader.start()
