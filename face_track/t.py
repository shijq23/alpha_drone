#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import time

import cv2
import numpy as np
import mediapipe as mp

from mockdjitellopy import Tello
from pid import PID

HANDLER = logging.StreamHandler()
FORMATTER = logging.Formatter(
    '[%(levelname)s] %(filename)s - %(lineno)d - %(message)s')
HANDLER.setFormatter(FORMATTER)

LOGGER = logging.getLogger('alpha')
LOGGER.addHandler(HANDLER)
LOGGER.setLevel(logging.INFO)

cv2_base_dir = os.path.dirname(os.path.abspath(cv2.__file__))
default_face = os.path.join(cv2_base_dir, "data",
                            "haarcascade_frontalface_default.xml")
default_eyes = os.path.join(cv2_base_dir, "data",
                            "haarcascade_eye_tree_eyeglasses.xml")
face_cascade = cv2.CascadeClassifier(default_face)
eye_cascade = cv2.CascadeClassifier(default_eyes)
if face_cascade.empty():
    LOGGER.warn(f"Error loading face cascade {default_face}")
    exit(0)

mp_face_detection = mp.solutions.face_detection
#mp_drawing = mp.solutions.drawing_utils
face_detection = mp_face_detection.FaceDetection(min_detection_confidence=0.5)

fbRange = [6200, 10000]  # forward backward measured in area
udRange = [80, 160]  # up down measured in height
lrRange = [110, 220]  # lef right measured in width
yawRange = [110, 220]  # yaw measued in width
pid = [0.4, 0.4, 0]
pError = 0
w, h = 360, 240

fb_pid = PID(kP=-0.07, kI=-0.00001, kD=0.001)
ud_pid = PID(kP=0.7, kI=0.0001, kD=-0.001)
lr_pid = PID(kP=0.7, kI=0.0001, kD=-0.001)
yaw_pid = PID(kP=0.7, kI=0.0001, kD=-0.001)

#Tello.LOGGER.setLevel(logging.DEBUG)
#PID.LOGGER.setLevel(logging.DEBUG)


def initTello():
    drone = Tello()
    drone.connect()
    LOGGER.info("battery {}".format(drone.get_battery()))
    drone.takeoff()
    drone.streamoff()
    drone.streamon()
    #time.sleep(0.5)
    return drone


def telloGetFrame(drone, w=360, h=240):
    frame = drone.get_frame_read()
    img = frame.frame
    img = cv2.resize(img, (w, h))
    return img


def trackFace(tello, info, w=360, h=240) -> None:
    area = info[1]
    cx, cy = info[0]
    if area == 0 or cx == 0 or cy == 0:
        lr_v = 0
        fb_v = 0
        ud_v = 0
        yaw_v = 0
    else:
        # left_right_velocity
        error = cx - w / 2
        lr_v = int(lr_pid.update(error))
        lr_v = np.clip(lr_v, -20, 20)

        # forward_backward_velocity
        error = area - w * h / 10
        fb_v = int(fb_pid.update(error))
        fb_v = np.clip(fb_v, -20, 20)
        #print("fb", fb_v, "area", area, "error", error)

        # up_down_velocity
        error = cy - h / 2
        ud_v = int(ud_pid.update(error))
        ud_v = np.clip(ud_v, -20, 20)

        # yaw_velocity
        error = cx - w / 2
        yaw_v = int(yaw_pid.update(error))
        yaw_v = np.clip(yaw_v, -20, 20)

    tello.send_rc_control(lr_v, fb_v, ud_v, yaw_v)
    #print("fb", fb_v, "area", area, "error", error)


def findFace(img):

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(image=gray,
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
        cv2.circle(img, (cx, cy), 5, (0, 255, 0), cv2.FILLED)

        # roi_gray = gray[y:y + h, x:x + w]
        # roi_color = img[y:y + h, x:x + w]
        # eyes = eye_cascade.detectMultiScale(roi_gray)
        # for (ex, ey, ew, eh) in eyes:
        #     cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), 2)

    if len(faceListArea) != 0:
        i = faceListArea.index(max(faceListArea))
        return img, [faceListCenter[i], faceListArea[i]]
    else:
        return img, [[0, 0], 0]


def findFace_mp(img):
    # Convert the BGR image to RGB and process it with MediaPipe Face Detection.
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = face_detection.process(rgb)
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
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 255, 0), 1, cv2.LINE_AA)
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


def putFPS(img) -> None:
    cur_time = time.time()
    fps = 1.0 / (cur_time - putFPS.prev_time)
    fps = int(fps)
    putFPS.prev_time = cur_time
    cv2.putText(img, f"FPS: {fps}", (7, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                (100, 255, 0), 1, cv2.LINE_AA)


putFPS.prev_time = time.time()

tello = initTello()
fb_pid.reset()
lr_pid.reset()
ud_pid.reset()
yaw_pid.reset()
while True:
    img = telloGetFrame(tello)
    img, info = findFace_mp(img)
    trackFace(tello, info)
    #print("center", info[0], "area", info[1])
    putFPS(img)
    cv2.imshow("alpha drone", img)
    if cv2.waitKey(1) != -1:
        tello.land()
        break

#cap.release()
cv2.destroyAllWindows()
tello.end()
