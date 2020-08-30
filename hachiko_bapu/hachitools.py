from typing import Any, Callable, Optional, List, TypeVar, Generic
T = TypeVar("T"); R = TypeVar("R")

from threading import Timer
from os import environ

SEC_MS = 1000

def htmlColor(c:str): return tuple(int(c[i-1:i+1], 16) for i in range(1, len(c), 2))
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

class Fold(Generic[T, R]):
  def __init__(self): pass
  def accept(self, value:T): pass
  def finish(self) -> R: pass

class AsList(Generic[T], Fold[T, List[T]]):
  def __init__(self):
    self.items = []
  def accept(self, value):
    self.items.append(value)
  def finish(self): return self.items

class RefUpdate(Generic[T]):
  def __init__(self, initial:T):
    self._item = initial; self.last_item:Optional[T] = None
  @property
  def item(self): return self._item
  def _updated(self): self.last_item = self._item

  def hasUpdate(self):
    has_upd = self.last_item != self.item
    self._updated() # used in check loop
    return has_upd
  def show(self, item:T):
    self._updated()
    self._item = item
  def slides(self, n_sec, *items:T):
    stream = iter(items)
    def showNext():
      nonlocal timeouts
      try:
        self.show(next(stream))
        timeouts[0] = timeout(n_sec, showNext)
      except StopIteration: pass
    timeouts = [timeout(n_sec, showNext)]
    return timeouts

class SwitchCall:
  def __init__(self, op, op1):
    self.flag = False
    self.op, self.op1 = op, op1
  def __call__(self):
    self.op() if self.flag else self.op1()
    self.flag = not self.flag
