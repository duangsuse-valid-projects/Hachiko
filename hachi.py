#!/bin/env python3
# -*- coding: utf-8 -*-

from argparse import ArgumentParser
from time import time
from threading import Timer

import pygame
from synthesize import NoteSynth

WINDOW_DIMEN = (300,300)
INSTRUMENT_SF2 = "instrument.sf2"
sampleRate = 44100

def timeout(n_sec, op):
  timer = Timer(n_sec, op); timer.start()
  return timer

class NonlocalReturn(Exception):
  def __init__(self, value):
    super().__init__(value)
  @property
  def value(self): return self.args[0]

app = ArgumentParser(prog="hachi", description="Simple tool for creating pitch timeline")
app.add_argument("-note-base", type=int, default=45, help="pitch base number")
app.add_argument("-play", type=str, default=None, help="music file used")
app.add_argument("-use-hot", default=False, action="store_true", help="make key A and key S associated")


def main(args):
  cfg = app.parse_args(args)
  guiReadPitches(cfg.note_base)

def guiReadPitches(note_base):
  pygame.init()
  pygame.display.set_mode(WINDOW_DIMEN)
  notes = []

  synth = NoteSynth(sampleRate)
  synth.setFont(INSTRUMENT_SF2)
  synth.start()
  def playSec(n_sec, pitch = note_base):
    synth.noteSwitch(note_base)
    timeout(n_sec, synth.noteoff)
  playSec(0.5)

  def base_slide(n):
    nonlocal note_base
    note_base += n
    playSec(0.3)
  def onKey(k):
    if k == 'q': raise SystemExit()
    elif k == '-': base_slide(-10)
    elif k == '=': base_slide(+10)
    elif k == 'p': raise NonlocalReturn("proceed")
    elif k == 'r': pass
  def onEvent(event):
    notNumber = lambda: event.key not in range(ord('0'), ord('9')+1)
    getNumber = lambda: note_base + (event.key - ord('0'))

    if event.type == pygame.KEYDOWN:
      if notNumber(): return
      else: synth.noteon(getNumber())
    elif event.type == pygame.KEYUP:
      if notNumber(): onKey(chr(event.key))
      else: synth.noteoff(getNumber())

  while True:
    try: 
      for event in pygame.event.get(): onEvent(event)
    except NonlocalReturn as exc:
      if exc.value == "proceed": break
  return notes

from sys import argv
if __name__ == "__main__": main(argv[1:])
