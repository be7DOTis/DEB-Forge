# import required generic python libraries
import asyncio
import time
import math
import board

# import required non-generic python libraries. Installed using PIP.
import neopixel 
from viam.robot.client import RobotClient
from viam.rpc.dial import Credentials, DialOptions
from viam.components.camera import Camera
from viam.components.generic import Generic
from viam.services.vision import VisionClient

# Setup Global vars for LED Neopixel strips. NOTE: Refactor to use less globals.
# (WS281x/Neopixels are colloquially called Pixels.)
pixel_pin = board.D18 # Using Pin 18 for the sweet DMA capabilities.
num_pixels = 55 # We have just under a metre across the "desk" so 55 leds of a 60 led/m strip
ORDER = neopixel.GRBW # Neopixel/WS281x style LED strips have every possible variation in its colour order depending on the type. This strip was GRBW
# setting up the NeoPixel objects.
pixels = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=0.5, auto_write=False, pixel_order=ORDER
)
ambient_lum = (5,5,5,5) #0-255 RGB brightness of leds

async def connect():
    opts = RobotClient.Options.with_api_key( 
        api_key='ojhu1ibet65mwspq01anih6upigpng70',
        api_key_id='a67911da-4ee4-4703-8a9b-00646b1baebc'
    )
    return await RobotClient.at_address('deb-forge-main.x5shop4nza.viam.cloud', opts)

# To take the camera and Viam ML detection service and return a list of confident hand detections.
async def detect_hands(camera_name, hand_detector):
    # Await any hand detections using our hand detector vision service from Viam
    potential_hand_detections = await hand_detector.get_detections_from_camera(camera_name)
    confident_hand_detections = [] # Instance list to put in confident detections
    # and go through the potential hand detections and filter out low considence one.
    for d in potential_hand_detections:
        if d.confidence > 0.8:
            print("hand detected : ", d)
            confident_hand_detections.append(d)
    return confident_hand_detections

async def beam_forming(camera_width_px, camera_height_px, detections):
    x_scale_factor = num_pixels / camera_width_px # Map range of cameras vision to the num of LEDs of LED strip
    # Go through all the detections and form a beam for each.
    for d in range(len(detections)):
        # Only dealing with X as the LED matrix is currently only 55x1 as using a single strip
        # some taking off the num of leds and swapping of min max because camera 0 coord and LED 0 coord are inverse each other
        x_max_beam = num_pixels-math.floor(detections[d].x_min * x_scale_factor) 
        x_min_beam = num_pixels-math.floor(detections[d].x_max * x_scale_factor)
        print("Illuminating X: ", x_min_beam, "-", x_max_beam)
        # Go through all of the LEDs in the beam and turn them to Max brightness
        for led in range(x_min_beam, x_max_beam):
            pixels[led] = (255,255,255,255)

# To reset all the LEDs in the strip to the ambient light we set globally
async def refresh_led_pixels():
    for i in range(num_pixels):
        pixels[i] = ambient_lum

async def main():
    machine = await connect() # Connect to Viam server
    camera_name = "camera-1" # Set camera name to what its Componant name is in Viam
    camera = Camera.from_robot(machine, camera_name) # 
    # To get the true dimensions of the stream we are getting from the camera
    # we must take an image and then find the dimensions of the image.
    # NOTE: Probably should be refactored into a function
    calibration_image = await camera.get_image(mime_type="image/jpeg")    
    cam_width_px = calibration_image.width
    cam_height_px = calibration_image.height
    print("Camera stream resolution:", cam_height_px, " x ", cam_width_px)

    hand_detector = VisionClient.from_robot(machine, "hand-detector-service")
    while True:
        hands = await detect_hands("camera-1", hand_detector)
        if hands:
            await refresh_led_pixels()
            await beam_forming(cam_width_px, cam_height_px, hands)
        else:
            pixels.fill(ambient_lum)
        pixels.show()

    await machine.close()

if __name__ == '__main__':
    asyncio.run(main())
 