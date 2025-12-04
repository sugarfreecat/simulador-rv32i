class Registradores:
  def __init__(self):
    self.reg = [0] * 32

  def read(self, x):
    return self.reg[x]

  def write(self, x, val):
    if x != 0:
      self.reg[x] = val & 0xFFFFFFFF