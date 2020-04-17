#!/bin/env python3
# -*- coding: utf-8 -*-

from mido import MidiFile

def midiNotes(path):
  midi_file = MidiFile(path)

  for i, track in enumerate(midi_file.tracks):
    msgs = [track[index] for index in range(0, len(track), 2)] #note-on -- note-off
    for msg in msgs:
      note = msg.dict().get("note")
      if note != None: yield note

from sys import argv
if __name__ == "__main__": print(list(midiNotes(argv[1])))
