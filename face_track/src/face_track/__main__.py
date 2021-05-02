#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

import cv2

from face_track import tracker

request_run: bool = True


def main(args=None):
    """The main routine."""
    if args is None:
        args = sys.argv[1:]

    alpha = tracker.FaceTracker()
    while request_run:
        img = alpha.readFrame()
        img, info = alpha.findFace(img)
        alpha.trackFace(info)
        #print("center", info[0], "area", info[1])
        alpha.putFPS(img)
        alpha.putBattery(img)
        alpha.putTemperature(img)
        alpha.putFlight(img)
        cv2.imshow("Alpha Drone", img)
        if cv2.waitKey(1) != -1:
            break

    #cap.release()
    cv2.destroyAllWindows()
    alpha.end()


if __name__ == "__main__":
    sys.exit(main())
