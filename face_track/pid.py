# import necessary packages
# -*- coding: utf-8 -*-
import time
import logging


class PID(object):

    EPSILON = 1e-3 # the minium delta time in seconds
    HANDLER = logging.StreamHandler()
    FORMATTER = logging.Formatter('[%(levelname)s] %(filename)s - %(lineno)d - %(message)s')
    HANDLER.setFormatter(FORMATTER)

    LOGGER = logging.getLogger('pid')
    LOGGER.addHandler(HANDLER)
    LOGGER.setLevel(logging.INFO)
    
    def __init__(self, kP:float=1.0, kI:float=0.0, kD:float=0.0) -> any:
        super().__init__()
        # initialize gains
        self.kP = kP
        self.kI = kI
        self.kD = kD

        self.cP = 0.0
        self.cI = 0.0
        self.cD = 0.0
        self.cV = 0.0

        self.currTime = time.time()
        self.prevTime = self.currTime
        self.prevError = 0.0

    def reset(self) -> None:
        # reset the current and previous time
        self.currTime = time.time()
        self.prevTime = self.currTime

        # reset the previous error
        self.prevError = 0.0

        # reset the term result variables
        self.cP = 0.0
        self.cI = 0.0
        self.cD = 0.0
        self.cV = 0.0

    def update(self, error: float) -> float:
        # grab the current time and calculate delta time
        self.currTime = time.time()
        deltaTime = self.currTime - self.prevTime
        deltaTime = .033
        # if deltaTime < PID.EPSILON:
        #     return self.cV

        # calculate the delta error
        deltaError = error - self.prevError

        # calculate the proportional term
        self.cP = error

        # calculate the integral term
        self.cI += error * deltaTime

        # calculate the derivative term (and prevent divide by zero)
        self.cD = (deltaError / deltaTime) if deltaTime > 0.0 else 0.0

        # save previous time and error for the next update
        self.prevTime = self.currTime
        self.prevError = error

        # sum the terms and return
        self.cV = sum([self.kP * self.cP, self.kI * self.cI, self.kD * self.cD])
        PID.LOGGER.debug(f"{self.cP} {self.cI} {self.cD} {self.cV}")
        return self.cV
