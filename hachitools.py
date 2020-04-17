from threading import Timer

def grayColor(n): return (n,n,n)

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