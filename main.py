#!/usr/bin/env python3
import sys
from time import sleep
import time
import cv2
import os
import requests
import hashlib
import json
from os import path


def getSha1Hash(string):
    return hashlib.sha1(string.encode()).hexdigest()


camera_name = None
api_key = None
FINGERPRINT = getSha1Hash("FINGERPRINT")
FORCE_RESOLUTION = {
    "width": 1280,
    "height": 720,
}


def do_snapshot(data):
    global api_key, FINGERPRINT
    url = "https://webcam.connect.prusa3d.com/c/snapshot"
    headers = {
        "token": api_key,
        "Content-Type": "image/jpeg",
        "fingerprint": FINGERPRINT,
        "timestamp": str(int(time.time())),
    }

    res = requests.put(url, headers=headers, data=data)
    if res.status_code != 204:
        print(f"do_snapshot() Response: {res.status_code} ({res.reason})")
    return res


def do_info():
    global camera_name, api_key, FINGERPRINT
    url = "https://webcam.connect.prusa3d.com/c/info"
    headers = {
        "token": api_key,
        "fingerprint": FINGERPRINT,
        "Content-Type": "application/json",
    }

    body = {
        "config": {
            "name": camera_name,
            "trigger_scheme": "TEN_SEC",
        }
    }

    res = requests.put(url, headers=headers, json=body)
    if res.status_code != 200:
        print(f"do_info() Response: {res.status_code} ({res.reason})")
    return res


def main(save=False, save_path=None):
    global api_key, camera_name

    if save_path is None:
        save_path = './'

    saved_data = None

    if save_path is not None:
        try:
            with open(path.join(save_path, 'webcam.json'), 'r') as f:
                print("Loading saved data...")
                saved_data = json.load(f)
        except FileNotFoundError:
            print("No saved data found, please scan the QR code again")
            pass
        except Exception as e:
            print(e)

    # get the list of webcams
    webcam_list = []
    video_devices = os.listdir('/dev/')

    for device in video_devices:
        if device.startswith('video'):
            device_path = '/dev/' + device
            # device_name = None
            # can_open = False
            # resolution = None
            try:
                capture = cv2.VideoCapture(device_path)
                with open(f"/sys/class/video4linux/{device}/name", "r") as f:
                    device_name = f.read().strip()
                can_open = capture.isOpened()
                if can_open:
                    data = {
                        "device_path": device_path,
                        "device_name": device_name,
                    }
                    webcam_list.append(data)
                    capture.release()
            except:
                pass

    # print the list of webcams
    if saved_data is None:
        print("Available webcams:")
        for i, webcam in enumerate(webcam_list):
            print(f"{i}. {webcam['device_name']}")
        print()

    # ask user to select a webcam
    selected_webcam = None
    webcam_path = None

    if saved_data is None:
        while True:
            try:
                selected_webcam = int(input("Select a webcam: "))
                if selected_webcam < 0 or selected_webcam >= len(webcam_list):
                    raise ValueError()
                webcam_path = webcam_list[selected_webcam]['device_path']
                break
            except ValueError:
                print("Invalid input, please try again")
    else:
        try:
            webcam_path = saved_data['camera_path']
            api_key = saved_data['api_key']
            camera_name = saved_data['camera_name']
        except:
            print("Invalid saved data, please delete the saved data and try again")
            sys.exit(1)

    if webcam_path.startswith('/dev/video'):
        # get jpeg data from the selected webcam
        capture = cv2.VideoCapture(webcam_path)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, FORCE_RESOLUTION['width'])
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, FORCE_RESOLUTION['height'])

        # ask for camera name
        if camera_name is None:
            camera_name = input("Enter camera name: ")

        # try to scan the QR code and get the API key#
        if api_key is None:
            qcd = cv2.QRCodeDetector()
            while api_key is None:
                ret, frame = capture.read()
                if not ret:
                    continue
                data, bbox, _ = qcd.detectAndDecode(frame)
                # draw bounding box
                if bbox is not None:
                    cv2.polylines(frame, bbox.astype(int), True, (0, 255, 0), 2)
                    # check if the QR code is a valid API key
                    data_str = str(data)
                    splitted = data_str.split("?token=")
                    if len(splitted) > 1:
                        api_key = splitted[1]
                        print(f"API key found! ({api_key})")
                        break
                cv2.imshow("Scan QR Code", frame)
                if cv2.waitKey(1) == ord('q'):
                    break
            cv2.destroyAllWindows()

        if api_key is None:
            print("API key not found, exiting...")
            sys.exit(1)

        if save and saved_data is None:
            save_data = {
                "api_key": api_key,
                "camera_path": webcam_list[selected_webcam]['device_path'],
                "interval": 10,
                "camera_name": camera_name,
            }

            if save_path is None:
                save_path = './'

            with open(path.join(save_path, 'webcam.json'), 'w') as f:
                json.dump(save_data, f)

        print("Starting webcam...")

        try:
            do_info()
            while True:
                ret, frame = capture.read()
                if not ret:
                    break
                jpeg_data = cv2.imencode('.jpg', frame)[1].tobytes()
                do_snapshot(jpeg_data)
                if saved_data is None or saved_data['interval'] is None:
                    sleep(10)
                else:
                    sleep(saved_data['interval'])
        except KeyboardInterrupt:
            capture.release()
            cv2.destroyAllWindows()
        except Exception as e:
            print(e)
            capture.release()
            cv2.destroyAllWindows()
    elif webcam_path.startswith('http'):
        # mjepg streamer from octoprint (snapshot url)
        do_info()
        while True:
            try:
                res = requests.get(webcam_path)
                if res.status_code != 200:
                    raise Exception(f"Invalid response code: {res.status_code}")
                jpeg_data = res.content
                do_snapshot(jpeg_data)
                if saved_data is None or saved_data['interval'] is None:
                    sleep(10)
                else:
                    sleep(saved_data['interval'])
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(e)
                sleep(10)
    else:
        print("Invalid webcam path, exiting...")
        sys.exit(1)


if __name__ == "__main__":
    save_arg = (len(sys.argv) > 1 and sys.argv[1] == "--save")
    save_path_arg = (sys.argv[2] if len(sys.argv) > 2 else None)
    main(save_arg, save_path_arg)
