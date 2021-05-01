#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import atexit
import logging
import math
import os
import time

import cv2
import keyboard
import numpy as np

from mockdjitellopy import Tello
from pid import PID

# import mediapipe as mp


class FaceTracker(object):
    HANDLER = logging.StreamHandler()
    FORMATTER = logging.Formatter(
        '[%(levelname)s] %(filename)s - %(lineno)d - %(message)s')
    HANDLER.setFormatter(FORMATTER)

    LOGGER = logging.getLogger('alpha')
    LOGGER.addHandler(HANDLER)
    LOGGER.setLevel(logging.INFO)

    MAX_COMMAND_SEC: int = 100  # throttle control, max number of commands per second

    cv2_base_dir = os.path.dirname(os.path.abspath(cv2.__file__))
    default_face = os.path.join(cv2_base_dir, "data",
                                "haarcascade_frontalface_default.xml")
    face_cascade = cv2.CascadeClassifier(default_face)
    if face_cascade.empty():
        LOGGER.warn(f"Error loading face cascade {default_face}")
        exit(0)

    default_eyes = os.path.join(cv2_base_dir, "data",
                                "haarcascade_eye_tree_eyeglasses.xml")
    eye_cascade = cv2.CascadeClassifier(default_eyes)
    if eye_cascade.empty():
        LOGGER.warn(f"Error loading eye cascade {default_eyes}")
        exit(0)

    # mp_face_detection = mp.solutions.face_detection
    # #mp_drawing = mp.solutions.drawing_utils
    # face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.5)

    #Tello.LOGGER.setLevel(logging.DEBUG)
    #PID.LOGGER.setLevel(logging.DEBUG)

    def __init__(self, w: int = 320, h: int = 240) -> None:
        super().__init__()

        self.drone = FaceTracker.initTello()
        self.prev_time = time.time()
        self.w: int = w
        self.h: int = h

        self.fb_pid = PID('fb',
                          kP=0.7,
                          kI=0.0,
                          kD=-0.5,
                          SP=math.sqrt(w * h / 10))
        self.ud_pid = PID('ud', kP=0.7, kI=-0.0, kD=-0.5, SP=h / 2)
        self.lr_pid = PID('lr', kP=-0.7, kI=-0.0, kD=0.5, SP=w / 2)
        self.yaw_pid = PID('yaw', kP=-0.7, kI=-0.0, kD=0.5, SP=w / 2)

        self.fb_pid.reset()
        self.lr_pid.reset()
        self.ud_pid.reset()
        self.yaw_pid.reset()
        self.fps: int = 0
        self.track_count: int = 0

        self.fb_override: int = 0
        self.lr_override: int = 0
        self.ud_override: int = 0
        self.yaw_override: int = 0

        atexit.register(self.end)

    @staticmethod
    def initTello() -> Tello:
        drone = Tello(retry_count=1)
        drone.connect()

        FaceTracker.LOGGER.info("battery {}".format(drone.get_battery()))
        drone.streamoff()
        drone.streamon()
        drone.get_frame_read()
        drone.takeoff()
        drone.send_rc_control(0, 0, 0, 0)
        drone.move_up(70)
        return drone

    def _throttle(self):
        t = self.fps <= FaceTracker.MAX_COMMAND_SEC
        if not t:
            interval = self.fps // FaceTracker.MAX_COMMAND_SEC
            t = self.track_count % interval == 0
        #FaceTracker.LOGGER.info(f"{self.track_count} {t} {self.fps}")
        self.track_count += 1
        return t

    def readFrame(self):
        frame = self.drone.get_frame_read()
        img = frame.frame
        img = cv2.resize(img, (self.w, self.h))
        return img

    def trackFace(self, info) -> None:
        area = info[1]
        cx, cy = info[0]

        def clip(x: int, lower: int = -100, upper: int = 100) -> int:
            return max(lower, min(upper, x))

        # lr_v = 0  left -100, right 100
        # fb_v = 0  backward -100, forward 100
        # ud_v = 0  down -100, up 100
        # yaw_v = 0 ccw -100, cw 100
        if self.lr_override or self.fb_override or self.ud_override or self.yaw_override:
            lr_v = self.lr_override
            fb_v = self.fb_override
            ud_v = self.ud_override
            yaw_v = self.yaw_override
            self.lr_override = 0
            self.fb_override = 0
            self.ud_override = 0
            self.yaw_override = 0
        elif area == 0 or cx == 0 or cy == 0:
            lr_v = 0
            fb_v = 0
            ud_v = 0
            yaw_v = 0
        else:
            # left_right_velocity
            lr_v = int(self.lr_pid.update(cx))
            lr_v = clip(lr_v, -5, 5)
            # lr_v = 0

            # forward_backward_velocity
            pv = math.sqrt(area)
            fb_v = int(self.fb_pid.update(pv))
            fb_v = clip(fb_v, -20, 20)
            # fb_v = 0

            # up_down_velocity
            ud_v = int(self.ud_pid.update(cy))
            ud_v = clip(ud_v, -10, 10)
            # ud_v = 0

            # yaw_velocity
            yaw_v = int(self.yaw_pid.update(cx))
            yaw_v = clip(yaw_v, -20, 20)
            # yaw_v = 0

        #if self._throttle():
        self.drone.send_rc_control(lr_v, fb_v, ud_v, yaw_v)
        FaceTracker.LOGGER.debug(
            f"{lr_v:>3d} {fb_v:>3d} {ud_v:>3d} {yaw_v:>3d}")
        #print("fb", fb_v, "area", area, "error", error)

    def findFace(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(image=gray,
                                                   scaleFactor=1.3,
                                                   minNeighbors=8,
                                                   minSize=(20, 30),
                                                   maxSize=(160, 200))

        faceListCenter = []
        faceListArea = []

        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cx = x + w // 2
            cy = y + h // 2
            area = w * h

            faceListCenter.append([cx, cy])
            faceListArea.append(area)
            cv2.circle(img, (cx, cy), 4, (0, 255, 0), cv2.FILLED)

            roi_gray = gray[y:y + h, x:x + w]
            roi_color = img[y:y + h, x:x + w]
            eyes = self.eye_cascade.detectMultiScale(roi_gray)
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh),
                              (0, 255, 0), 2)

        if len(faceListArea) != 0:
            i = faceListArea.index(max(faceListArea))
            return img, [faceListCenter[i], faceListArea[i]]
        else:
            return img, [[0, 0], 0]

    def findFace_mp(self, img):
        # Convert the BGR image to RGB and process it with MediaPipe Face Detection.
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb)
        #print(results)

        if not results.detections:
            return img, [[0, 0], 0]

        faceListCenter = []
        faceListArea = []

        for detection in results.detections:
            #print(mp_face_detection.get_key_point(detection, mp_face_detection.FaceKeyPoint.NOSE_TIP))
            #mp_drawing.draw_detection(img, detection)
            box = detection.location_data.relative_bounding_box
            ih, iw, ic = img.shape
            (x, y, w, h) = (int(box.xmin * iw), int(box.ymin * ih),
                            int(box.width * iw), int(box.height * ih))
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(img, f"{int(detection.score[0]*100)}%", (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 255, 0), 1,
                        cv2.LINE_AA)
            cx = int(x + w / 2)
            cy = int(y + h / 2)
            area = w * h
            faceListCenter.append([cx, cy])
            faceListArea.append(area)
            cv2.circle(img, (cx, cy), 5, (0, 255, 0), cv2.FILLED)

        if len(faceListArea) != 0:
            i = faceListArea.index(max(faceListArea))
            return img, [faceListCenter[i], faceListArea[i]]
        else:
            return img, [[0, 0], 0]

    def putFPS(self, img) -> None:
        cur_time = time.time()
        fps = 1.0 / (cur_time - self.prev_time)
        fps = int(fps)
        self.prev_time = cur_time
        self.fps = fps
        cv2.putText(img, f"FPS: {fps}", (7, 30), cv2.FONT_HERSHEY_PLAIN, 1,
                    (100, 255, 0), 1, cv2.LINE_AA)

    def putBattery(self, img) -> None:
        ih, iw, ic = img.shape
        battery = self.drone.get_battery()
        color = (100, 255, 0) if battery > 20 else (100, 0, 255)
        cv2.putText(img, f"BAT: {battery}%", (iw - 90, 30),
                    cv2.FONT_HERSHEY_PLAIN, 1, color, 1, cv2.LINE_AA)

    def end(self) -> None:
        FaceTracker.LOGGER.info("end")
        try:
            self.drone.end()
        except AttributeError:
            pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        FaceTracker.LOGGER.info("exit")
        self.end()

    def __del__(self):
        FaceTracker.LOGGER.info("del")
        self.end()
        try:
            super().__del__(self)
        except AttributeError:
            pass


request_run: bool = True


def kbdCallback(e) -> None:
    global request_run
    #print(e.name)
    if e.name == "up":
        kbdCallback.alpha.fb_override = 20
    elif e.name == "down":
        kbdCallback.alpha.fb_override = -20
    elif e.name == "left":
        kbdCallback.alpha.lr_override = -20
    elif e.name == "right":
        kbdCallback.alpha.lr_override = 20
    else:
        request_run = False


kbdCallback.alpha = {}


def main():
    alpha = FaceTracker()
    kbdCallback.alpha = alpha
    keyboard.on_press(kbdCallback)

    while request_run:
        img = alpha.readFrame()
        img, info = alpha.findFace(img)
        alpha.trackFace(info)
        #print("center", info[0], "area", info[1])
        alpha.putFPS(img)
        alpha.putBattery(img)
        cv2.imshow("alpha drone", img)
        cv2.waitKey(1)

    #cap.release()
    cv2.destroyAllWindows()
    alpha.end()


if __name__ == "__main__":
    main()
