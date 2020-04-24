# Hachiko

<div align="center">
<img alt="Hachiko" src="Hachiko.png"></img>
</div>

Simple tool for creating pitch timeline, this program divides midi creation into `pitches` and `timeline` part.

When creating timeline, press <kbd>A</kbd> to give position/duration information, and use <kbd>S</kbd> to split different notes directly when holding <kbd>A</kbd>

```python
# Twinkle Little Star
[45, 45, 52, 52, 54, 54, 52, 50, 50, 49, 49, 47, 47, 45, 52, 52, 50, 50, 49, 49, 47, 52, 52, 50, 50, 49, 49, 47, 45, 45, 52, 52, 54, 54, 52, 50, 50, 49, 49, 47, 47, 45]
```

> Tip: press <kbd>K</kbd> in pitch window, and input code in console (__it's recommended to launch this application in console__)

The name of the project is *Hachiko*, inspired by the golden yellow Akita dog - ハチ公, which is in homophonic with "扒公" (means melody extraction "耳 Copy" or "扒谱").

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

Once `puzi.srt` is generated, you can use `python srt2mid.py puzi.srt` to transform it into MIDI file

Btw, you can use pitches from extrenal tool (like [Synthesizer V](https://synthesizerv.com) editor) extracted by `python midnotes.py puzi.mid` instead of built-in approach

Btw, there's also an option to use [MELODIA Algorithm](https://github.com/duangsuse-valid-projects/audio_to_midi_melodia) to extract pitches directly from music

## Tool `srt2mid.py` and `lrc_merge.py`

[srt2mid.py](srt2mid.py) can be used to make conversation between SRT / MIDI File format

Output filename is determined automatically from input path, and SRT representation of MIDI track will be timeline of integer(note pitch)s.

The default mode, "from", means "from srt to mid", and when extracting lyrics from mid file you have to use "back-lyrics" instead.

```plain
Usage: srt2mid [ from/back/back-lyrics ] files
```

[lrc_merge.py](lrc_merge.py) can be used to merge words-based lyrics into sentence-based lyrics

```plain
usage: lrc_merge [-h] [-dist n_sec] [-min-len n_sec] [-o name] (path / 'lrc')
```

+ `dist` max distance for words in same sentence, default `0.8`
+ `min-len` min duration for the last word in sentence (only when `lrc` input is used)

Execute `python3 lrc_merge.py -h` to see full details
