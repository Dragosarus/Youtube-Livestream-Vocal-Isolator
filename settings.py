# Displays how to supply command line arguments
CMD_USAGE = "Usage: python main.py [LIVESTREAM URL] [QUALITY]"

# Path to folder where temporary video files will be stored
# Consider avoiding putting this on an SSD (opt instead for e.g a RAM disk)
# to avoid wasting write cycles
# Example: "E:/temp"
TEMP_FOLDER = ""

# Ensure everything inside the folder only belongs to this program
TEMP_FOLDER += "/YTLivestreamVocalIsolator"

# Where spleeter should put its output
SPLEETER_OUT = TEMP_FOLDER + "/spleeter_out"

# Default format code (lowest, should always be available)
DEFAULT_QUALITY = "91"

# Disable to always use DEFAULT_QUALITY (or the cmd argument)
ASK_FOR_QUALITY = True

# Used to restrict size of file/folder names (i.e. "outputXX.wav")
# Making this too small might not 
BUFFER_LIMIT = 10

# Stop subprocess windows from popping up (when not run via IDLE)
CREATE_NO_WINDOW = 0x08000000

# Indicates which segments should be processed from the ones given
#  in the .m3u8 url
# {"segment-length":n_most_recent_segments},
#   where n_most_recent_segments is an integer > 0
# In other words, indicates the minimum delay -- n_most_recent_segments = 1
# ensures the most recent segment is played at the expense of making the
# playback choppier
#
# It appears there are (mainly) 2 stream setups:
# - segment_length = 1s, 3 segments listed
# - segment_length = 2s, 5+ segments listed
# In setup 1, this script will always be behind.
# In setup 2, this script might be ahead of YT's player
#   if n_most_segments is small enough (e.g. 2)
SEG_START = {
	1: 2, # ~2s behind
	2: 2, # ~4s behind
}

# (GPU) Limit the amount of VRAM TensorFlow is allowed to allocate
# By default, spleeter puts this at 0.7 (70%!)
TF_MEMORY_FRACTION = "0.1" # % of available VRAM
