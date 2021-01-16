from inspect import getsource # Edit spleeter.separator to consume less VRAM
from math import ceil
from os import path, remove, makedirs
from queue import Queue
from shutil import rmtree # remove temporary files
from subprocess import CalledProcessError, check_output
from sys import stderr, argv, exit as sysexit
from threading import Thread
from time import sleep, perf_counter

from m3u8 import load as m3u8_load
from pydub import AudioSegment
from pydub.playback import play
import spleeter.separator

from settings import * # Local module

global exit_flag 
exit_flag = False # Tell threads to shut down after a KeyboardInterrupt

# Fetch livestream segments as determined by the .m3u8 url from youtube-dl
def ffmpeg_thread(stream_url, spleeter_queue):
    global exit_flag
    counter = 0
    current_segs = [] # seg.ts urls
    segment_archive = [] # Ensure the same segment is not read twice
    segment_length = "1" # Length of each segment, in seconds
    archive_size = BUFFER_LIMIT

    while not exit_flag:
        # load segs
        if not current_segs:
            playlist = m3u8_load(stream_url) # Get new segments
            segment_length = "".join(str(playlist.segments).split("\n#EXTINF:")[1]).split(",")[0] # \n#EXTINF:X,\n
            segment_length = float(segment_length)

            # Fetch the n most recent segments (according to SEG_START):
            seg_index = int(ceil(segment_length))
            if seg_index not in SEG_START.keys():
                seg_index = 0
            current_segs = [t.split("\n")[1] for t in str(playlist.segments).split("#EXTINF")[1:]]
        try:
            # ensure segments are not repeated
            if current_segs[0] in segment_archive:
                current_segs.pop(0)
                continue
        except IndexError:
            print("IndexError")
            print(stream_url)
            sysexit()

        segment_archive.append(current_segs.pop(0))
        if len(segment_archive) > archive_size:
            segment_archive.pop(0)

        file_name = "output" + str(counter) + ".wav"
        output_name = TEMP_FOLDER + "/" + "output" + str(counter) + ".wav"

        try:
            cmd = ["ffmpeg", "-i", segment_archive[-1], output_name, "-y"]
            out = check_output(cmd, creationflags=CREATE_NO_WINDOW)
        except CalledProcessError as e: # some error occurred; skip segment
            print("FFMPEG: CalledProcessError!")
            print(e.output)
            print(out)
            s = AudioSegment.silent(segment_length)
            s.export(output_name, 'wav')

        spleeter_queue.put((output_name, file_name, segment_length)) # Signal that output is available
        counter = (counter + 1) % BUFFER_LIMIT
        sleep(segment_length / 3) # Avoid polling the url too often
    
    print("Closing ffmpeg_thread...")
            
# Isolate audio
def spleeter_thread(separator, ffmpeg_queue, arbiter_queue, delete_queue):
    # This thread does not exit properly on KeyboardInterrupt,
    # so exit_flag is useless here (most of the time).
    counter = 0
    
    while True:
        try:
            # wait until output is available
            segment_path, _file_name, segment_length = ffmpeg_queue.get(timeout=1) 
        except Exception as _empty_exception:
            continue

        #print("SPLEETER: separating " + segment_path)
        separator.separate_to_file(segment_path, SPLEETER_OUT)
        delete_queue.put(segment_path) # Remove output because we do not need it anymore
        #print("SPLEETER: separated " + segment_path)
        out_dir = SPLEETER_OUT + "/output" + str(counter)
        sound = AudioSegment.from_wav(out_dir + "/vocals.wav")
        arbiter_queue.put((sound, out_dir, segment_length))
        counter = (counter + 1) % BUFFER_LIMIT
    #print("Closing spleeter_thread...") # when main thread exits
      

# Hand out audio to be played to one of two playback threads
# Two threads are used to minimize downtime (the pause between two segments)
# i.e. instead of:
# t:  {---seg1---}  {---seg2---}  {---seg3---} ...
# the hope is to get this:
# t1: {---seg1---}          {---seg3---} ...
# t2:            {---seg2---}          {-...
def arbiter_thread(spleeter_queue, p1_queue, p2_queue):
    global exit_flag
    init = True
    counter = 0
    queues = [p1_queue, p2_queue]
    current_queue = 0

    ts2 = 0 # Initial value does not matter
    while not exit_flag:
        ts1 = ts2 # Measure time spent waiting for next segment
        try:
            # Wait until output is available
            sound, out_dir, segment_length = spleeter_queue.get(timeout=1)
        except Exception as _empty_exception:
            continue
        ts2 = perf_counter()
        if not init: # Try to start playing segment when the previous ends
            sleep(max(segment_length-0.05-(ts2-ts1), 0))
        else: # No point in waiting before playing the first segment
            init = False
        print("PLAYBACK: playing", counter)
        queues[current_queue].put((sound,out_dir))
        counter = (counter + 1) % BUFFER_LIMIT
        current_queue ^= 1
        ts2 = perf_counter()
    print("Closing arbiter_thread...") 

# Play isolated vocals
def playback_thread(playback_queue, delete_queue):
    global exit_flag
    while not exit_flag: 
        try:
            sound, out_dir = playback_queue.get(timeout=1)
        except Exception as _empty_exception:
            continue
        play(sound)
        delete_queue.put(out_dir)
    print("Closing one of the playback_threads...")

# Delete temporary files after they have served their purpose
def delete_thread(delete_queue):
    global exit_flag
    exit_wait = True # Ensure all temp files are removed
    while not exit_flag or exit_wait:
        try:
            del_path = delete_queue.get(timeout=3)
        except Exception: # Empty
            exit_wait = not exit_flag
            continue

        try:
            if path.exists(del_path):
                if path.isdir(del_path):
                    rmtree(del_path)
                else:
                    remove(del_path)
        except Exception as e:
            print("DELETE: failed!", del_path, str(e))
            sleep(0.1)
    print("Closing delete_thread...")

if __name__ == "__main__":
    # Tell user to set a location for TEMP_FOLDER if they have not already done so
    if not TEMP_FOLDER:
        print("Please set a location for temporary files by assigning a folder path to TEMP_FOLDER in settings.py, then try again.", file=stderr)
        print("NOTE: It is recommended that this folder is on a RAM disk (will shorten an SSD's lifespan due to write cycles).", file=stderr)
        print("You can create a RAM disk via e.g. https://sourceforge.net/projects/imdisk-toolkit/", file=stderr)
        print("The required size depends on the quality of the livestream, but 64 MB should be enough for this program.", file=stderr)
        input("Press enter to exit.")
        sysexit()

    url = argv[1].strip() if len(argv) >= 2 else ""
    while "youtube.com/watch?v=" not in url:
        if len(argv) >= 2:
            print(CMD_USAGE)
        url = input("Paste livestream url: \n>> ")

    # Display available quality formats if this has not already been supplied via the command line
    if len(argv) >= 3:
        quality = argv[2].strip()
    elif ASK_FOR_QUALITY:
        t = check_output(["youtube-dl", "-F", url], creationflags=CREATE_NO_WINDOW)
        print(t.decode().split("[info] ")[-1])
        quality = input("Choose format code (default: {}) \n>> ".format(DEFAULT_QUALITY))
        if not quality:
            quality = DEFAULT_QUALITY
    else:
        quality = DEFAULT_QUALITY
            


    print("youtube-dl: retrieving m3u8 url...")
    try:
        stream_url = check_output(["youtube-dl", "-f", quality, "-g", url], creationflags=CREATE_NO_WINDOW).decode()[:-1]
    except Exception as e:
        print("Error:", e, file=stderr)
        print("Ensure you have chosen a valid format code and try again.", file=stderr)
        input("Press enter to exit.")
        sysexit()

    if not stream_url.endswith("/index.m3u8"):
        print("Error: not an ongoing livestream.", file=stderr)
        input("Press enter to exit.")
        sysexit()
    
    print("youtube-dl: finished!")

    if not path.exists(TEMP_FOLDER):
        makedirs(TEMP_FOLDER, exist_ok=True)
    if not path.exists(SPLEETER_OUT):   
        makedirs(SPLEETER_OUT, exist_ok=True)

    # Inter-thread communication
    spleeter_q = Queue() # ffmpeg -> spleeter
    arbiter_q = Queue() # spleeter -> arbiter
    playback1_q = Queue() # arbiter -> playback1
    playback2_q = Queue() # arbiter -> playback2
    delete_q = Queue() # spleeter, playbackN -> delete

    # Modify spleeter.separator to consume less VRAM
    # https://stackoverflow.com/questions/41858147/how-to-modify-imported-source-code-on-the-fly/41863728
    source = getsource(spleeter.separator)
    mem_fraction = source.split("gpu_memory_fraction = ")[1]
    mem_fraction = mem_fraction[:mem_fraction.find("\n")]
    new_source = source.replace("gpu_memory_fraction = " + mem_fraction, 
                                "gpu_memory_fraction = " + TF_MEMORY_FRACTION)
    exec(new_source, spleeter.separator.__dict__)


    warmup_path = TEMP_FOLDER + "/warmup.mp3"
    
    if not path.exists(warmup_path):
        print("Creating warm-up file...")
        s = AudioSegment.silent()
        s.export(warmup_path)
        print("Warm-up file created!")

    print("Warming up spleeter")
    separator = spleeter.separator.Separator("spleeter:2stems")
    separator.separate_to_file(warmup_path, SPLEETER_OUT)
    delete_q.put(SPLEETER_OUT + "/warmup")
    delete_q.put(warmup_path)
    print("Warm-up completed!")
    
    # Start threads
    ts = [
        Thread(target=ffmpeg_thread,   args=[stream_url, spleeter_q]),
        Thread(target=spleeter_thread, args=[separator, spleeter_q, arbiter_q, delete_q]),
        Thread(target=arbiter_thread,  args=[arbiter_q, playback1_q, playback2_q]),
        Thread(target=playback_thread, args=[playback1_q, delete_q]), # Playback #1
        Thread(target=playback_thread, args=[playback2_q, delete_q]), # Playback #2
        Thread(target=delete_thread,   args=[delete_q])
    ]

    for t in ts:
        # Spleeter does not react nicely to KeyboardInterrupts
        if t == ts[1]: 
            t.daemon = True
        t.start()

    try:
        while True:
            sleep(100)
    except (KeyboardInterrupt, SystemExit):
        delete_q.put(TEMP_FOLDER) # Ensure temporary files are deleted
        # Tell non-daemon threads to exit (spleeter wouldn't listen anyway)
        exit_flag = True 
        print("Closing main thread (and spleeter_thread)...")
