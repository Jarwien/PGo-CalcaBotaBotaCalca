import time
import subprocess
import logging
from PIL import Image
from io import BytesIO


logger = logging.getLogger('PokemonGo')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class CalcyIVError(Exception):
    pass


class RedBarError(Exception):
    pass


class PhoneNotConnectedError(Exception):
    pass


class CalcyIVNotRunning(Exception):
    pass


class PokemonGo(object):
    def __init__(self, device_id, user_id):
        devices = self.get_devices()
        if devices == [] or (device_id is not None and device_id not in devices):
            raise PhoneNotConnectedError
        if device_id is None:
            self.device_id = devices[0]
        else:
            self.device_id = device_id
        if user_id is None:
            self.user_id = None
        else:
            self.user_id = user_id
        self.use_fallback_screenshots = False
        self.resolution = None
        try:
            return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "shell", "pidof", "-s", "tesmath.calcy"])
        except Exception as e:
            raise CalcyIVNotRunning
        self.pid = stdout.decode('utf-8').strip()

    def run(self, args):
        logger.debug("Running %s", args)
        p = subprocess.Popen([str(arg) for arg in args], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        # logger.debug("Return code %d", p.returncode)
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
        if i > image.size[1] / 30 and i < image.size[1] / 10:
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
        logger.info("Tapping on " + format(self.get_x(x), '>4d') + " x " + format(self.get_y(y), '<4d') + "  (" + format(x, '>.2f') + "% x " + format(y, '<.2f') + "%) and waiting " + str(sleep) + "seconds...")
        time.sleep(sleep)

    def key(self, key, sleep):
        self.run(["adb", "-s", self.device_id, "shell", "input", "keyevent", key])
        logger.info("Pressing key " + key + " and waiting " + str(sleep) + "seconds...")
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

        # with output box:
        # return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "shell", "am broadcast -a {} -n {}".format(intent, package)])


        if self.user_id is not None:
            # for calcy inside island
            return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "shell", "am broadcast --user " + self.user_id + " -a {} --ez silentMode true -n {}".format(intent, package)])
        else:
            # without output box (default)
            return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "shell", "am broadcast -a {} --ez silentMode true -n {}".format(intent, package)])

        logger.debug("Sending intent: " + intent + " to " + package + "...")
        time.sleep(sleep)

    def get_last_logcat(self):
        ''' Grabs only the last return line of CalcyIV, and everything after it,
            instead of watching the logcat, which causes problems with buffers sync.

            The same as running:
                sh -c 'adb logcat -d | \grep $(adb shell pidof -s tesmath.calcy) | tac | grep "Received values" -B1000 -m1'

            Deprecated (android 7.0 or higher only):
                adb logcat -d --pid=$(adb shell pidof -s tesmath.calcy) | tac | grep "Received values" -B1000 -m1

            TODO: detect android version and use one of the two versions, because the general one is very slow.
        '''
        # code, stdout, stderr = self.run(["adb", "logcat", "--pid={}".format(self.pid),])
        # output = self.run(['sh', '-c', 'adb logcat --pid=' + self.pid + ' | tac | grep "Received values" -B1000 -m1'])


        logger.info("Grabbing CalcyIV's log...")
        # Android 6 and lower:
        processOutput = subprocess.run(['sh', '-c', 'adb logcat -d | grep ' + self.pid + ' | tac | grep "Received values" -B1000 -m1'], stdout=subprocess.PIPE)
        # Android 7 and higher:
        #processOutput = subprocess.run(['adb', 'logcat' '--pid=' + self.pid, '-d | tac | grep "Received values" -B1000 -m1\''], stdout=subprocess.PIPE)

        outputSanitizedList = processOutput.stdout.decode('utf-8').strip().splitlines()
        return outputSanitizedList
