from tkinter import Frame, PanedWindow, LEFT, TOP, RIGHT, BOTTOM, Label, Button, Entry, Text, INSERT, END
from tkinter import Radiobutton, Checkbutton, Listbox, BROWSE, Scrollbar, Scale, Spinbox
from tkinter import LabelFrame, Menu, Menubutton, Canvas
from tkinter import Tk, Toplevel, X, Y, BOTH, FLAT, RAISED, HORIZONTAL, VERTICAL
from tkinter import StringVar, BooleanVar, IntVar, DoubleVar
from tkinter import Widget as TkWidget
from functools import wraps
from typing import NamedTuple

from .tkgui_utils import EventCallback, EventPoller, useTheme

from tkinter.ttk import Style, Progressbar, Combobox, Sizegrip, Notebook, Treeview
if useTheme: from tkinter.ttk import * # TTK support

'''
This is a declarative wrapper for Python's tkinter GUI layout support.
Common knowledges on Tk:
- there's three layout managers: pack(box-layout), grid, posit(absolute)
- in pack there's three common property: master(parent), side(gravity), fill(size-match-parent), expand(able-to-change)
- packing order is useful: e.g. you have a full-size listBox with yScrollBar, then pack scrollBar first
- use keyword arg(k=v) in constructor or item.configure(k=v)/item[k]=v for widget setup
- Tk should be singleton, use Toplevel for a new window
- Parallelism: Tk cannot gurantee widgets can be updated correctly from other threads, set event loop [Tk.after] instead
Notice:
- this lib uses [widget] decorator to make first arg(parent) *curried*(as first arg in returned lambda)
- two main Box layout (VBox, HBox) .appendChild can accept (curried widget ctor)/widget-value/(widget list ctor)
- use .childs for children list of a layout, since .children is a Tk property
- use shorthand: _ = self.underscore
- spinBox&slider: range(start, stop) is end-exclusive, so 1..100 represented as range(1,100+1)
- rewrite layout&setup (do setXXX setup or bind [TkGUI.connect] listener) and call run(title) to start GUI application

MenuItems: OpNamed(named), SubMenu, Sep(sep), CheckBox, RadioButton
Widgets(button/bar/line/box): button, radioButton, menuButton; scrollBar, progressBar; slider, text;
  (string:)input, textarea, (number:)spinBox, (listing:)listBox, comboBox;
  menu, separator, fill, canvas, treeWidget
Containers: HBox(horizontalLayout), VBox(verticalLayout); labeledBox, splitter, tabWidget

Aux funs:
- _.fill(widget) can make a widget(.e) packed at specified side/fill
- _.var(type) can create a Tk value storage
- _.by(name, widget) can dynamic set widget as self.name attribute

Features adopted from Teek:
- init_threads to add a global event poller from threads (but this lib is not globally thread safe :( )
- make textarea marks from float to (line,col)
- remove Widget.after&after_cancel, use Timeout objects with global creator

TODO:
- Adopt Font, Color, Pen/Palette objects
- Adopt Image, ScreenDistance, Varaible (maybe, but _.by is enough?)
- Adopt Extras: Links for Textarea, and tooltips for all widgets
- Adopt: collapse, withScroll, withDoubleScroll, Box with scrollBar
'''

def mayGive1(value, op_obj):
  '''creates a [widget]. If TkGUI switch to use DSL tree-data construct, this dynamic-type trick can be removed'''
  return op_obj(value) if callable(op_obj) else op_obj

ignorableWidgetOptions = []

from re import search
from _tkinter import TclError

def widget(op):
  '''make a "create" with kwargs configuration = lambda parent: '''
  def curry(*args, **kwargs):
    kwargs1 = kwargs
    def create(p):
      try: return op(p, *args, **kwargs1)
      except TclError as e:
        mch = search("""unknown option "-([^"]+)"$""", str(e))
        if mch != None:
          opt = mch.groups()[0]
          if opt in ignorableWidgetOptions: # dirty hack for tk/ttk configure compat
            del kwargs1[opt]; return create(p)
        raise e
    return create
  return curry

def nop(*arg): pass

class MenuItem:
  def __init__(self, name):
    self.name = name
class MenuItem:
  class OpNamed(MenuItem):
    def __init__(self, name, op):
      super().__init__(name); self.op = op
  @staticmethod
  def named(name, op): return MenuItem.OpNamed(name, op)
  class SubMenu(MenuItem):
    def __init__(self, name, childs):
      super().__init__(name); self.childs = childs
  class Sep(MenuItem):
    def __init__(self): super().__init__("|")
  sep = Sep()
  class CheckBox(MenuItem):
    def __init__(self, name, dst):
      super().__init__(name); self.dst=dst
  class RadioButton(MenuItem):
    def __init__(self, name, dst, value):
      super().__init__(name); self.dst,self.value = dst,value

class Textarea(Text):
  def __init__(self, master=None, **kwargs):
    super().__init__(master=master, **kwargs)
    self.marker = Textarea.MarkerPos(self)
  class LineCol(NamedTuple("LineCol", [("line", int), ("col", int)])): #v text indexes comparing inherited.
    def __repr__(self): return f"LineCol({self.line}:{self.col})"

  class MarkerPos:
    def __init__(self, outter):
      self._outter = outter
    def coerceInBounds(self, index):
      o = self._outter
      if index < o.start: return o.start
      if index > o.end: return o.end
      return index
    def stepFrom(self, loc, chars=0, indices=0, lines=0):
      code = "%d.%d %+d lines %+d chars %+d indices" % (loc.line, loc.col, lines, chars, indices)
      return self.coerceInBounds(self[code])

    def __getitem__(self, name) -> "Textarea.LineCol":
      (line, col) = map(int, self._outter.index(name).split("."))
      return Textarea.LineCol(line, col)
    def __setitem__(self, name, pos):
      self._outter.mark_set(name, "%i.%i" %(pos.line, pos.col))
    def __delitem__(self, name):
      self._outter.mark_unset(name)

  @property
  def start(self): return Textarea.LineCol(1, 0)
  @property
  def end(self): return self.marker["end - 1 char"]

class TreeWidget(Treeview):
  def makeTree(self, tree):
    '''[tree] is a (tuple name, childs for nested) str list'''
    def insert(nd, src):
      self.insert(nd, END, src, text=str(src))
    def insertRec(nd, src):
      if isinstance(src, tuple):
        (name, childs) = src
        self.insert(nd, END, name, text=name)
        for it in childs: insertRec(name, it)
      elif isinstance(src, list):
        for it in src: insertRec(nd, it)
      else: insert(nd, src)
    insertRec("", tree)
  def moveTo(self, dst, nd):
    self.move(nd, dst, END)

class BaseTkGUI:
  def __init__(self, root):
    self.tk:Toplevel = root
    self.ui:TkWidget = None #>layout
    self.style:Style = Style(self.tk)
  def layout(self) -> "Widget":
    '''
    (FAILED since Python has NO overriding) I'm sorry about adding so many kwargs, but Python is not real OOP (just obj.op_getter property-based),
    there's no name can be implicitly(w/o "self") solved in scope -- inner class, classmethod, staticmethod, property, normal defs
    so only global/param/local can be used without boilerplates, I've choosen keyword args.
    '''
    raise NotImplementedError("main layout")
  def setup(self): pass

  def var(self, type, initial=None, var_map = {str: StringVar, bool: BooleanVar, int: IntVar, float: DoubleVar}):
    variable = var_map[type](self.tk)
    if initial != None: variable.set(initial)
    return variable
  def by(self, attr, e_ctor):
    def createAssign(p):
      e = mayGive1(p, e_ctor)
      self.__setattr__(attr, e); return e
    return createAssign
  @property
  def underscore(self) -> "BaseTkGUI": return self

  def run(self, title):
    self.tk.wm_deiconify()
    self.tk.wm_title(title)
    self.ui = mayGive1(self.tk, self.layout())
    self.ui.pack()
    self.setup()
    self.focus(); self.tk.mainloop()
  @property
  def title(self) -> str: return self.tk.wm_title()
  @title.setter
  def title(self, v): self.tk.wm_title(v)
  @property
  def size(self) -> tuple: return self.tk.wm_minsize()
  def setSize(self, dim:tuple): self.tk.wm_minsize(dim[0], dim[1])
  def setSizeMax(self, dim:tuple): self.tk.wm_maxsize(dim[0], dim[1])
  def setGeometry(self, dim, xy=None):
    code = "x".join(str(i) for i in dim)
    if xy != None: code += "+%d+%d" %(xy[0],xy[1])
    self.tk.wm_geometry()
  def setWindowAttributes(self, attrs): self.tk.wm_attributes(*attrs)
  @property
  def screenSize(self):
    return (self.tk.winfo_screenwidth(), self.tk.winfo_screenheight() )
  def focus(self): self.tk.focus_set()
  def listThemes(self): return self.style.theme_names()
  @property
  def theme(self): return self.style.theme_use()
  @theme.setter
  def theme(self, v): return self.style.theme_use(v)
  def addSizeGrip(self):
    Sizegrip(self.ui).pack(side=RIGHT)

  class Widget:
    def pack(self): pass
    def forget(self): pass
    def destroy(self): pass
  class Box(Frame, Widget):
    def __init__(self, parent, pad, is_vertical):
      super().__init__(parent)
      self.childs = []
      self.pad,self.is_vertical = pad,is_vertical
    def pack(self, **kwargs):
      super().pack(**kwargs)
      if len(self.childs) == 0: return
      self.childs[0].pack(side=(TOP if self.is_vertical else LEFT) )
      for it in self.childs[1:]: self._appendChild(it)
    def destroy(self):
      for it in self.childs: self.removeChild(it)

    def _appendChild(self, e):
      if self.is_vertical: e.pack(side=TOP, fill=Y, pady=self.pad)
      else: e.pack(side=LEFT, fill=X, padx=self.pad)
    def appendChild(self, e_ctor):
      e = mayGive1(self, e_ctor)
      if isinstance(e, list):
        for it in e: self._appendChild(it)
        self.childs.extend(e)
      else:
        self._appendChild(e)
        self.childs.append(e)
    def removeChild(self, e):
      e.forget()
      try: e.destory()
      except AttributeError: pass
      self.childs.remove(e)
    @property
    def firstChild(self): return self.childs[0]
    @property
    def lastChild(self): return self.childs[-1]
  class HBox(Box):
    def __init__(self, parent, pad=3):
      super().__init__(parent, pad, False)
  class VBox(Box):
    def __init__(self, parent, pad=5):
      super().__init__(parent, pad, True)

  class SeparatorFrame(Frame):
    def __init__(self, parent, text, fill, *args, **kwargs):
      self.text,self.fill = text,fill
      super().__init__(parent, *args, **kwargs)
    def pack(self, *args, **kwargs):
      if self.text != None: Label(self, text=self.text).pack()
      del kwargs["fill"]
      super().pack(*args, fill=self.fill, expand=(self.fill == BOTH), **kwargs)
  class PackSideFill(Widget):
    def __init__(self, e, side, fill):
        super().__init__()
        self.e,self.side,self.fill = e,side,fill
    def pack(self, *args, **kwargs):
      kwargs.update({"side": self.side or kwargs.get("side"), "fill": self.fill, "expand": self.fill == BOTH})
      self.e.pack(*args, **kwargs)
    def forget(self): return self.e.forget()
    def destroy(self): return self.e.destroy()

  @staticmethod
  def _createLayout(ctor_box, p, items):
    box = ctor_box(p)
    box.childs = list(mayGive1(box, it) for it in items)
    return box
  @staticmethod
  def verticalLayout(*items): return lambda p: TkGUI._createLayout(TkGUI.VBox, p, items)
  @staticmethod
  def horizontalLayout(*items): return lambda p: TkGUI._createLayout(TkGUI.HBox, p, items)

  @staticmethod
  @widget
  def menu(p, *items, use_default_select = False):
    e_menu = Menu(p, tearoff=use_default_select)
    for it in items:
      if isinstance(it, MenuItem.OpNamed):
        e_menu.add_command(label=it.name, command=it.op)
      elif isinstance(it, MenuItem.SubMenu):
        child = TkGUI.menu(*it.childs, use_default_select)(e_menu)
        e_menu.add_cascade(label=it.name, menu=child)
      elif isinstance(it, MenuItem.Sep): e_menu.add_separator()
      elif isinstance(it, MenuItem.CheckBox): e_menu.add_checkbutton(label=it.name, variable=it.dst)
      elif isinstance(it, MenuItem.RadioButton): e_menu.add_radiobutton(label=it.name, variable=it.dst, value=it.value)
    return e_menu
  def setMenu(self, menu_ctor):
    self.tk["menu"] = menu_ctor(self.tk)
  def makeMenuPopup(self, menu_ctor):
    menu = mayGive1(self.tk, menu_ctor)
    def popup(event):
      try: menu.tk_popup(event.x_root, event.y_root) 
      finally: menu.grab_release()
    return popup

  @staticmethod #^ layouts v button/bar/slider/box
  @widget
  def text(p, valr, **kwargs):
    kwargs["textvariable" if isinstance(valr, StringVar) else "text"] = valr
    return Label(p, **kwargs)
  @staticmethod
  @widget
  def textarea(p, placeholder=None, **kwargs):
    text = Textarea(p, **kwargs)
    if placeholder != None: text.insert(INSERT, placeholder)
    return text
  @staticmethod
  @widget
  def button(p, text, on_click, **kwargs):
    return Button(p, text=text, command=on_click, **kwargs)
  @staticmethod
  @widget
  def radioButton(p, text, dst, value, on_click=nop):
    return Radiobutton(p, text=text, variable=dst, value=value, command=on_click)
  @staticmethod
  @widget
  def menuButton(p, text, menu_ctor, **kwargs):
    menub = Menubutton(p, text=text, **kwargs)
    menub["menu"] = mayGive1(menub, menu_ctor)
    return menub
  @staticmethod
  @widget
  def input(p, placeholder="", **kwargs):
    ent = Entry(p, **kwargs)
    ent.delete(0, END)
    ent.insert(0, placeholder)
    return ent
  @staticmethod
  @widget
  def spinBox(p, range:range, **kwargs):
    if range.step != 1: return Spinbox(p, values=tuple(range), **kwargs)
    else: return Spinbox(p, from_=range.start, to=range.stop-1, **kwargs)
  @staticmethod
  @widget
  def slider(p, range:range, **kwargs):
    if not useTheme: kwargs["resolution"] = range.step
    return Scale(p, from_=range.start, to=range.stop-1, **kwargs)
  @staticmethod
  @widget
  def checkBox(p, text_valr, dst, a=True, b=False, on_click=nop):
    '''make [text_valr] and [dst] points to same if you want to change text when checked'''
    valr = text_valr
    return Checkbutton(p, **{"textvariable" if isinstance(valr, StringVar) else "text": valr}, 
      variable=dst, onvalue=a, offvalue=b, command=nop)
  @staticmethod
  @widget
  def listBox(p, items, mode=BROWSE, **kwargs):
    lbox = Listbox(p, selectmode=mode, **kwargs)
    for (i, it) in enumerate(items): lbox.insert(i, it)
    return lbox
  @staticmethod
  @widget
  def comboBox(p, items):
    cbox = Combobox(p)
    for (i, it) in enumerate(items): cbox.insert(i, it)
    return cbox
  @staticmethod
  @widget
  def scrollBar(p, orient=VERTICAL):
    return TkGUI.PackSideFill(Scrollbar(p, orient=orient), None, Y if orient==VERTICAL else X)
  @staticmethod
  @widget
  def progressBar(p, dst, orient=HORIZONTAL):
    return Progressbar(p, variable=dst, orient=orient)

  @staticmethod
  @widget
  def labeledBox(p, text, *items, **kwargs):
    lbox = TkGUI.PackSideFill(LabelFrame(p, text=text, **kwargs), None, BOTH)
    for it in items: mayGive1(lbox.e, it).pack()
    return lbox
  @staticmethod
  @widget
  def separator(p, text=None, fill=X, height=2, bg="white", relief=FLAT):
    extras = {} if useTheme else {"bg":bg, "bd":1}
    return TkGUI.SeparatorFrame(p, text, fill, height=height, relief=relief, **extras)
  @staticmethod
  @widget
  def splitter(p, orient, *items, **kwargs):
    paned_win = PanedWindow(p, orient=orient, **kwargs)
    for it in items: paned_win.add(mayGive1(paned_win, it))
    return paned_win
  @staticmethod
  @widget
  def tabWidget(p, *entries):
    '''you may want tabs to fill whole window, use [fill].'''
    tab = Notebook(p)
    for (name, e_ctor) in entries:
      e = mayGive1(tab, e_ctor)
      if isinstance(e, BaseTkGUI.Box): e.pack() # in tabs, should pack early
      tab.add(e, text=name)
    return tab
  @staticmethod
  @widget
  def fill(p, e_ctor, fill=BOTH, side=None):
    return TkGUI.PackSideFill(mayGive1(p, e_ctor), side, fill)
  @staticmethod
  @widget
  def canvas(p, dim, **kwargs):
    (width,height) = dim
    return Canvas(p, width=width, height=height, **kwargs)
  @staticmethod
  @widget
  def treeWidget(p):
    treev = TreeWidget(p)
    return treev

  hor = HORIZONTAL
  vert = VERTICAL
  left,top,right,bottom = LEFT,TOP,RIGHT,BOTTOM
  raised,flat=RAISED,FLAT
  at_cursor,at_end=INSERT,END

  class Event:
    click = "<Button-1>"
    doubleClick = "<Double 1>"
    mouseM = "<Button-2>"
    mouseR = "<Button-3>"
    key = "<Key>"
    enter = "<Enter>"; leave = "<Leave>"

  @staticmethod
  def connect(sender, signal, receiver, slot):
    ''' connects a command from [sender] to notify [receiver].[slot], or call slot(sender, receiver, *signal_args) '''
    def runProc(*arg, **kwargs):
      return slot(sender, receiver, *arg, **kwargs)
    listen = receiver.__getattribute__(slot) if not callable(slot) else runProc
    sender[signal+"command"] = listen
  @staticmethod
  def bindScrollBarY(_, b, _1, v, *args): b.yview_moveto(v)
  @staticmethod
  def bindScrollBarX(_, b, _1, v, *args): b.xview_moveto(v)

  @staticmethod
  def bindYScrollBar(box, bar):
    TkGUI.connect(box, "yscroll", bar.e, "set")
    TkGUI.connect(bar.e, "", box, TkGUI.bindScrollBarY)
  @staticmethod
  def bindXScrollBar(box, bar):
    TkGUI.connect(box, "xscroll", bar.e, "set")
    TkGUI.connect(bar.e, "", box, TkGUI.bindScrollBarX)

class TkGUI(BaseTkGUI, EventPoller):
  root:"TkGUI" = None
  def __init__(self):
    if TkGUI.root != None: raise RuntimeError("TkGUI is singleton, should not created twice")
    super().__init__(Tk())
    self.on_quit = EventCallback()
    EventPoller.__init__(self)
    TkGUI.root = self
    self.tk.bind("<Destroy>", lambda _: self.on_quit.run())
  def quit(self):
    self.tk.destroy()

class TkWin(BaseTkGUI):
  def __init__(self):
    super().__init__(Toplevel(TkGUI.root.tk))

def callThreadSafe(op, args=(), kwargs={}):
  return TkGUI.root.callThreadSafe(op, args, kwargs)

def makeThreadSafe(op):
  '''
  A decorator that makes a function safe to be called from any thread, (and it runs in the main thread).
  If you have a function runs a lot of Tk update and will be called asynchronous, better decorate with this (also it will be faster)
  [op] should not block the main event loop.
  '''
  @wraps(op)
  def safe(*args, **kwargs):
    return callThreadSafe(op, args, kwargs)
  return safe

class Timeout:
  def __init__(self, after_what, op):
    assert TkGUI.root != None, "TkGUI not initialized"
    self.op = op
    self._id = TkGUI.root.tk.after(after_what, op)

  def cancel(self):
    """Prevent this timeout from running as scheduled."""
    TkGUI.root.tk.after_cancel(self._id) # race condition?


def runAsync(thunk, op, **kwargs):
  '''launch the [thunk], then call [op] safely with args, return thunk() result'''
  future = lambda res: callThreadSafe(op, (res,), kwargs)
  return thunk(future)

def thunkify(op, kw_callback="callback", *args, **kwargs):
  '''make a function with named callback param as thunk'''
  def addCb(cb, kws):
    kws[kw_callback] = cb
    return kws
  return lambda cb: op(*args, **addCb(kwargs, cb))

from threading import Thread
def thunkifySync(op, *args, **kwargs):
  def callAsync(cb):
    Thread(target=lambda args1, kwargs1: cb(op(*args1, **kwargs1)), args=(args, kwargs) ).start()
  return callAsync

from time import sleep
def delay(msec):
  sleep(msec/1000)
  return lambda cb: cb(msec)
