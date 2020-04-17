# -*- coding: utf-8 -*-

from typing import Tuple, List

from ctypes import sizeof, create_string_buffer, c_int16
from funutils import *

import numpy
from sf2utils.sf2parse import Sf2File

drivers = ["alsa", "oss", "jack", "portaudio", "sndmgr", "coreaudio", "Direct Sound", "pulseaudio"]

from FluidSynth import *

def fluid_synth_write_s16_stereo(synth, n: int, n_channel = 2) -> numpy.ndarray:
  """Return generated samples in stereo 16-bit format"""
  buf = create_string_buffer(n*n_channel*sizeof(c_int16))
  fluid_synth_write_s16(synth, n, buf, 0, n_channel, buf, 1, n_channel)
  return numpy.frombuffer(buf.raw, dtype=numpy.int16) #origin: copy buf[:]

class Synth:
  """Synth represents a FluidSynth synthesizer"""
  def __init__(self, gain=0.2, samplerate=44100, channels=256):
    self.settings = new_fluid_settings()
    self.synth = new_fluid_synth(self.settings)
    for (k, v) in { b"synth.gain": gain,
      b"synth.sample-rate": samplerate,
      b"synth.midi-channels": channels }.items(): self.setting(k, v)
    self.audio_driver = None
  def release(self):
    delete_fluid_synth(self.synth)
    delete_fluid_settings(self.settings)
    if self.audio_driver != None: delete_fluid_audio_driver(self.audio_driver)

  def setting(self, key, value):
    bk = key.encode() if isinstance(key, str) else key
    sets = self.settings
    if isinstance(value, int):
      fluid_settings_setint(sets, bk, value)
    elif isinstance(value, float):
      fluid_settings_setnum(sets, bk, value)
    elif isinstance(value, str):
      fluid_settings_setstr(sets, bk, value.encode())

  def sfload(self, filename, update_midi_preset=0) -> int:
      return fluid_synth_sfload(self.synth, filename.encode(), update_midi_preset)
  def sfunload(self, sfid, update_midi_preset=0):
      return fluid_synth_sfunload(self.synth, sfid, update_midi_preset)
  def program_select(self, chan, sfid, bank, preset):
      return fluid_synth_program_select(self.synth, chan, sfid, bank, preset)

  def noteon(self, chan, key, vel=127):
    require(chan, isNonnegative, "bad channel")
    require(key, isInbounds(0, 128), "bad key")
    require(vel, isInbounds(0, 128), "bad velocity")
    return fluid_synth_noteon(self.synth, chan, key, vel)
  def noteoff(self, chan, key):
    require(chan, isNonnegative, "bad channel")
    require(key, isInbounds(0, 128), "bad key")
    return fluid_synth_noteoff(self.synth, chan, key)

  def start(self, driver=platform({"linux": "alsa", "windows": "sndmgr", "macos": "coreaudio"}), device=None):
    """driver could be any str in drivers"""
    require(driver, drivers.__contains__, "unsupported driver")
    self.setting(b"audio.driver", driver)
    if device is not None: self.setting(f"audio.{driver}.device", device)
    self.audio_driver = new_fluid_audio_driver(self.settings, self.synth)
  def get_samples(self, n=1024):
    """Generate audio samples
    Returns ndarray containing n audio samples.
    If synth is set to stereo output(default) the array will be size 2*n.
    """
    return fluid_synth_write_s16_stereo(self.synth, n)

class NoteSynth(Synth):
  def __init__(self, sample_rate):
    super().__init__(samplerate=sample_rate)
    self.sample_rate = sample_rate
    self.last_pitch = (-1)
  @staticmethod
  def getFontPresets(path_sfont) -> List[Tuple[int, int, str]]:
    with open(path_sfont, "rb") as fbuf:
      sf = Sf2File(fbuf)
      return [(p.bank, p.preset, p.name) for p in sf.build_presets() if len(p.bags) != 0]

  def setFont(self, path_sfont, idx_preset = 0):
    presets = NoteSynth.getFontPresets(path_sfont)
    require(presets, hasIndex(idx_preset), "preset outbounds")
    preset = presets[idx_preset]
    (bank, patch, _) = preset
    self.program_select(0, self.sfload(path_sfont), bank, patch)

  def noteon(self, pitch): return super().noteon(0, pitch)
  def noteoff(self, pitch = None):
    return super().noteoff(0, pitch) if pitch != None else super().noteoff(0, self.last_pitch)
  def noteSwitch(self, pitch):
    if self.last_pitch != (-1):
      self.noteoff()
    self.noteon(pitch)
    self.last_pitch = pitch

  def sampleNote(self, n_sec):
    return self.get_samples(self.sample_rate*n_sec)
