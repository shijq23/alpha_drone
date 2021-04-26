#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import cv2
import numpy as np
from djitellopy import Tello

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

fbRange = [6200, 10000]
pid = [0.4, 0.4, 0]
pError = 0
w, h = 360, 240


def initTello():
    drone = Tello()
    drone.connect()
    print("battery", drone.get_battery())
    drone.streamoff()
    drone.streamon()
    return drone

def telloGetFrame(drone, w=360, h=240):
    frame = drone.get_frame_read()
    img = frame.frame
    img = cv2.resize(img, (w, h))
    return img

def trackFace(tello, info, w, pid, pError):
    area = info[1]
    cx, cy = info[0]
    if area == 0 or cx == 0 or cy == 0:
        speed = 0
        error = 0
        fb = 0
    else:
        error = cx - w // 2
        speed = pid[0] * error + pid[1] * (error - pError)
        speed = int(np.clip(speed, -100, 100))  # yaw

        if area > fbRange[1]:
            fb = -20  # backward
        elif area < fbRange[0] and area > 0:
            fb = 20  # forward 
        else:
            fb = 0  # stay

    #tello.send_rc_control(0, fb, 0, speed)
    #print("fb", fb, "area", area)
    return error


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


tello = initTello()
while True:
    img = telloGetFrame(tello, w, h)
    img, info = findFace(img)
    pError = trackFace(tello, info, w, pid, pError)
    #print("center", info[0], "area", info[1])
    cv2.imshow("Output", img)
    if cv2.waitKey(50) != -1:
        break

#cap.release()
cv2.destroyAllWindows()
