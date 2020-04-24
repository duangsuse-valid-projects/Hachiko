#!/bin/env python3
# -*- coding: utf-8 -*-

from datetime import timedelta
import srt
from mido import Message, MidiFile, MidiTrack

from sys import getdefaultencoding

SEC_MS = 1000

def transform(srts):
  out = MidiFile()
  track = MidiTrack()
  out.tracks.append(track)

  timeof = lambda dt: int(dt.total_seconds()*SEC_MS)
  t0 = 0
  for srt in srts:
    note = int(srt.content)
    t1 = timeof(srt.start)
    t2 = timeof(srt.end)
    track.append(Message("note_on", note=note, time=t1-t0))
    track.append(Message("note_off", note=note, time=t2-t1))
    t0 = t2

  return out

def transformBack(notes: MidiTrack, is_lyrics):
  out = []
  notez = iter(notes)
  def read(ty):
    note = next(notez)
    if note.type != ty:
      if note.type == "end_of_track": raise StopIteration("EOT")
      else: raise ValueError(f"unexpected note near {note}, expecting {ty}")
    return note

  timeof = lambda n: timedelta(seconds=n/SEC_MS)
  t_acc = timedelta(); lyric = None
  index = 1 #< for subtitles
  while True:
    try:
      if is_lyrics: lyric = read("lyrics")
      on = read("note_on")
      t_on = timeof(lyric.time if is_lyrics else on.time)
      t_off = timeof(read("note_off").time)
    except StopIteration: break
    out.append(srt.Subtitle(index, t_acc+t_on, t_acc+t_on+t_off, lyric.text if is_lyrics else str(on.note) ))
    t_acc += (t_on + t_off)
    index += 1

  return out

def newPath(f, ext):
  return f.name.rsplit(".")[0] + f".{ext}"

def backMidFile(f, is_lyrics):
  track = max(MidiFile(f.name, charset=getdefaultencoding()).tracks, key=len)
  srts = srt.compose(transformBack(track, is_lyrics))
  with open(newPath(f, "srt"), "w+") as srtf: srtf.write(srts)

modes = {
  "from": lambda f: transform(srt.parse(f.read())).save(newPath(f, "mid")),
  "back": lambda f: backMidFile(f, False),
  "back-lyrics": lambda f: backMidFile(f, True)
}

def main(args):
  if len(args) < 1:
    print(f"Usage: srt2mid [ {'/'.join(modes.keys())} ] files")
    return
  mname = args[0]
  (mode, paths) = (modes["from"], args[0:]) if mname not in modes else (modes[mname], args[1:])
  for path in paths:
    with open(path, "r") as ins: mode(ins)

from sys import argv
if __name__ == "__main__": main(argv[1:])
