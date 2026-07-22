import ctypes.util
import platform
import sys
import argparse

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

def run_headless(input_path: str, output_path: str, points_str_list: list[str] | None):
    import soundfile as sf
    from audio import SpectralTransformer, EqCurve

    points = []
    if points_str_list:
        for p_str in points_str_list:
            try:
                x_str, y_str = p_str.split(',')
                points.append((float(x_str), float(y_str)))
            except ValueError:
                print(f"Error: Invalid point format '{p_str}'. Must be 'x,y'.", file=sys.stderr)
                sys.exit(1)
    else:
        # Default points
        points = [(0.3, 0.5), (0.3, 0.2)]

    eq_curve = EqCurve(points)

    try:
        transformer = SpectralTransformer(
            windowLength=512,
            hopLength=256,
            windowType='hann'
        )

        spectrum = transformer.analyze(input_path)
        spectrum = transformer.apply_equalizer(spectrum, eq_curve)
        transformer.synthesize(spectrum, output_path=output_path)

        print(f"Successfully applied EQ and saved output to '{output_path}'")
    except Exception as e:
        print(f"Error processing audio file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Equalizer - Headless or GUI Mode")
    parser.add_argument("--headless", "-hl", action="store_true", help="Run in headless mode without GUI")
    parser.add_argument("--input", "-i", type=str, help="Input audio file path (required in headless mode)")
    parser.add_argument("--output", "-o", type=str, help="Output audio file path (required in headless mode)")
    parser.add_argument("--points", "-p", type=str, nargs="+",
                        help="EQ control points in 'x,y' format (e.g. -p 0.3,0.5 0.3,0.2)")

    args = parser.parse_args()

    if args.headless:
        if not args.input or not args.output:
            parser.error("Headless mode requires both --input (-i) and --output (-o) to be specified.")
        run_headless(args.input, args.output, args.points)
    else:
        import gui.Gui as Gui
        Gui.main()
