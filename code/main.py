import ctypes.util
import platform
import sys

# On NixOS/Nix, ctypes.util.find_library can fail under minimal environments
# (like nix run) due to missing compiler tools or path caching.
# We patch it to directly return the library filenames for sounddevice and
# soundfile, allowing them to be loaded from LD_LIBRARY_PATH.
if platform.system() == 'Linux':
    _original_find_library = ctypes.util.find_library
    def _patched_find_library(name):
        if name == 'portaudio':
            return 'libportaudio.so'
        if name == 'sndfile':
            return 'libsndfile.so'
        return _original_find_library(name)
    ctypes.util.find_library = _patched_find_library

import gui.Gui as Gui

if __name__ == "__main__":
    Gui.main()

