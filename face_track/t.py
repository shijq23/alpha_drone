#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging

import cv2
import numpy as np
from mockdjitellopy import Tello
from pid import PID

cv2_base_dir = os.path.dirname(os.path.abspath(cv2.__file__))
default_face = os.path.join(cv2_base_dir, "data",
                            "haarcascade_frontalface_default.xml")
default_eyes = os.path.join(cv2_base_dir, "data",
                            "haarcascade_eye_tree_eyeglasses.xml")
face_cascade = cv2.CascadeClassifier(default_face)
eye_cascade = cv2.CascadeClassifier(default_eyes)
if face_cascade.empty():
    print("--(!)Error loading face cascade", default_face)
    exit(0)

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

Tello.LOGGER.setLevel(logging.DEBUG)
#PID.LOGGER.setLevel(logging.DEBUG)


def initTello():
    drone = Tello()
    drone.connect()
    print("battery", drone.get_battery())
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
        error = cx - w /2
        yaw_v = int(yaw_pid.update(error))
        yaw_v = np.clip(yaw_v, -20, 20)


    tello.send_rc_control(lr_v, fb_v, ud_v, yaw_v)
    #print("fb", fb_v, "area", area, "error", error)


def findFace(img):

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 8)

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


def putFPS(img, prev_time):
    cur_time = time.time()
    fps = 1.0 / (cur_time - prev_time)
    fps = int(fps)
    cv2.putText(img, str(fps), (7, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                (100, 255, 0), 1, cv2.LINE_AA)
    return cur_time


tello = initTello()
prev_time = time.time()
fb_pid.reset()
lr_pid.reset()
ud_pid.reset()
yaw_pid.reset()
while True:
    img = telloGetFrame(tello)
    img, info = findFace(img)
    trackFace(tello, info)
    #print("center", info[0], "area", info[1])
    prev_time = putFPS(img, prev_time)
    cv2.imshow("alpha drone", img)
    if cv2.waitKey(1) != -1:
        break

#cap.release()
cv2.destroyAllWindows()
#tello.end()
