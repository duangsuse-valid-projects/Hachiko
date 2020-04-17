# Hachiko

Simple tool for creating pitch timeline, this program divides midi creation into `pitches` and `timeline` part.

When creating timeline, press <kbd>A</kbd> to give position/duration information, and use <kbd>S</kbd> to split different notes directly when holding <kbd>A</kbd>

```python
# Twinkle Little Star
[45, 45, 52, 52, 54, 54, 52, 50, 50, 49, 49, 47, 47, 45, 52, 52, 50, 50, 49, 49, 47, 52, 52, 50, 50, 49, 49, 47, 45, 45, 52, 52, 54, 54, 52, 50, 50, 49, 49, 47, 47, 45]
```

> Tip: press <kbd>K</kbd> in pitch window, and input code in console (__it's recommended to launch this application in console__)

## Installing

There's no need for system-wide installation, just use the script `hachi.py`

System library [FluidSynth](https://github.com/FluidSynth/fluidsynth) is required to run this application.

```bash
pip install --user -r requirements.txt
python3 hachi.py
```

## UI Control / Basic Routine

Hachiko is self documented, so just use the program.

```bash
python3 hachi.py -h
```

> NOTE: For the first time using GUI, you can spend more time learning hot keys

Once `puzi.srt` is generated, you can use `python3 srt2mid.py puzi.srt` to transform it into MIDI file.
