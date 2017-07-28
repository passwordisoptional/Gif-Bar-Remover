#!/bin/python

from skimage import io
from skimage.filters.rank import entropy as getLocalEntropy
from skimage.morphology import disk
from scipy.signal import savgol_filter
import numpy as np
import sys
import matplotlib.pyplot as plt
from subprocess import call
from subprocess import check_output
import warnings
import os
import magic
# import random
# import pdb
# import cv2

# entropy is eratic on the edges, so ignore N edge pixels
sideCutoff = 20 

# crop final image by an additional N pixels, to ensure bars are entirely removed
finalCutoff = 7

debug = False

class Image():
	data = None
	name = None
	columnEntropy = None
	edges = None

	def show(self):
		cv2.imshow(self.name, self.data)
		cv2.waitKey(0)
		cv2.destroyWindow(self.name)

	def height(self):
		return self.data.shape[0]

	def width(self):
		return self.data.shape[1]

def parseCommandLine():
	if len(sys.argv) < 2:
		raise Exception('Input and output file names must be passed in')

	debug = sys.argv[1] == '--debug'

	origImageName = sys.argv[-2]
	newImageName = sys.argv[-1]

	return origImageName, newImageName, debug

def getFileType(imageName):
	mimeType = magic.from_file(imageName, mime=True)

	if debug:
		print('mime type:', mimeType)

	return mimeType[mimeType.index('/')+1:]

def getImage(origImageName):
	image = Image()
	image.name = '/tmp/temp.jpg'

	# In case we're modifying a gif or video, get first frame
	call(['convert', origImageName + '[0]', image.name])

	# Read image
	image.data = io.imread(image.name, True)
	# image.show()

	if debug:
		print('Processing image', origImageName)
		print('Height:', image.height())
		print('Width:', image.width())

	return image

def getEntropy(image):
	# Calculate local entropy at every pixel
	with warnings.catch_warnings():
		warnings.simplefilter("ignore")
		entropy = getLocalEntropy(image.data, disk(10))

	# Sum entropy by columns
	return entropy.sum(axis=0)[sideCutoff:image.width()-sideCutoff]
	# image.columnEntropy[340] = 1500

def getEdges(image):
	# Smooth entropy curve for more consistent results
	savgolEntropy = savgol_filter(image.columnEntropy, 51, 4)

	# Determine locations of greatest entropy change
	slopes = np.diff(savgolEntropy).tolist()
	maxSlopeIndex = slopes.index(max(slopes)) + sideCutoff + finalCutoff
	minSlopeIndex = slopes.index(min(slopes)) + sideCutoff - finalCutoff
	edges = (maxSlopeIndex, minSlopeIndex)

	if debug:
		xs = range(sideCutoff, sideCutoff + len(image.columnEntropy))
		# with warnings.catch_warnings():
		# 	warnings.simplefilter("ignore")
		# 	polyFuncAr = np.poly1d(np.polyfit(range(len(entropySums)), entropySums, 50))(ls)
		# print('entropySums:', getSlopeIndicies(entropySums))
		# print('polyFunc:', getSlopeIndicies(polyFuncAr))
		print('Edges are', edges)
		plt.plot(xs, image.columnEntropy, '-', xs, savgolEntropy, '--')
		plt.show()

	return edges

def cropImage(image, origImageName, newImageName):

	def makeGeometry(height, width, x1, x2):
		return str(abs(x1 - x2)) + 'x' + str(height) + '+' + str(min(x1, x2)) + '+0'

	if debug:
		print('Converting... ', end='', flush=True)

	# For videos, convert needs like 8G of ram and 10G of temp storage space
	os.environ['MAGICK_TMPDIR'] = os.environ['HOME'] + '/tmp'
	convertCall = ['convert', origImageName, '-crop', makeGeometry(image.height(), image.width(), *image.edges), '+repage', newImageName]
	# print(' '.join(convertCall))
	call(convertCall)

	if debug:
		print('done.')

def restoreSound():
	# When cropping a video, convert strips audio. Use ffmpeg to add it back.
	tempVideoName = '/tmp/temp.mp4'
	if getImageFormat(origImageName) == b'PAM':
		ffmpegCall = ['ffmpeg', '-i', origImageName, '-i', newImageName, '-map', '0:a', '-map', '1:v', '-c', 'copy', tempVideoName]
		# print(' '.join(ffmpegCall))
		devnull = open(os.devnull, 'w')
		call(ffmpegCall, stdout=devnull)
		devnull.close()
		os.rename(tempVideoName, newImageName)

def removeBars(origImageName, newImageName, debugLocal=False):
	global debug
	debug = debugLocal

	image = getImage(origImageName)
	image.columnEntropy = getEntropy(image)
	image.edges = getEdges(image)
	cropImage(image, origImageName, newImageName)
	# restoreSound()

def main():
	removeBars(*parseCommandLine())

if __name__ == '__main__':
	main()