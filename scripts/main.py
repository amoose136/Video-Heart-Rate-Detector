""" 
====================================================
        Real Time Heart Rate Detector 
====================================================

The Haar cascade dataset used is the Extended Yale Database B Cropped

  http://vision.ucsd.edu/~leekc/ExtYaleDatabase/ExtYaleB.html


Summary:
    This utility overlays the heart rate extracted from input video.
    Order of operations:
        -> Run real time facial tracking and recognition using Haar cascades
        and SVM 
        -> Integrate cropped faces over red channel to produce 1d scalar 
        -> FFT 1d red brightness scalar for sets of 30 frames
        -> Find peak of FFT within range of expected heart rates

To Run:
    * To run it without options
        python main.py

    * Or running with options (By default, scale_multiplier = 4):

        python main.py [scale_multiplier=<full screensize divided by scale_multiplier>]

    * Say you want to run with 1/2 of the full sreen size, specify that scale_multiplier = 4:

        python main.py 4


Usage: 
        press 'q' or 'ESC' to quit the application


        
Adapted from code by Chenxing Ouyang <c2ouyang@ucsd.edu>
Chenxing's code does the face detection python implementation and provided the Haar cascade database

Written by Amos Manneschmidt

"""

import cv2
import os
import numpy as np
from scipy import ndimage
from time import time
import matplotlib.pyplot as plt
import utils as ut
import svm
import sys
import logging
import warnings
from pdb import set_trace as br

print(__doc__)

###############################################################################
# Building SVC from database

FACE_DIM = (50,50) # h = 50, w = 50

# Load training data from face_profiles/
face_profile_data, face_profile_name_index, face_profile_names  = ut.load_training_data("../face_profiles/")

print "\n", face_profile_name_index.shape[0], " samples from ", len(face_profile_names), " people are loaded"

# Build the classifier
clf, pca = svm.build_SVC(face_profile_data, face_profile_name_index, FACE_DIM)


###############################################################################
# Facial Recognition In Live Tracking


DISPLAY_FACE_DIM = (500, 500) # the displayed video stream screen dimention 
SKIP_FRAME = 2      # the fixed skip frame
frame_skip_rate = 0 # skip SKIP_FRAME frames every other frame
SCALE_FACTOR = 2 # used to resize the captured frame for face detection for faster processing speed
face_cascade = cv2.CascadeClassifier("../classifier/haarcascade_frontalface_default.xml") #create a cascade classifier
sideFace_cascade = cv2.CascadeClassifier('../classifier/haarcascade_profileface.xml')

if len(sys.argv) == 2:
    SCALE_FACTOR = float(sys.argv[1])
elif len(sys.argv) >2:
    logging.error("main.py ")
# dictionary mapping used to keep track of head rotation maps
rotation_maps = {
    "left": np.array([-30, 0, 30]),
    "right": np.array([30, 0, -30]),
    "middle": np.array([0, -30, 30]),
}

def get_rotation_map(rotation):
    """ Takes in an angle rotation, and returns an optimized rotation map """
    if rotation > 0: return rotation_maps.get("right", None)
    if rotation < 0: return rotation_maps.get("left", None)
    if rotation == 0: return rotation_maps.get("middle", None)

current_rotation_map = get_rotation_map(0) 


webcam = cv2.VideoCapture(0)

ret, frame = webcam.read() # get first frame
frame_scale = (frame.shape[1]/SCALE_FACTOR,frame.shape[0]/SCALE_FACTOR)  # (y, x)

cropped_face = []
num_of_face_saved = 0


while ret:
    key = cv2.waitKey(1)
    # exit on 'q' 'esc' 'Q'
    if key in [27, ord('Q'), ord('q')]: 
        break
    # resize the captured frame for face detection to increase processing speed
    resized_frame = cv2.resize(frame, frame_scale)

    processed_frame = resized_frame
    # Skip a frame if the no face was found last frame

    if frame_skip_rate == 0:
        faceFound = False
        for rotation in current_rotation_map:

            rotated_frame = ndimage.rotate(resized_frame, rotation)

            gray = cv2.cvtColor(rotated_frame, cv2.COLOR_BGR2GRAY)

            # return tuple is empty, ndarray if detected face
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.3,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            ) 

            # If frontal face detector failed, use profileface detector
            faces = faces if len(faces) else sideFace_cascade.detectMultiScale(                
                gray,
                scaleFactor=1.3,
                minNeighbors=5,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE
            )

            # for f in faces:
            #     x, y, w, h = [ v*SCALE_FACTOR for v in f ] # scale the bounding box back to original frame size
            #     cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0))
            #     cv2.putText(frame, "DumbAss", (x,y), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0))

            if len(faces):
                for f in faces:
                    # Crop out the face
                    x, y, w, h = [ v for v in f ] # scale the bounding box back to original frame size
                    cropped_face = rotated_frame[y: y + h, x: x + w]   # img[y: y + h, x: x + w]
                    cropped_face = cv2.resize(cropped_face, DISPLAY_FACE_DIM, interpolation = cv2.INTER_AREA)

                    # Name Prediction
                    face_to_predict = cv2.resize(cropped_face, FACE_DIM, interpolation = cv2.INTER_AREA)
                    face_to_predict = cv2.cvtColor(face_to_predict, cv2.COLOR_BGR2GRAY)

                    # Display frame
                    cv2.rectangle(rotated_frame, (x,y), (x+w,y+h), (0,255,0))

                # rotate the frame back and trim the black paddings
                processed_frame = ut.trim(ut.rotate_image(rotated_frame, rotation * (-1)), frame_scale)

                # reset the optmized rotation map
                current_rotation_map = get_rotation_map(rotation)

                faceFound = True


                break

        if faceFound: 
            frame_skip_rate = 0
            # print "Face Found"
        else:
            frame_skip_rate = SKIP_FRAME
            # print "Face Not Found"

    else:
        frame_skip_rate -= 1
        # print "Face Not Found"


    # print "Frame dimension: ", processed_frame.shape
  
    cv2.putText(processed_frame, "Press ESC or 'q' to quit.", (5, 15),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255))
    cv2.imshow("Real Time Facial Recognition", processed_frame)


    # br()
    if len(cropped_face):
        cv2.imshow("Cropped Face", cv2.cvtColor(cropped_face, cv2.COLOR_BGR2GRAY))
        # face_to_predict = cv2.resize(cropped_face, FACE_DIM, interpolation = cv2.INTER_AREA)
        # face_to_predict = cv2.cvtColor(face_to_predict, cv2.COLOR_BGR2GRAY)
        # name_to_display = svm.predict(clf, pca, face_to_predict, face_profile_names)
    # get next frame
    ret, frame = webcam.read()


webcam.release()
cv2.destroyAllWindows()