"""E-puck controller: reliable single-pixel color detection + multi-color sequence + resume navigation"""
from controller import Robot
import cv2 as cv
import numpy as np
import os

TIME_STEP = 32
MAX_SPEED = 6.28
DIST_LIMIT = 70.0

# Color detection thresholds
# Red thresholds
R_MIN_RED = 100
G_MAX_RED = 80
B_MAX_RED = 80

# Green thresholds
R_MAX_GREEN = 80
G_MIN_GREEN = 100
B_MAX_GREEN = 80

# Blue thresholds
R_MAX_BLUE = 80
G_MAX_BLUE = 80
B_MIN_BLUE = 100

COLOURS = ["red", "green", "blue"]

robot = Robot()

# Motors
leftMotor = robot.getDevice('left wheel motor')
rightMotor = robot.getDevice('right wheel motor')

leftMotor.setPosition(float('inf'))
rightMotor.setPosition(float('inf'))

# Proximity sensors
rightSensor1 = robot.getDevice('ps0')
rightSensor2 = robot.getDevice('ps1')
leftSensor1 = robot.getDevice('ps7')
leftSensor2 = robot.getDevice('ps6')

rightSensor1.enable(TIME_STEP)
rightSensor2.enable(TIME_STEP)
leftSensor1.enable(TIME_STEP)
leftSensor2.enable(TIME_STEP)

# Camera
cam = robot.getDevice('camera')
cam.enable(TIME_STEP)

W = cam.getWidth()
H = cam.getHeight()

# Create folder to save images on Desktop
DESKTOP_PATH = os.path.expanduser("~/Desktop")
SAVE_FOLDER = os.path.join(DESKTOP_PATH, "webot_img")
os.makedirs(SAVE_FOLDER, exist_ok=True)

image_count = 0
encountered = []
active_target = None  # Tracks if we are currently holding/stopping for a color


# ----------------------------------
# Proximity sensor functions
# ----------------------------------

def get_left_sensor():
    value1 = leftSensor1.getValue()
    value2 = leftSensor2.getValue()
    average = (value1 + value2) / 2.0
    return average > DIST_LIMIT


def get_right_sensor():
    value1 = rightSensor1.getValue()
    value2 = rightSensor2.getValue()
    average = (value1 + value2) / 2.0
    return average > DIST_LIMIT


# ----------------------------------
# Multi-color center detection
# ----------------------------------

def detect_center_colour():
    img = cam.getImage()
    if img is None:
        return None

    x = W // 2
    y = H // 2

    r = cam.imageGetRed(img, W, x, y)
    g = cam.imageGetGreen(img, W, x, y)
    b = cam.imageGetBlue(img, W, x, y)

    # Check Red
    if (r > R_MIN_RED) and (g < G_MAX_RED) and (b < B_MAX_RED):
        return "red"
    # Check Green
    elif (r < R_MAX_GREEN) and (g > G_MIN_GREEN) and (b < B_MAX_GREEN):
        return "green"
    # Check Blue
    elif (r < R_MAX_BLUE) and (g < G_MAX_BLUE) and (b > B_MIN_BLUE):
        return "blue"

    return None


# ----------------------------------
# Capture and save camera image
# ----------------------------------

def save_camera_image(color_name):
    global image_count

    img = cam.getImage()
    if img is None:
        print("Camera image unavailable")
        return

    # Convert Webots image to NumPy array
    image_array = np.frombuffer(img, dtype=np.uint8)
    image_array = image_array.reshape((H, W, 4))

    # Convert BGRA to BGR
    image_bgr = cv.cvtColor(image_array, cv.COLOR_BGRA2BGR)

    image_count += 1
    filename = f"{color_name}_object_{image_count:03d}.jpg"
    filepath = os.path.join(SAVE_FOLDER, filename)

    success = cv.imwrite(filepath, image_bgr)

    if success:
        print(f"Image saved: {filepath}")
    else:
        print("Failed to save image")


# ----------------------------------
# Robot movement functions
# ----------------------------------

def stop():
    leftMotor.setVelocity(0.0)
    rightMotor.setVelocity(0.0)


def move_forward():
    leftMotor.setVelocity(0.5 * MAX_SPEED)
    rightMotor.setVelocity(0.5 * MAX_SPEED)


def move_backward():
    leftMotor.setVelocity(-0.5 * MAX_SPEED)
    rightMotor.setVelocity(-0.5 * MAX_SPEED)


def turn_left():
    leftMotor.setVelocity(0.1 * MAX_SPEED)
    rightMotor.setVelocity(0.5 * MAX_SPEED)


def turn_right():
    leftMotor.setVelocity(0.5 * MAX_SPEED)
    rightMotor.setVelocity(0.1 * MAX_SPEED)


# ----------------------------------
# Main controller
# ----------------------------------

def main():
    global encountered, active_target

    TIME_DELAY = 0.5
    time_start = robot.getTime()
    pause_until = 0.0

    move_forward()

    while robot.step(TIME_STEP) != -1:
        now = robot.getTime()

        # If we are currently paused after capturing an object, wait a moment before resuming navigation
        if active_target is not None:
            if now < pause_until:
                continue
            else:
                # Done pausing, clear target and resume moving forward
                active_target = None
                move_forward()
                time_start = now

        # 1. Color detection (only check for colors we haven't encountered yet)
        detected = detect_center_colour()
        if detected and detected not in encountered:
            stop()
            print(f"{detected.upper()} detected! Stopping.")
            
            # Save image and record finding
            save_camera_image(detected)
            encountered.append(detected)
            
            remaining = [c for c in COLOURS if c not in encountered]
            print(f"Summary - encountered: {', '.join(encountered)} | not yet: {', '.join(remaining) if remaining else 'none'}")

            # Mark as active target and set a 1.5-second pause before driving away to avoid immediate re-triggering
            active_target = detected
            pause_until = now + 1.5
            
            # Briefly reverse away from the block so it has room to turn and navigate away
            move_backward()
            continue

        # 2. Obstacle avoidance navigation
        time_elapsed = robot.getTime()
        time_diff = time_elapsed - time_start

        if time_diff >= TIME_DELAY:
            blocked_left = get_left_sensor()
            blocked_right = get_right_sensor()

            if blocked_left and blocked_right:
                move_backward()
            elif blocked_left:
                turn_right()
            elif blocked_right:
                turn_left()
            else:
                move_forward()

            time_start = time_elapsed


if __name__ == '__main__':
    main()
