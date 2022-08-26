# coding=utf-8
import collections
import time

import cv2
import numpy as np


class FPSHandler:
    """
    Class that handles all FPS-related operations. Mostly used to calculate different streams FPS, but can also be
    used to feed the video file based on it's FPS property, not app performance (this prevents the video from being sent
    to quickly if we finish processing a frame earlier than the next video frame should be consumed)
    """

    _fpsBgColor = (0, 0, 0)
    _fpsColor = (255, 255, 255)
    _fpsType = cv2.FONT_HERSHEY_SIMPLEX
    _fpsLineType = cv2.LINE_AA

    def __init__(self, cap=None, maxTicks=100):
        """
        Args:
            cap (cv2.VideoCapture, Optional): handler to the video file object
            maxTicks (int, Optional): maximum ticks amount for FPS calculation
        """
        self._timestamp = None
        self._start = None
        self._framerate = cap.get(cv2.CAP_PROP_FPS) if cap is not None else None
        self._useCamera = cap is None

        self._iterCnt = 0
        self._ticks = {}

        if maxTicks < 2:
            raise ValueError(f"Proviced maxTicks value must be 2 or higher (supplied: {maxTicks})")

        self._maxTicks = maxTicks

    def nextIter(self):
        """
        Marks the next iteration of the processing loop. Will use :obj:`time.sleep` method if initialized with video file
        object
        """
        if self._start is None:
            self._start = time.monotonic()

        if not self._useCamera and self._timestamp is not None:
            frameDelay = 1.0 / self._framerate
            delay = (self._timestamp + frameDelay) - time.monotonic()
            if delay > 0:
                time.sleep(delay)
        self._timestamp = time.monotonic()
        self._iterCnt += 1

    def tick(self, name):
        """
        Marks a point in time for specified name
        Args:
            name (str): Specifies timestamp name
        """
        if name not in self._ticks:
            self._ticks[name] = collections.deque(maxlen=self._maxTicks)
        self._ticks[name].append(time.monotonic())

    def tickFps(self, name):
        """
        Calculates the FPS based on specified name
        Args:
            name (str): Specifies timestamps' name
        Returns:
            float: Calculated FPS or :code:`0.0` (default in case of failure)
        """
        if name in self._ticks and len(self._ticks[name]) > 1:
            timeDiff = self._ticks[name][-1] - self._ticks[name][0]
            return (len(self._ticks[name]) - 1) / timeDiff if timeDiff != 0 else 0.0
        else:
            return 0.0

    def fps(self):
        """
        Calculates FPS value based on :func:`nextIter` calls, being the FPS of processing loop
        Returns:
            float: Calculated FPS or :code:`0.0` (default in case of failure)
        """
        if self._start is None or self._timestamp is None:
            return 0.0
        timeDiff = self._timestamp - self._start
        return self._iterCnt / timeDiff if timeDiff != 0 else 0.0

    def printStatus(self):
        """
        Prints total FPS for all names stored in :func:`tick` calls
        """
        print("=== TOTAL FPS ===")
        for name in self._ticks:
            print(f"[{name}]: {self.tickFps(name):.1f}")

    def drawFps(self, frame, name):
        """
        Draws FPS values on requested frame, calculated based on specified name
        Args:
            frame (numpy.ndarray): Frame object to draw values on
            name (str): Specifies timestamps' name
        """
        frameFps = f"{name.upper()} FPS: {round(self.tickFps(name), 1)}"
        # cv2.rectangle(frame, (0, 0), (120, 35), (255, 255, 255), cv2.FILLED)
        cv2.putText(frame, frameFps, (5, 15), self._fpsType, 0.5, self._fpsBgColor, 4, self._fpsLineType)
        cv2.putText(frame, frameFps, (5, 15), self._fpsType, 0.5, self._fpsColor, 1, self._fpsLineType)

        if "nn" in self._ticks:
            cv2.putText(frame, f"NN FPS:  {round(self.tickFps('nn'), 1)}", (5, 30), self._fpsType, 0.5,
                        self._fpsBgColor, 4, self._fpsLineType)
            cv2.putText(frame, f"NN FPS:  {round(self.tickFps('nn'), 1)}", (5, 30), self._fpsType, 0.5, self._fpsColor,
                        1, self._fpsLineType)


def frameNorm(frame, bbox):
    """
    It takes a bounding box and a frame, and returns the bounding box in pixel coordinates

    :param frame: the frame to be processed
    :param bbox: The bounding box of the face
    :return: The bounding box coordinates are being normalized to the frame size.
    """
    normVals = np.full(len(bbox), frame.shape[0])
    normVals[::2] = frame.shape[1]
    return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)


def drawText(
        frame, text, org, color="black", bg_color="gray", font_scale=0.5, thickness=1
):
    if isinstance(color, str):
        color = color_tables.get(color.lower(), "black")
    if isinstance(bg_color, str):
        bg_color = color_tables.get(bg_color.lower(), "gray")
    cv2.putText(
        frame,
        text,
        org,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        bg_color,
        thickness + 3,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        text,
        org,
        cv2.FONT_HERSHEY_SIMPLEX,
        font_scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def drawRect(frame, p1, p2, color="black", bg_color="gray", thickness=1):
    if isinstance(color, str):
        color = color_tables.get(color.lower(), "black")
    if isinstance(bg_color, str):
        bg_color = color_tables.get(bg_color.lower(), "gray")
    cv2.rectangle(frame, pt1=p1, pt2=p2, color=bg_color, thickness=thickness + 5)
    cv2.rectangle(frame, pt1=p1, pt2=p2, color=bg_color, thickness=thickness)


color_tables = {
    "aliceblue": (255, 248, 240),
    "antiquewhite": (215, 235, 250),
    "aqua": (255, 255, 0),
    "aquamarine": (212, 255, 127),
    "azure": (255, 255, 240),
    "beige": (220, 245, 245),
    "bisque": (196, 228, 255),
    "black": (0, 0, 0),
    "blanchedalmond": (205, 235, 255),
    "blue": (255, 0, 0),
    "blueviolet": (226, 43, 138),
    "brown": (42, 42, 165),
    "burlywood": (135, 184, 222),
    "cadetblue": (160, 158, 95),
    "chartreuse": (0, 255, 127),
    "chocolate": (30, 105, 210),
    "coral": (80, 127, 255),
    "cornflowerblue": (237, 149, 100),
    "cornsilk": (220, 248, 255),
    "crimson": (60, 20, 220),
    "cyan": (255, 255, 0),
    "darkblue": (139, 0, 0),
    "darkcyan": (139, 139, 0),
    "darkgoldenrod": (11, 134, 184),
    "darkgray": (169, 169, 169),
    "darkgreen": (0, 100, 0),
    "darkgrey": (169, 169, 169),
    "darkkhaki": (107, 183, 189),
    "darkmagenta": (139, 0, 139),
    "darkolivegreen": (47, 107, 85),
    "darkorange": (0, 140, 255),
    "darkorchid": (204, 50, 153),
    "darkred": (0, 0, 139),
    "darksalmon": (122, 150, 233),
    "darkseagreen": (143, 188, 143),
    "darkslateblue": (139, 61, 72),
    "darkslategray": (79, 79, 47),
    "darkslategrey": (79, 79, 47),
    "darkturquoise": (209, 206, 0),
    "darkviolet": (211, 0, 148),
    "deeppink": (147, 20, 255),
    "deepskyblue": (255, 191, 0),
    "dimgray": (105, 105, 105),
    "dimgrey": (105, 105, 105),
    "dodgerblue": (255, 144, 30),
    "firebrick": (34, 34, 178),
    "floralwhite": (240, 250, 255),
    "forestgreen": (34, 139, 34),
    "fuchsia": (255, 0, 255),
    "gainsboro": (220, 220, 220),
    "ghostwhite": (255, 248, 248),
    "gold": (0, 215, 255),
    "goldenrod": (32, 165, 218),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "green": (0, 128, 0),
    "greenyellow": (47, 255, 173),
    "honeydew": (240, 255, 240),
    "hotpink": (180, 105, 255),
    "indianred": (92, 92, 205),
    "indigo": (130, 0, 75),
    "ivory": (240, 255, 255),
    "khaki": (140, 230, 240),
    "lavender": (250, 230, 230),
    "lavenderblush": (245, 240, 255),
    "lawngreen": (0, 252, 124),
    "lemonchiffon": (205, 250, 255),
    "lightblue": (230, 216, 173),
    "lightcoral": (128, 128, 240),
    "lightcyan": (255, 255, 224),
    "lightgoldenrodyellow": (210, 250, 250),
    "lightgray": (211, 211, 211),
    "lightgreen": (144, 238, 144),
    "lightgrey": (211, 211, 211),
    "lightpink": (193, 182, 255),
    "lightsalmon": (122, 160, 255),
    "lightseagreen": (170, 178, 32),
    "lightskyblue": (250, 206, 135),
    "lightslategray": (153, 136, 119),
    "lightslategrey": (153, 136, 119),
    "lightsteelblue": (222, 196, 176),
    "lightyellow": (224, 255, 255),
    "lime": (0, 255, 0),
    "limegreen": (50, 205, 50),
    "linen": (230, 240, 250),
    "magenta": (255, 0, 255),
    "maroon": (0, 0, 128),
    "mediumaquamarine": (170, 205, 102),
    "mediumblue": (205, 0, 0),
    "mediumorchid": (211, 85, 186),
    "mediumpurple": (219, 112, 147),
    "mediumseagreen": (113, 179, 60),
    "mediumslateblue": (238, 104, 123),
    "mediumspringgreen": (154, 250, 0),
    "mediumturquoise": (204, 209, 72),
    "mediumvioletred": (133, 21, 199),
    "midnightblue": (112, 25, 25),
    "mintcream": (250, 255, 245),
    "mistyrose": (225, 228, 255),
    "moccasin": (181, 228, 255),
    "navajowhite": (173, 222, 255),
    "navy": (128, 0, 0),
    "oldlace": (230, 245, 253),
    "olive": (0, 128, 128),
    "olivedrab": (35, 142, 107),
    "orange": (0, 165, 255),
    "orangered": (0, 69, 255),
    "orchid": (214, 112, 218),
    "palegoldenrod": (170, 232, 238),
    "palegreen": (152, 251, 152),
    "paleturquoise": (238, 238, 175),
    "palevioletred": (147, 112, 219),
    "papayawhip": (213, 239, 255),
    "peachpuff": (185, 218, 255),
    "peru": (63, 133, 205),
    "pink": (203, 192, 255),
    "plum": (221, 160, 221),
    "powderblue": (230, 224, 176),
    "purple": (128, 0, 128),
    "red": (0, 0, 255),
    "rosybrown": (143, 143, 188),
    "royalblue": (225, 105, 65),
    "saddlebrown": (19, 69, 139),
    "salmon": (114, 128, 250),
    "sandybrown": (96, 164, 244),
    "seagreen": (87, 139, 46),
    "seashell": (238, 245, 255),
    "sienna": (45, 82, 160),
    "silver": (192, 192, 192),
    "skyblue": (235, 206, 135),
    "slateblue": (205, 90, 106),
    "slategray": (144, 128, 112),
    "slategrey": (144, 128, 112),
    "snow": (250, 250, 255),
    "springgreen": (127, 255, 0),
    "steelblue": (180, 130, 70),
    "tan": (140, 180, 210),
    "teal": (128, 128, 0),
    "thistle": (216, 191, 216),
    "tomato": (71, 99, 255),
    "turquoise": (208, 224, 64),
    "violet": (238, 130, 238),
    "wheat": (179, 222, 245),
    "white": (255, 255, 255),
    "whitesmoke": (245, 245, 245),
    "yellow": (0, 255, 255),
    "yellowgreen": (50, 205, 154),
}
