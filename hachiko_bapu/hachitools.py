from typing import Any, Callable, Optional, TypeVar; T = TypeVar("T")

from threading import Timer
from os import environ

SEC_MS = 1000

def grayColor(n:int): return (n,n,n)

def env(name:str, transform:Callable[[str],T], default:T) -> T:
  return transform(environ[name]) if name in environ else default

def timeout(n_sec:float, op):
  timer = Timer(n_sec, op); timer.start()
  return timer

class NonlocalReturn(Exception):
  def __init__(self, value = None):
    super().__init__(value)
  @property
  def value(self): return self.args[0]

class Fold:
  def __init__(self): pass
  def accept(self, value): pass
  def finish(self): pass

class AsList(Fold):
  def __init__(self):
    self.items = []
  def accept(self, value):
    self.items.append(value)
  def finish(self): return self.items

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
    timeouts = [timeout(n_sec, showNext)]
    return timeouts

class CallFlag:
  def __init__(self, op, op1):
    self.flag = False
    self.op, self.op1 = op, op1
  def __call__(self):
    self.op() if self.flag else self.op1()
    self.flag = not self.flag
