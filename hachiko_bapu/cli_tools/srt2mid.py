#!/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Iterator, cast

from datetime import timedelta
from srt import Subtitle, parse as srt_parse, compose as srt_compose
from mido import Message, MetaMessage, MidiFile, MidiTrack

from sys import getdefaultencoding
from os import environ

SEC_MS = 1000

def env(name, transform, default): return transform(environ[name]) if name in environ else default
SINGLE_TRACK = env("SINGLE_TRACK", bool, False)
TICKS_PER_BEAT = env("TICKS_PER_BEAT", int, 500) #480? both for srt->mid and mid<-srt
NOTE_BASE = env("NOTE_BASE", int, 45)

def transform(srtz:Iterator[Subtitle], is_lyrics:bool) -> MidiFile:
  out = MidiFile(charset=getdefaultencoding(), ticks_per_beat=TICKS_PER_BEAT)
  track = MidiTrack()
  out.tracks.append(track)

  timeof = lambda dt: int(dt.total_seconds()*SEC_MS)
  t0 = 0
  for srt in srtz:
    t1 = timeof(srt.start)
    t2 = timeof(srt.end)
    if is_lyrics: #v const branches
      track.append(MetaMessage("lyrics", text=srt.content, time=t1-t0))
    note = NOTE_BASE if is_lyrics else int(srt.content) #< pitch from
    track.append(Message("note_on", note=note, time=0 if is_lyrics else t1-t0))
    track.append(Message("note_off", note=note, time=t2-t1))
    t0 = t2

  return out

def transformBack(notez:Iterator[Message], is_lyrics:bool, k_time:float) -> List[Subtitle]:
  out = []
  def read(ty, blanks = ["set_tempo"]):
    note = next(notez)
    if note.type != ty:
      if note.type == "end_of_track": raise StopIteration("EOT")
      while note.type in blanks: note = next(notez) #< jump off!
      if note.type != ty: raise ValueError(f"unexpected msg {note}, expecting {ty}")
    return note

  timeof = lambda n: timedelta(seconds=n/k_time)
  t_acc = timedelta(); lyric = None
  index = 1 #< for subtitles
  while True:
    try:
      if is_lyrics: lyric = read("lyrics")
      on = read("note_on")
      t_on = timeof(lyric.time if is_lyrics else on.time)
      t_off = timeof(read("note_off").time)
    except StopIteration: break #v pitch back
    out.append(Subtitle(index, t_acc+t_on, t_acc+t_on+t_off, lyric.text if is_lyrics else str(on.note) ))
    t_acc += (t_on + t_off)
    index += 1

  return out


def newPath(f, ext):
  return f.name.rsplit(".")[0] + f".{ext}"

def fromSrtFile(f, is_lyrics):
  transform(srt_parse(f.read()), is_lyrics).save(newPath(f, "mid"))

def backMidFile(f, is_lyrics):
  midi = MidiFile(f.name, charset=getdefaultencoding(), ticks_per_beat=TICKS_PER_BEAT)
  (notes, k_time) = (cast(MidiTrack, max(midi.tracks, key=len)), SEC_MS) if SINGLE_TRACK else (midi, 1)

  text_srt = srt_compose(transformBack(iter(notes), is_lyrics, float(k_time)))
  with open(newPath(f, "srt"), "w+") as srtf: srtf.write(text_srt)

def midiNotes(path): #< merged from old midnotes.py
  for i, track in enumerate(MidiFile(path).tracks):
    msgs = [track[index] for index in range(0, len(track), 2)] #note-on -- note-off
    for msg in msgs:
      note = msg.dict().get("note")
      if note != None: yield note

modes = {
  "from": lambda f: fromSrtFile(f, False),
  "from-lyrics": lambda f: fromSrtFile(f, True),
  "back": lambda f: backMidFile(f, False),
  "back-lyrics": lambda f: backMidFile(f, True),
  "print-notes": lambda f: print(list(midiNotes(f.name)))
}

from sys import argv
def main(args = argv[1:]):
  if len(args) < 1:
    print(f"Usage: srt2mid [ {'/'.join(modes.keys())} ] files...")
    return
  mname = args[0]
  (mode, paths) = (modes["from"], args[0:]) if mname not in modes else (modes[mname], args[1:])
  for path in paths:
    with open(path, "r") as ins: mode(ins)

if __name__ == "__main__": main()
