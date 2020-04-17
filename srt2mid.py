#!/bin/env python3
# -*- coding: utf-8 -*-

import srt
from mido import Message, MidiFile, MidiTrack

def transform(srts):
  out = MidiFile()
  track = MidiTrack()
  out.tracks.append(track)

  timeof = lambda dt: int(dt.total_seconds()*1000)
  t0 = 0
  for srt in srts:
    note = int(srt.content)
    t1 = timeof(srt.start)
    t2 = timeof(srt.end)
    track.append(Message("note_on", note=note, time=t1-t0))
    track.append(Message("note_off", note=note, time=t2-t1))
    t0 = t2

  return out

def main(args):
  if len(args) < 1:
    print("Usage: srt2mid files")
    return
  for path in args:
    with open(path, "r") as srtf:
      srts = srt.parse(srtf.read())
      transform(srts).save(path.rsplit(".")[0] + ".mid")

from sys import argv
if __name__ == "__main__": main(argv[1:])
