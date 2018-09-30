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
        self.use_fallback_screenshots = False
        self.resolution = None

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

        try:
            return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "shell", "pidof", "-s", "tesmath.calcy"])
        except Exception as e:
            raise CalcyIVNotRunning
        self.pid = stdout.decode('utf-8').strip()

        try:
            # Android Version
            return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "shell", "getprop", "ro.build.version.release"])
            self.version_android = int(stdout.decode('utf-8').strip()[0])
        except Exception as e:
            # Assume old phone
            logger.info('Could not detect your Android version! :(')
            self.version_android = 4

        try:
            # SDK Version
            return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "shell", "getprop", "ro.build.version.sdk"])
            self.version_sdk = int(stdout.decode('utf-8').strip())
        except Exception as e:
            # Assume old phone
            logger.info('Could not detect your SDK version! :(')
            self.version_sdk = 0

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
        logger.debug("Tapping on " + format(self.get_x(x), '>4d') + " x " + format(self.get_y(y), '<4d') + "  (" + format(x, '>.2f') + "% x " + format(y, '<.2f') + "%) and waiting " + str(sleep) + "seconds...")
        time.sleep(sleep)

    def key(self, key, sleep):
        self.run(["adb", "-s", self.device_id, "shell", "input", "keyevent", key])
        logger.debug("Pressing key " + key + " and waiting " + str(sleep) + " seconds...")
        time.sleep(sleep)

    def type(self, text, sleep):
        self.run(["adb", "-s", self.device_id, "shell", "input", "type", text])
        logger.debug("Writing " + text + " and waiting " + str(sleep) + " seconds...")
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
        logger.debug("Sending intent: " + intent + " to " + package + "...")
        if self.user_id is not None:
            # For CalcyIV inside Island or other sandboxing app
            return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "shell", "am broadcast --user " + self.user_id + " -a {} --ez silentMode true -n {}".format(intent, package)])
        else:
            # Default: no white box (faster and betta).
            return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "shell", "am broadcast -a {} --ez silentMode true -n {}".format(intent, package)])
            # Old method: with white box
            # return_code, stdout, stderr = self.run(["adb", "-s", self.device_id, "shell", "am broadcast -a {} -n {}".format(intent, package)])

        time.sleep(sleep)

    def get_last_logcat(self, sleep=0):
        '''
        Grabs only the last return line of CalcyIV, and everything after it,
        instead of watching the logcat, which causes problems with buffers sync.

        The same as running:
            sh -c 'adb logcat -d | \grep $(adb shell pidof -s tesmath.calcy) | tac | grep "Received values" -B1000 -m1'
        Or, for Android 7 and higher:
            sh -c 'adb logcat -d --pid=$(adb shell pidof -s tesmath.calcy) | tac | grep "Received values" -B1000 -m1'
        '''
        time.sleep(sleep)

        logger.info("Grabbing CalcyIV's log...")
        # TODO: loop here until the log is good to go, instead of looping on the main script (ivcheck.py)
        # while outputSanitizedList is not empty, something like that.
        if self.version_android >= 7:
            # Android 7 and higher have logcat with '--pid' argument available.
            processOutput = subprocess.run(['sh', '-c', 'adb logcat -d -t ' + str((12 + sleep)) + ' --pid=' + self.pid + ' | tac | grep "Received values" -B1000 -m1'], stdout=subprocess.PIPE)
        else:
            # Android 6 and lower:
            processOutput = subprocess.run(['sh', '-c', 'adb logcat -d -t ' + str((12 + sleep)) + ' | grep ' + self.pid + ' | tac | grep "Received values" -B1000 -m1'], stdout=subprocess.PIPE)

        outputSanitizedList = processOutput.stdout.decode('utf-8').strip().splitlines()
        return outputSanitizedList

    def get_clipboard_from_device(self):
        processOutput = subprocess.run(['sh', '-c', 'adb shell am broadcast -a clipper.get | grep data | sed "s/^.*data=.\\(.*\\)..*/\\1/"'], stdout=subprocess.PIPE)
        outputSanitizedList = processOutput.stdout.decode('utf-8').strip().splitlines()
        return outputSanitizedList
        return processOutput
