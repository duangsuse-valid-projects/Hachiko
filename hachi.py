#!/bin/env python3
# -*- coding: utf-8 -*-

from argparse import ArgumentParser
from time import time

import pygame
from synthesize import NoteSynth
from hachitools import *

WINDOW_DIMEN = (300,300)

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
      if len(self.notes) == 0: return
      rm = self.notes.pop()
      ctx.show(f"!~{rm} #{len(self.notes)}")
    elif k == 'r':
      print(self.notes)
      n = int(input("n?> ") or len(self.notes))
      ctx.slides(0.5, *map(lambda i: f"!{i}", self.notes[-n:]), "!done")
    elif k == 'k':
      expr = input("list> ")
      if expr != "": self.notes = eval(expr)

class AsList(Fold):
  def __init__(self):
    self.items = []
  def accept(self, value):
    self.items.append(value)
  def finish(self): return self.items

from datetime import timedelta
from srt import Subtitle, compose
class AsSrt(AsList):
  def finish(self):
    td = lambda s: timedelta(seconds=s)
    return compose([Subtitle(i+1, td(p[0]), td(p[1]), str(p[2])) for (i, p) in enumerate(self.items)])

def main(args):
  cfg = app.parse_args(args)
  pygame.init()
  rkeys = RecordKeys()
  pitches = guiReadPitches(cfg.note_base, rkeys, onKey=rkeys.actions)
  srt = guiReadTimeline(iter(pitches), AsSrt(), play=cfg.play, mode="hot" if cfg.use_hot else "normal")
  print(srt)

def gameWindow(caption, dimen):
  pygame.display.set_caption(caption)
  pygame.display.set_mode(dimen)

def gameCenterText(text, cx=0.5, cy=0.5):
  bg = pygame.display.get_surface()
  bg.fill(backgroundColor)

  font = pygame.font.Font(None, fontSize)
  rtext = font.render(text, 1, textColor)
  textpos = rtext.get_rect(centerx=bg.get_width()*cx, centery=bg.get_height()*cy)
  bg.blit(rtext, textpos)
  pygame.display.flip()

playDuration = [0.3, 0.5]

def guiReadPitches(note_base, reducer, caption = "Add Pitches", onKey = lambda ctx, k: ()):
  gameWindow(caption, WINDOW_DIMEN)

  synth = NoteSynth(sampleRate)
  def playSec(n_sec, pitch):
    synth.noteSwitch(pitch)
    timeout(n_sec, synth.noteoff)

  synth.setFont(INSTRUMENT_SF2)
  synth.start()
  playSec(playDuration[1], note_base)

  ctx = RefUpdate("Ready~!")
  intro = ctx.slides(1.5, f"0={dumpOctave(note_base)}", "[P] proceed",
                     "[-=] slide pitch", "[R]replay [K]bulk entry", "Have Fun!")

  def base_slide(n):
    nonlocal note_base
    note_base += n
    playSec(playDuration[0], note_base)
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
    if pygame.font and ctx.hasUpdate():
      text = ctx.text
      if len(text) != 0 and text[0] == '!':
        cmd = text[1:]
        if cmd == "done": synth.noteoff()
        elif cmd.startswith("~"): playSec(playDuration[0], int(cmd[1:].rsplit("#")[0]))
        else: synth.noteSwitch(int(cmd))
      gameCenterText(text)

    try:
      for event in pygame.event.get(): onEvent(event)
    except NonlocalReturn as exc:
      if exc.value == "proceed": break
  return reducer.finish()

class CallFlag:
  def __init__(self, op, op1):
    self.flag = False
    self.op, self.op1 = op, op1
  def __call__(self):
    self.op() if self.flag else self.op1()
    self.flag = not self.flag

def guiReadTimeline(pitchz, reducer, play = None, mode = "normal", caption = "Add Timeline"):
  mus = pygame.mixer_music
  gameWindow(caption, WINDOW_DIMEN)
  is_hot = mode == "hot"
  if play != None:
    mus.load(play)
    mus.play()

  synth = NoteSynth(sampleRate)
  synth.setFont(INSTRUMENT_SF2)
  synth.start()

  onPausePlay = CallFlag(mus.unpause, mus.pause)
  gameCenterText("[A]split" if is_hot else "[A]keep [S]split")
  t0 = time()
  t1 = None
  def giveSegment():
    nonlocal t1
    t2 = time()
    reducer.accept( (t1-t0, t2-t0, synth.last_pitch) )
    t1 = t2 #< new start

  synth.last_pitch = 0 if is_hot else next(pitchz, 50) #< hot: (key A) will load first pitch
  def nextPitch():
    try: return next(pitchz)
    except StopIteration: raise NonlocalReturn("done")
  def doSplit(): synth.noteSwitch(nextPitch())

  def onEvent(event):
    nonlocal t1
    if event.type == pygame.KEYDOWN:
      key = chr(event.key)
      if key == 'a':
        t1 = time()
        if is_hot: doSplit()
        else: synth.noteon(synth.last_pitch)
    elif event.type == pygame.KEYUP:
      key = chr(event.key)
      if key == ' ': onPausePlay()
      elif key == 'a':
        synth.noteoff()
        giveSegment()
        if not is_hot: synth.last_pitch = nextPitch()
      elif key == 's' and not is_hot: doSplit(); giveSegment()

    elif event.type == pygame.QUIT: raise SystemExit()
  while True:
    try:
      for event in pygame.event.get(): onEvent(event)
    except NonlocalReturn: break
  return reducer.finish()

from sys import argv
if __name__ == "__main__": main(argv[1:])
