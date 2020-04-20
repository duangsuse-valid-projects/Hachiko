#!/bin/env python3
# -*- coding: utf-8 -*-

from argparse import ArgumentParser, FileType
from time import time

import pygame
from synthesize import NoteSynth
from hachitools import *

from json import dumps, loads

def splitAs(type, transform = int, delim = ","):
  return lambda it: type(transform(s) for s in it.split(delim))

WINDOW_DIMEN = env("DIMEN", splitAs(tuple), (300,300))

backgroundColor = grayColor(env("GRAY_BACK", int, 0x30))
textColor = grayColor(env("GRAY_TEXT", int, 0xfa))
fontSize = env("SIZE_FONT", int, 36)

playDuration = env("PLAY_DURATION", splitAs(list, transform=float), [0.3, 0.5, 1.5])

INSTRUMENT_SF2 = env("SFONT", str, "instrument.sf2")
sampleRate = env("SAMPLE_RATE", int, 44100)
sfontPreset = 0

OCTAVE_NAMES = ["C","Cs","D","Ds","E","F","Fs","G","Gs","A","As","B"]
OCTAVE_MAX_VALUE = 12

BLACK_KEYS = [1, 3, 6, 8, 10]

def dumpOctave(pitch):
  octave, n = divmod(pitch, OCTAVE_MAX_VALUE)
  return f"{OCTAVE_NAMES[octave]}_{n}" + ("b" if n in BLACK_KEYS else "")
def readOctave(octa):
  octave, n = octa.rstrip("b").split("_")
  return OCTAVE_NAMES.index(octave)*OCTAVE_MAX_VALUE + int(n)


app = ArgumentParser(prog="hachi", description="Simple tool for creating pitch timeline",
    epilog="In pitch window, [0-9] select pitch; [Enter] add; [Backspace] remove last")
app.add_argument("-note-base", type=int, default=45, help="pitch base number")
app.add_argument("-note-preset", type=int, default=0, help=f"SoundFont ({INSTRUMENT_SF2}) preset index, count from 0")
app.add_argument("-play", type=FileType("r"), default=None, help="music file used for playing")
app.add_argument("-o", type=str, default="puzi.srt", help="output subtitle file path")

class RecordKeys(AsList):
  def actions(self, ctx, k):
    if k == '\x08': #<key delete
      if len(self.items) == 0: return
      rm = self.items.pop()
      ctx.show(f"!~{rm} #{len(self.items)}")
    elif k == 'r':
      print(dumps(self.items))
      n = int(input("n?> ") or len(self.items))
      ctx.slides(playDuration[1], *map(lambda i: f"!{i}", self.items[-n:]), "!done")
    elif k == 'k':
      expr = input("list> ")
      if expr != "": self.items = loads(expr)


from datetime import timedelta
from srt import Subtitle, compose
class AsSrt(AsList):
  def finish(self):
    td = lambda s: timedelta(seconds=s)
    return compose([Subtitle(i+1, td(p[0]), td(p[1]), str(p[2])) for (i, p) in enumerate(self.items)])

def main(args):
  cfg = app.parse_args(args)
  global sfontPreset; sfontPreset = cfg.note_preset
  pygame.init()
  rkeys = RecordKeys()
  pitches = guiReadPitches(cfg.note_base, rkeys, onKey=rkeys.actions)
  srt = guiReadTimeline(iter(pitches), AsSrt(), play=cfg.play)
  with open(cfg.o, "w+", encoding="utf-8") as srtf:
    srtf.write(srt)


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


def guiReadPitches(note_base, reducer, onKey = lambda ctx, k: (), caption = "Add Pitches"):
  gameWindow(caption, WINDOW_DIMEN)

  synth = NoteSynth(sampleRate)
  def playSec(n_sec, pitch):
    synth.noteSwitch(pitch)
    timeout(n_sec, synth.noteoff)

  synth.setFont(INSTRUMENT_SF2, sfontPreset)
  synth.start()
  playSec(playDuration[1], note_base)

  ctx = RefUpdate("Ready~!")
  intro = ctx.slides(playDuration[2], f"0={dumpOctave(note_base)}", "[P] proceed",
      "[-=] slide pitch", "[R]replay [K]bulk entry", "Have Fun!")

  def baseSlide(n):
    nonlocal note_base
    note_base += n
    playSec(playDuration[0], note_base)
    ctx.show(dumpOctave(note_base))

  def defaultOnKey(k):
    intro[0].cancel() #< stop intro anim
    if k == 'q': raise SystemExit()
    elif k == '-': baseSlide(-10)
    elif k == '=': baseSlide(+10)
    elif k == 'p': raise NonlocalReturn("proceed")
    elif k == '\r':
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

  while True: #v main logic
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

class CallFlagTimed(CallFlag):
  def __init__(self, op, op1):
    super().__init__(op, op1)
    self.t0 = time()
  def __call__(self):
    if self.flag:
      return super().__call__()
    else: #v resuming
      super().__call__()
      t0 = self.t0
      t1 = time()
      self.t0 = t1
      return t1 - t0

def guiReadTimeline(pitchz, reducer, play = None, caption = "Add Timeline", seek = 5.0, d_volume = 0.1):
  mus = pygame.mixer_music; mus_t0 = time()
  gameWindow(caption, WINDOW_DIMEN)
  if play != None:
    mus.load(play)
    mus.play()

  synth = NoteSynth(sampleRate)
  synth.setFont(INSTRUMENT_SF2, sfontPreset)
  synth.start()

  onPausePlay = CallFlagTimed(mus.unpause, mus.pause)
  gameCenterText("[A]keep [S]split")
  t0 = time()
  t1 = None

  def nextPitch():
    try: return next(pitchz)
    except StopIteration: raise NonlocalReturn("done")
  def splitNote():
    synth.noteSwitch(nextPitch())
  def giveSegment():
    nonlocal t1
    t2 = time()
    reducer.accept( (t1-t0, t2-t0, synth.last_pitch) )
    t1 = t2 #< new start

  def onEvent(event):
    nonlocal t0, t1, mus_t0
    if event.type == pygame.KEYDOWN:
      key = chr(event.key)
      if key == 'a':
        t1 = time()
        splitNote()
      elif key == 's': giveSegment(); splitNote()
    elif event.type == pygame.KEYUP:
      key = chr(event.key)
      if key == 'a':
        synth.noteoff()
        giveSegment()
      elif key == ' ':
        t = onPausePlay()
        if t != None: t0 += t
      elif key == 'ē': # Arrow-Right
        if mus.get_pos() == (-1): return
        pos = time() - mus_t0 #< pygame mixer_music.get_pos does not follow set_pos
        newpos = pos+seek
        print("+@", pos, newpos)
        mus.set_pos(newpos)
        mus_t0 -= seek
        t0 -= seek
      elif key == '-': # volume down
        mus.set_volume(mus.get_volume() - d_volume)
      elif key == '=': # volume up
        mus.set_volume(mus.get_volume() + d_volume)

    elif event.type == pygame.QUIT: raise SystemExit()
  while True:
    try:
      for event in pygame.event.get(): onEvent(event)
    except NonlocalReturn: break
  return reducer.finish()

from sys import argv
if __name__ == "__main__": main(argv[1:])
