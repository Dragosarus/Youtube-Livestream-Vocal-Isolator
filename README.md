# Youtube Livestream Vocal Isolator
Livestream playback with on the fly vocal isolation

## About
Allows you to listen to a stream (more specifically, the vocals from it) in the background while doing something else. The output will generally be delayed by a few seconds compared to the Youtube player (but might depending on stream settings be slightly ahead).

Notes:
- Non-vocals likely won't be affected (significantly) <ins>when mixed with vocals</ins>. Non-vocals on their own mostly disappear, though.
- When run, the program takes up almost 3800 MB of RAM and, if the GPU can be used, 10% of its VRAM (configurable).

Demo (with GPU support): To be added

## Usage
0. Extract `main.py` and `settings.py` to a folder of your choice. Upon running `main.py` for the first time, the folders `__pycache__` and `pretrained_models` will be created in the same directory (totalling ~76 MB).

1. In `settings.py`, give `TEMP_FOLDER` a path to a folder where temporary files will be stored (e.g. `"E:\temp"`). The path does not need to exist before executing the program -- folders will be created if needed.
- You might not want to use an SSD for this (as they have a limited number of write cycles). Consider using a RAM disk (using e.g. [ImDisk](https://www.ltr-data.se/opencode.html/)) -- a size of 32 MB should be enough with the default settings.

2. Double click `main.py`, or via the command line:

&emsp;&emsp;`python main.py [URL] [FORMAT CODE]`

&emsp;where
- `URL` points to an ongoing livestream (e.g. https://www.youtube.com/watch?v=21X5lGlDOfg)
- `FORMAT CODE` indicates the quality (see available format codes by running the script or via `youtube-dl -F {URL}`).

3. Press Ctrl+C to close the program (or otherwise, but you will have to remove leftover temporary files yourself). You might need to do this twice.

## Dependencies
- [Python 3.7+](https://www.python.org/)
- [ffmpeg](http://www.ffmpeg.org/)
- [youtube-dl](https://github.com/ytdl-org/youtube-dl)

Install via e.g. `pip install {package}`:
- [m3u8](https://github.com/globocom/m3u8)
- [pydub](https://github.com/jiaaro/pydub)
- [spleeter](https://github.com/deezer/spleeter)

Optional:
[GPU support](https://www.tensorflow.org/install/gpu)

## Settings
Notable settings in `settings.py`:
- `TEMP_FOLDER` -- where temporary files should be stored.
- `DEFAULT_QUALITY` -- default format code: `"91"`
- `ASK_FOR_QUALITY` -- whether to prompt for a format code if not given one as a cmd argument (uses `DEFAULT_QUALITY` if disabled)
- `SEG_START` -- indicates minimum delay depending on the stream setup (segment length).
- `TF_MEMORY_FRACTION` -- (GPU) limits how much VRAM TensorFlow (used by Spleeter) is allowed to allocate
