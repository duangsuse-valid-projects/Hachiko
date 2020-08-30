from tkinter import Frame, PanedWindow, LEFT, TOP, RIGHT, BOTTOM, Label, Button, Entry, Text, INSERT, END
from tkinter import Radiobutton, Checkbutton, Listbox, BROWSE, Scrollbar, Scale, Spinbox
from tkinter import LabelFrame, Menu, Menubutton, Canvas
from tkinter import Tk, Toplevel, X, Y, BOTH, FLAT, RAISED, HORIZONTAL, VERTICAL
from tkinter import StringVar, BooleanVar, IntVar, DoubleVar

'''
This is a declarative wrapper for Python's tkinter support
Common knowledges on Tk:
- there's three layout manager: pack(box-layout), grid, posit(absolute)
- in pack there's three common property: master(parent), side(gravity), fill(size-match-parent), expand(able-to-change)
- use keyword arg(k=v) in constructor or item.configure(k=v)/item[k]=v for widget setup
- Tk should be singleton, use Toplevel for new window
Notice:
- this lib uses [widget] decorator to make first arg(parent) *curried*(as first arg in returned lambda)
- use shorthand: _ = self.underscore ; and _.var(type) can make Tk value storage ; _.by(name, widget) can dynamic set widget attribute
- spinBox&slider: range(start, stop) is end-exclusive, so 1..100 represented as range(1,100+1)
- rewrite layout/setup (do setXXX setup or bind [connect] listener) and call run(title) to start GUI application
'''

def mayGive1(value, op_obj):
  return op_obj(value) if callable(op_obj) else op_obj

def widget(op):
  def create(*args, **kwargs):
    return lambda p: op(p, *args, **kwargs)
  return create

def nop(*arg): pass

class MenuItem:
  def __init__(self, name):
    self.name = name
class MenuItem:
  class SubMenu(MenuItem):
    def __init__(self, name, childs):
      super().__init__(name); self.childs = childs
  class OpNamed(MenuItem):
    def __init__(self, name, op):
      super().__init__(name); self.op = op
  @staticmethod
  def named(name, op): return MenuItem.OpNamed(name, op)
  class Sep(MenuItem):
    def __init__(self): super().__init__("|")
  sep = Sep()
  class CheckBox(MenuItem):
    def __init__(self, name, dst):
      super().__init__(name); self.dst=dst
  class RadioButton(MenuItem):
    def __init__(self, name, dst, value):
      super().__init__(name); self.dst,self.value = dst,value

class TkGUI:
  def __init__(self, is_root = True):
    self.tk = Tk() if is_root else Toplevel()
    self.ui = None #>layout
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
      e = e_ctor(p)
      self.__setattr__(attr, e); return e
    return createAssign
  @property
  def underscore(self) -> "TkGUI": return self

  def run(self, title):
    self.tk.wm_deiconify()
    self.tk.wm_title(title)
    self.ui = mayGive1(self.tk, self.layout())
    self.ui.pack()
    self.setup()
    self.focus(); self.tk.mainloop()
  def setSize(self, dim): self.tk.wm_minsize(dim[0], dim[1])
  def setWindowAttributes(self, attrs): self.tk.wm_attributes(*attrs)
  def focus(self): self.tk.focus_set()

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
    def __init__(self, text, fill, *args, **kwargs):
      self.text,self.fill = text,fill
      super().__init__(*args, **kwargs)
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

  @staticmethod #^ layouts v button/bar/slider/box
  @widget
  def text(p, valr, **kwargs):
    kwargs["textvariable" if isinstance(valr, StringVar) else "text"] = valr
    return Label(p, **kwargs)
  @staticmethod
  @widget
  def textarea(p, placeholder=None, **kwargs):
    text = Text(p, **kwargs)
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
    menub["menu"] = menu_ctor(menub)
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
  def spinBox(p, value_range, **kwargs):
    return Spinbox(p, from_=value_range.start, to=value_range.stop-1, **kwargs)
  @staticmethod
  @widget
  def slider(p, value_range, **kwargs):
    return Scale(p, from_=value_range.start, to=value_range.stop-1, resolution=value_range.step, **kwargs)
  @staticmethod
  @widget
  def checkBox(p, text, dst, a=True, b=False):
    return Checkbutton(p, text=text, variable=dst, onvalue=a, offvalue=b)
  @staticmethod
  @widget
  def listBox(p, items, mode=BROWSE, **kwargs):
    lbox = Listbox(p, selectmode=mode, **kwargs)
    for (i, it) in enumerate(items): lbox.insert(i, it)
    return lbox
  @staticmethod
  @widget
  def scrollBar(p, orient=VERTICAL):
    return TkGUI.PackSideFill(Scrollbar(p, orient=orient), None, Y if orient==VERTICAL else X)

  @staticmethod
  @widget
  def labeledBox(p, text=None, *items, **kwargs):
    lbox = TkGUI.PackSideFill(LabelFrame(p, text=text, **kwargs), None, BOTH)
    for it in items: mayGive1(lbox.e, it).pack()
    return lbox
  @staticmethod
  @widget
  def separator(p, text=None, fill=X, height=2, bg="white", relief=FLAT):
    return TkGUI.SeparatorFrame(text, fill, p, height=height, bg=bg, bd=1, relief=relief)
  @staticmethod
  @widget
  def splitter(p, orient, *items, **kwargs):
    paned_win = PanedWindow(p, orient=orient, **kwargs)
    for it in items: paned_win.add(mayGive1(paned_win, it))
    return paned_win
  @staticmethod
  @widget
  def fill(p, e_ctor, fill=BOTH, side=None):
    return TkGUI.PackSideFill(e_ctor(p), side, fill)
  @staticmethod
  @widget
  def canvas(p, dim, **kwargs):
    (width,height) = dim
    return Canvas(p, width=width, height=height, **kwargs)

  hor = HORIZONTAL
  vert = VERTICAL
  left,top,right,bottom = LEFT,TOP,RIGHT,BOTTOM
  raised,flat=RAISED,FLAT

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

class TkWin(TkGUI):
  def __init__(self):
    super().__init__(False)
