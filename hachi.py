#!/bin/env python3
# -*- coding: utf-8 -*-

from argparse import ArgumentParser
from time import time
from threading import Timer

import pygame
from synthesize import NoteSynth

WINDOW_DIMEN = (300,300)

def grayColor(n): return (n,n,n)
backgroundColor = grayColor(0x30)
textColor = grayColor(0xfa)
fontSize = 36

INSTRUMENT_SF2 = "instrument.sf2"
sampleRate = 44100

OCTAVE_NAMES = ["C","Cs","D","Ds","E","F","Fs","G","Gs","A","As","B"]
OCTAVE_MAX_VALUE = 12

BLACK_KEYS = [1, 3, 6, 8, 10]

def dumpOctave(pitch):
  octave, n = divmod(pitch, OCTAVE_MAX_VALUE)
  return f"{OCTAVE_NAMES[octave]}_{n}" + ("b" if n in BLACK_KEYS else "")
def readOctave(octa):
  octave, n = octa.rstrip("b").split("_")
  return OCTAVE_NAMES.index(octave)*OCTAVE_MAX_VALUE + int(n)

def timeout(n_sec, op):
  timer = Timer(n_sec, op); timer.start()
  return timer

class NonlocalReturn(Exception):
  def __init__(self, value):
    super().__init__(value)
  @property
  def value(self): return self.args[0]

class Fold:
  def __init__(self): pass
  def accept(self, value): pass
  def finish(self): pass

class RefUpdate:
  def __init__(self, initial = ""):
    self._text = initial; self.last_text = None
  @property
  def text(self): return self._text
  def update(self): self.last_text = self._text

  def show(self, text):
    self.update()
    self._text = text
  def hasUpdate(self):
    has_upd = self.last_text != self.text
    self.update()
    return has_upd
  def slides(self, n_sec, *texts):
    stream = iter(texts)
    def showNext():
      nonlocal timeouts
      try:
        self.show(next(stream))
        timeouts[0] = timeout(n_sec, showNext)
      except StopIteration: pass
    timeouts = [timeout(n_sec, showNext )]
    return timeouts

app = ArgumentParser(prog="hachi", description="Simple tool for creating pitch timeline")
app.add_argument("-note-base", type=int, default=45, help="pitch base number")
app.add_argument("-play", type=str, default=None, help="music file used")
app.add_argument("-use-hot", default=False, action="store_true", help="make key A and key S associated")

class RecordKeys(Fold):
  def __init__(self):
    self.notes = []
  def accept(self, value):
    self.notes.append(value)
  def finish(self): return self.notes
  def actions(self, ctx, k):
    if k == '\x08': #<key delete
      rm = self.notes.pop()
      ctx.show(f"~{rm} #{len(self.notes)}")
    elif k == 'r':
      print(self.notes)
      n = int(input("n?> ") or len(self.notes))
      ctx.slides(0.5, *map(lambda i: f"!{i}", self.notes[-n:]), "!done")
    elif k == 'k':
      expr = input("list> ")
      if expr != "": self.notes = eval(expr)

def main(args):
  cfg = app.parse_args(args)
  rkeys = RecordKeys()
  pitches = guiReadPitches(cfg.note_base, rkeys, "Add Pitches", rkeys.actions)


def guiReadPitches(note_base, reducer, caption, onKey = lambda ctx, k: ()):
  pygame.init()
  pygame.display.set_mode(WINDOW_DIMEN)
  pygame.display.set_caption(caption)

  synth = NoteSynth(sampleRate)
  def playSec(n_sec, pitch):
    synth.noteSwitch(pitch)
    timeout(n_sec, synth.noteoff)

  synth.setFont(INSTRUMENT_SF2)
  synth.start()
  playSec(0.5, note_base)

  ctx = RefUpdate("Ready~!")
  intro = ctx.slides(1.5, f"0={dumpOctave(note_base)}", "[P] proceed", "[-=] slide pitch", "Have Fun!")

  def base_slide(n):
    nonlocal note_base
    note_base += n
    playSec(0.3, note_base)
    ctx.show(dumpOctave(note_base))
  def defaultOnKey(k):
    if k == 'q': raise SystemExit()
    elif k == '-': base_slide(-10)
    elif k == '=': base_slide(+10)
    elif k == 'p': raise NonlocalReturn("proceed")
    elif k == '\r':
      intro[0].cancel()
      try: reducer.accept(readOctave(ctx.text))
      except ValueError: ctx.show(":\\")
    else: onKey(ctx, k)
  def onEvent(event):
    notNumber = lambda: event.key not in range(ord('0'), ord('9')+1)
    getNumber = lambda: note_base + (event.key - ord('0'))

    if event.type == pygame.KEYDOWN:
      if notNumber(): return
      else:
        pitch = getNumber()
        synth.noteon(pitch)
        ctx.show(dumpOctave(pitch))
    elif event.type == pygame.KEYUP:
      if notNumber(): defaultOnKey(chr(event.key))
      else: synth.noteoff(getNumber())
    elif event.type == pygame.QUIT:
      raise SystemExit()

  while True:
    bg = pygame.display.get_surface()
    bg.fill(backgroundColor)

    if pygame.font and ctx.hasUpdate():
      text = ctx.text
      if len(text) != 0 and text[0] == '!':
        cmd = text[1:]
        if cmd == "done": synth.noteoff()
        else: synth.noteSwitch(int(cmd))
      font = pygame.font.Font(None, fontSize)
      rtext = font.render(text, 1, textColor)
      textpos = rtext.get_rect(centerx=bg.get_width()/2, centery=bg.get_height()/2)
      bg.blit(rtext, textpos)
      pygame.display.flip()

    try:
      for event in pygame.event.get(): onEvent(event)
    except NonlocalReturn as exc:
      if exc.value == "proceed": break
  return reducer.finish()

from sys import argv
if __name__ == "__main__": main(argv[1:])
