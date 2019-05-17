# -*- coding: utf-8 -*-

import binascii

from ..tokentype import TokenType
from .state import ParseState

class PictState(ParseState):

	def __init__(self, parser):

		super().__init__(parser)

		self._parser._setStateValue('private', 'inPict', True)
		self._parser._setStateValue('private', 'pictAttributes', {})

		# Initialize image data and ID
		self.__data = ''
		self.__blipUIDBuffer = '' # used for parsing integer ID
		self.__blipUID = False # contains the actual integer ID

	###########################################################################

	# Process a \pict embedded image. For now, this only supports the default
	# hex dump format.
	def __append(self, pictAttributes):

		callback = self._parser._getCallback('onImage')
		if callback:
			callback(self._parser, pictAttributes, binascii.unhexlify(self.__data))

	###########################################################################

	# Look out for when we've finished with the embedded image.
	def _parseCloseBrace(self):

		oldFullStatePrivate = self._parser._fullState['private']
		super()._parseCloseBrace(False)

		# We're finished parsing an image ID (other possible source of ID is
		# the bliptag control word.)
		if 'inBlipUID' in oldFullStatePrivate and oldFullStatePrivate['inBlipUID']:
			self.__blipUID = int(self.__blipUIDBuffer.lstrip('0'), 16)

		# Once we've finished with the pict group, we can stop parsing in this
		# state.
		elif 'inPict' not in self._parser._fullState['private']:
			self.__append(oldFullStatePrivate['pictAttributes'])
			return False
		else:
			return True

	###########################################################################

	def _parseControl(self, word, param):

		# We'll encounter this destination when parsing images. It's a way to
		# uniquely identify the image. In my experience with test data, blipuid
		# and bliptagN are different representations of the same value.
		if '\\*' == self._parser._prevToken[1] and '\\blipuid' == word:

			# We already got the ID in a simpler way, so we can skip over this destination
			if self.__blipUID:
				state = SkipGroupState()
				state.parse()

			# We haven't gotten the ID yet, so go ahead and parse this destination
			else:
				self._parser._setStateValue('private', 'inBlipUID', True)

			return True

		# This is the other (easier) way to uniquely identify an image
		elif '\\bliptag' == word:
			self.__blipUID = int(param, 10)
			return True

		# Various image formatting parameters and metadata
		elif 'pictAttributes' in self._parser._curState['private'] and word in [
			'\\picscalex',    # Horizontal scaling %
			'\\picscaley',    # Vertical scaling %
			'\\piccropl',     # Twips (1/1440 of an inch) to crop off the left
			'\\piccropr',     # Twips (1/1440 of an inch) to crop off the right
			'\\piccropt',     # Twips (1/1440 of an inch) to crop off the top
			'\\piccropb',     # Twips (1/1440 of an inch) to crop off the bottom
			'\\picw',         # Width in pixels (if image is bitmap or from QuickDraw)
			'\\pich',         # Height in pixels (if image is bitmap or from QuickDraw)
			'\\picwgoal',     # Desired width in twips (1/1440 of an inch)
			'\\pichgoal',     # Desired height in twips (1/1440 of an inch)
			'\\picbpp',       # Specifies the bits per pixel in a metafile bitmap.
			                  # The valid range is 1 through 32, with 1, 4, 8, and
			                  # 24 being recognized.

			# These apply only to Windows bitmap images
			'\\wbmbitspixel', # From the 1.9.1 spec: "Number of adjacent color bits
			                  # on each plane needed to define a pixel. Possible
			                  # values are 1 (monochrome), 4 (16 colors), 8
			                  # (256 colors) and 24 (RGB). The default value is 1."
			'\\wbmplanes',    # From the 1.9.1 spec: "Number of bitmap color planes
			                  # (must equal 1)."
			'\\wbmwidthbytes' # From the 1.9.1 spec: "Specifies the number of bytes
			                  # in each raster line. This value must be an even
			                  # number because the Windows Graphics Device Interface
			                  # (GDI) assumes that the bit values of a bitmap form
			                  # an array of integer (two-byte) values. In other
			                  # words, \wbmwidthbytes multiplied by 8 must be the
			                  # next multiple of 16 greater than or equal to the
			                  # \picw (bitmap width in pixels) value.
		]:
			pictAttributes = self._parser._curState['private']['pictAttributes']
			pictAttributes[word] = int(param, 10)
			self._parser._setStateValue('private', 'pictAttributes', pictAttributes)
			return True

		# JPG
		elif 'pictAttributes' in self._parser._curState['private'] and '\\jpegblip' == word:
			pictAttributes = self._parser._curState['private']['pictAttributes']
			pictAttributes['source'] = 'jpeg'
			self._parser._setStateValue('private', 'pictAttributes', pictAttributes)
			return True

		# PNG
		elif 'pictAttributes' in self._parser._curState['private'] and '\\pngblip' == word:
			pictAttributes = self._parser._curState['private']['pictAttributes']
			pictAttributes['source'] = 'png'
			self._parser._setStateValue('private', 'pictAttributes', pictAttributes)
			return True

		# EMF (Enhanced metafile)
		elif 'pictAttributes' in self._parser._curState['private'] and '\\emfblip' == word:
			pictAttributes = self._parser._curState['private']['pictAttributes']
			pictAttributes['source'] = 'emf'
			self._parser._setStateValue('private', 'pictAttributes', pictAttributes)
			return True

		# OS/2 metafile
		elif 'pictAttributes' in self._parser._curState['private'] and '\\pmmetafile' == word:
			pictAttributes = self._parser._curState['private']['pictAttributes']
			pictAttributes['source'] = 'os2meta'
			pictAttributes['metafileType'] = param
			self._parser._setStateValue('private', 'pictAttributes', pictAttributes)
			return True

		# Windows metafile
		elif 'pictAttributes' in self._parser._curState['private'] and '\\wmetafile' == word:
			pictAttributes = self._parser._curState['private']['pictAttributes']
			pictAttributes['source'] = 'winmeta'
			pictAttributes['metafileMappingMode'] = param
			self._parser._setStateValue('private', 'pictAttributes', pictAttributes)
			return True

		# Windows device-independent bitmap
		elif 'pictAttributes' in self._parser._curState['private'] and '\\dibitmap' == word:
			pictAttributes = self._parser._curState['private']['pictAttributes']
			pictAttributes['source'] = 'wdibmp'
			pictAttributes['bitmapType'] = param
			self._parser._setStateValue('private', 'pictAttributes', pictAttributes)
			return True

		# Windows device-dependent bitmap
		elif 'pictAttributes' in self._parser._curState['private'] and '\\wbitmap' == word:
			pictAttributes = self._parser._curState['private']['pictAttributes']
			pictAttributes['source'] = 'wddbmp'
			pictAttributes['bitmapType'] = param
			self._parser._setStateValue('private', 'pictAttributes', pictAttributes)
			return True

		else:
			return super()._parseControl(word, param)

	###########################################################################

	# This is ordinarily an abstract function and I'm required to implement it,
	# but it's not actually used because I've overriden self._parse to solve a
	# significant performance issue.
	def _parseCharacter(self, token):

		return True

	###########################################################################

	# I had to override this because repeated calls to self._parseCharacter
	# result in terrible performance for even small images. This isn't a
	# beautiful solution, but it works *really* well. Prepare your nose for a
	# code smell (this is mostly a cut-and-paste from the ParseState class's
	# method with the call to self._parseCharacter removed.)
	def parse(self):

		if self._parser._content:

			self._parser._curToken = self._getNextToken()

			while TokenType.EOF != self._parser._curToken[0]:
				if TokenType.OPEN_BRACE == self._parser._curToken[0]:
					if not self._parseOpenBrace():
						return

				# Restore the previous state.
				elif TokenType.CLOSE_BRACE == self._parser._curToken[0]:
					if not self._parseCloseBrace():
						return

				# We're executing a control word. Execute this before
				# appending tokens to any special destination or group that
				# might contain control words.
				elif TokenType.CONTROL_WORDORSYM == self._parser._curToken[0]:
					tokenParts = self._splitControlWord(self._parser._curToken)
					if not self._parseControl(tokenParts[0], tokenParts[1]):
						return

				### Begin code that diverges from ParseState.parse() ###

				elif 'inBlipUID' in self._parser._curState['private'] and self._parser._curState['private']['inBlipUID']:
					self.__blipUIDBuffer += self._parser._curToken[1]

				elif not self._parser._curToken[1].isspace():
					self.__data += self._parser._curToken[1]

				###  End code that diverges from ParseState.parse()  ###

				self._parser._prevToken = self._parser._curToken
				self._parser._curToken = self._getNextToken()

