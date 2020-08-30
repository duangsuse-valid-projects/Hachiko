#!/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any, Callable, Optional, TypeVar, Generic
A = TypeVar("A"); T = TypeVar("T")

from argparse import ArgumentParser, FileType
from time import time
from datetime import timedelta

from srt import Subtitle, compose
from json import loads, dumps, JSONDecodeError

from os import environ, system #v disable prompt
environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import pygame

from .hachitools import *
from .synthesize import NoteSynth
from pkg_resources import resource_filename
from .funutils import let

def splitAs(type, transform = int, delim = ","):
  return lambda it: type(transform(s) for s in it.split(delim))

WINDOW_DIMEN = env("DIMEN", splitAs(tuple), (300,300))
NAME_STDOUT = "-"

backgroundColor = env("COLOR_BACK", htmlColor, grayColor(0x30))
textColor = env("COLOR_TEXT", htmlColor, grayColor(0xfa))
fontName = env("FONT_NAME", str, "Arial")
fontSize = env("FONT_SIZE", int, 36)

askMethod = env("ASK_METHOD", str, "tk")
playDuration = env("PLAY_DURATION", splitAs(list, transform=float), [0.3, 0.5, 1.5])
cmdOnDone = env("HACHIKO_DONE", str, "srt2mid out")

INSTRUMENT_SF2 = env("SFONT", str, resource_filename(__name__, "instrument.sf2"))
sampleRate = env("SAMPLE_RATE", int, 44100)
synth = NoteSynth(sampleRate) #< used twice

bgmVolume = env("BGM_VOLUME", float, None)
bgmSpeed = env("BGM_SPEED", float, None) #TODO

OCTAVE_NAMES = ["C","Cs","D","Ds","E","F","Fs","G","Gs","A","As","B"]
OCTAVE_MAX_VALUE = 12

BLACK_KEYS = [1, 3, 6, 8, 10]

from string import digits
def dumpOctave(pitch):
  octave, n = divmod(pitch, OCTAVE_MAX_VALUE)
  return f"{OCTAVE_NAMES[octave]}_{n} " + ("b" if n in BLACK_KEYS else "") + f"'{pitch}"
def readOctave(octa):
  octave, n = octa.rstrip(f"b'{digits}").split("_")
  return OCTAVE_NAMES.index(octave)*OCTAVE_MAX_VALUE + int(n)

def blockingAskThen(onDone:Callable[[T], Any], name:str, transform:Callable[[str],T], placeholder:Optional[str] = None):
  if askMethod == "input":
    if placeholder != None: print(placeholder, file=stderr)
    answer = input(f"{name}?> ")
    if answer != "": onDone(transform(answer))
  elif askMethod == "tk":
    from tkinter import Tk
    from tkinter.simpledialog import askstring
    tk = Tk(); tk.withdraw() #< born hidden

    answer = askstring(f"Asking for {name}", f"Please input {name}:", initialvalue=placeholder or "")
    tk.destroy()
    if answer != None: onDone(transform(answer))
  else: raise ValueError(f"unknown asking method {askMethod}")

app = ArgumentParser(prog="hachi", description="Simple tool for creating pitch timeline",
    epilog="In pitch window, [0-9] select pitch; [Enter] add; [Backspace] remove last\n"+
      f"Useful env-vars: SAMPLE_RATE, SFONT (sf2 path), ASK_METHOD (tk/input); pygame {pygame.ver}")
app.add_argument("-note-base", type=int, default=45, help="pitch base number")
app.add_argument("-note-preset", type=int, default=0, help=f"SoundFont ({INSTRUMENT_SF2}) preset index, count from 0")
app.add_argument("-seq", type=str, default=None, help="sequence given in pitch editor window")
app.add_argument("-play", type=FileType("r"), default=None, help="music file used for playing")
app.add_argument("-play-seek", type=float, default=0.0, help="initial seek for player")
app.add_argument("-o", type=str, default="puzi.srt", help="output subtitle file path (default puzi.srt, can be - for stdout)")

class ActionHandler(Generic[A, T]):
  def actions(self, ctx:A, key:T): pass

class RecordKeys(AsList, ActionHandler[RefUpdate, str]):
  def actions(self, ctx, key):
    if key == '\x08': #<key delete
      if len(self.items) == 0: return
      rm = self.items.pop()
      ctx.show(f"!~{rm} #{len(self.items)}")
    elif key == 'r':
      play = lambda n: ctx.slides(playDuration[1], *map(lambda i: f"!{i}", self.items[-n:]), "!done")
      try: blockingAskThen(play, "n", int, str(len(self.items)))
      except ValueError: ctx.show("Invalid Count")
    elif key == 'k':
      def save(answer):
        if isinstance(answer, (list, str)): self.items = answer
        else: ctx.show(f"Not List: {answer}")
      try: blockingAskThen(save, "list", loads, dumps(self.items))
      except JSONDecodeError: ctx.show("Load Failed")

class AsSrt(AsList):
  def finish(self):
    td = lambda s: timedelta(seconds=s)
    return compose([Subtitle(i+1, td(p[0]), td(p[1]), str(p[2])) for (i, p) in enumerate(self.items)])

from sys import argv, stdout, stderr
def main(args = argv[1:]):
  cfg = app.parse_args(args)
  global synth; calmSetSFont(synth, INSTRUMENT_SF2, cfg.note_preset); synth.start()
  pygame.mixer.init(sampleRate)
  pygame.init()
  rkeys = RecordKeys()
  pitches = loads(cfg.seq) if cfg.seq != None else guiReadPitches(cfg.note_base, rkeys, onKey=rkeys.actions)
  srt = guiReadTimeline(iter(pitches), AsSrt(), play=cfg.play, play_seek=cfg.play_seek)

  if cfg.o == NAME_STDOUT: stdout.write(srt)
  else:
    with open(cfg.o, "w+", encoding="utf-8") as srtf: srtf.write(srt)
  system(cmdOnDone.replace("out", cfg.o))


def gameWindow(caption, dimen):
  pygame.display.set_caption(caption)
  pygame.display.set_mode(dimen)

def gameCenterText(text, cx=0.5, cy=0.5):
  bg = pygame.display.get_surface()
  bg.fill(backgroundColor)

  font = pygame.font.SysFont(fontName, fontSize)
  rtext = font.render(text, 1, textColor)
  textpos = rtext.get_rect(centerx=bg.get_width()*cx, centery=bg.get_height()*cy)
  bg.blit(rtext, textpos)
  pygame.display.flip()

def mainloopCall(handler):
  for event in pygame.event.get(): handler(event)

def calmSetSFont(synth, path, preset):
  try: synth.setFont(path, preset)
  except OSError: print(f"{path} is required to enable note playback!", file=stderr)

def guiReadPitches(note_base:int, reducer, onKey = lambda ctx, k: (), caption = "Add Pitches"):
  gameWindow(caption, WINDOW_DIMEN)

  def playSec(n_sec, pitch):
    synth.noteSwitch(pitch)
    timeout(n_sec, synth.noteoff)

  playSec(playDuration[1], note_base)

  ctx = RefUpdate("Ready~!")
  intro = ctx.slides(playDuration[2], f"0={dumpOctave(note_base)}", "[P] proceed",
      "[-=] slide pitch", "[R]replay [K]list", "Have Fun!")

  def baseSlide(n):
    nonlocal note_base
    note_base = (note_base + n) % 128 #< cyclic coerceLT
    playSec(playDuration[0], note_base)
    ctx.show(dumpOctave(note_base))

  def defaultOnKey(k):
    if k == 'q': raise SystemExit()
    elif k == '-': baseSlide(-10)
    elif k == '=': baseSlide(+10)
    elif k == 'p': raise NonlocalReturn("proceed")
    elif k == '\r':
      try: reducer.accept(readOctave(ctx.item))
      except ValueError: ctx.show(":\\")
    else: onKey(ctx, k)
  def onEvent(event):
    notNumber = lambda: event.key not in range(ord('0'), ord('9')+1)
    getNumber = lambda: note_base + (event.key - ord('0'))

    if event.type == pygame.KEYDOWN:
      if len(intro) == 1: intro[0].cancel(); intro.pop() #< stop intro anim
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
      text = ctx.item
      if len(text) != 0 and text[0] == '!':
        cmd = text[1:]
        if cmd == "done": synth.noteoff()
        elif cmd.startswith("~"): playSec(playDuration[0], int(cmd[1:].rsplit("#")[0]))
        else: synth.noteSwitch(int(cmd))
      gameCenterText(text)

    try: mainloopCall(onEvent)
    except NonlocalReturn as exc:
      if exc.value == "proceed": break
  return reducer.finish()

class SwitchCallTimed(SwitchCall): #< time record (op -- op1)*
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

def guiReadTimeline(pitchz, reducer, play = None, play_seek = 0.0, caption = "Add Timeline", d_seek = 5.0, d_volume = 0.1, note_base = 45):
  mus = pygame.mixer_music; mus_t0 = time()
  gameWindow(caption, WINDOW_DIMEN)
  if play != None:
    mus.load(play)
    let(mus.set_volume, bgmVolume)
    mus.play()

  onPausePlay = SwitchCallTimed(mus.unpause, mus.pause)
  gameCenterText("[A]keep [S]split")
  t0 = time()
  t1 = None
  def seek(dist:float):
    nonlocal mus_t0, t0
    if mus.get_pos() == (-1): return
    pos = time() - mus_t0 #< pygame mixer_music.get_pos does not follow set_pos
    newpos = pos+dist
    print("+@", pos, newpos, file=stderr)
    mus.set_pos(newpos)
    mus_t0 -= dist
    t0 -= dist
  seek(play_seek)

  last_item = None #< function could be rewritten in two variants
  def nextPitch():
    try: return next(pitchz)
    except StopIteration: raise NonlocalReturn()
  def splitNote():
    nonlocal last_item
    pitch = nextPitch() #v compat for alternative type
    if isinstance(pitch, int): synth.noteSwitch(pitch)
    else:
      synth.noteSwitch(note_base if synth.last_pitch != note_base else note_base+2)
      last_item = pitch
      gameCenterText(str(pitch))
  def giveSegment():
    nonlocal t1
    t2 = time()
    reducer.accept( (t1-t0, t2-t0, last_item or synth.last_pitch) )
    t1 = t2 #< new start

  def onEvent(event):
    nonlocal t0, t1
    evt = event.type
    isKdown = (evt == pygame.KEYDOWN)
    def actButton(): return ('a' if event.button == 1 else 's')
    if isKdown or evt == pygame.MOUSEBUTTONDOWN:
      key = chr(event.key) if isKdown else actButton()
      if key == 's': giveSegment(); splitNote()
      elif key == 'a':
        t1 = time()
        splitNote()
    elif evt == pygame.KEYUP or evt == pygame.MOUSEBUTTONUP:
      key = chr(event.key) if evt==pygame.KEYUP else actButton()
      if key == 'a': # paired A
        synth.noteoff()
        giveSegment()
      elif key == ' ':
        t = onPausePlay()
        if t != None: t0 += t
      elif key == 'ē': # Arrow-Right
        seek(d_seek)
      elif key == '-': # volume down
        mus.set_volume(mus.get_volume() - d_volume)
      elif key == '=': # volume up
        mus.set_volume(mus.get_volume() + d_volume)

    elif evt == pygame.QUIT: raise SystemExit()
  while True:
    try: mainloopCall(onEvent)
    except NonlocalReturn: break
  synth.noteoff()
  return reducer.finish()

if __name__ == "__main__": main()
