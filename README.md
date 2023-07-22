# python-prusa-webcam

## Description
This python script allows you to turn any Webcam plugged into your device to turn into a Webcam for Prusa Connect!

## Prerequisites
- opencv-python (pip install opencv-python)
- requests (pip install requests)

Currently, there are hardcoded paths for `video4linux`. If you want to add support for other OSes, please create a pull request.

## Usage
1. Clone this repository
2. Run `python3 main.py`
3. Enter the index from the camera list
4. Scan the prusa QR Code with the camera
5. Enjoy!

**or**

1. Clone this repository
2. Run `python3 main.py --save`
3. Enter the index from the camera list
4. Scan the prusa QR Code with the camera
5. The program will save the entered index and the api token in plaintext in `./webcam.json` (This can be changed by passing `--save <path>` to the script)
6. Enjoy!

If scanning is no option, you can just manually create a `webcam.json` file with the following contents:
```json
{
  "api_key": "<api-key>",
  "camera_path": "/dev/video<index>"
}
```