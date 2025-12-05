import ctypes

class Memoria:
  def __init__(self, size):
    self.size = size
    
    # Divisao da memoria
    
    #Dados e instrucoes 
    self.data = (ctypes.c_ubyte * size)()
    
    #Memoria de video
    self.vram = bytearray(0x10000)      # 0x80000 – 0x8FFFF
    
    #Area reservada para os perifericos
    self.perifericos = [0] * 256        # 1 KB -> 0x9FC00 – 0x9FFFF

  def regiao(self, end):
    if 0x00000 <= end <= 0x7FFFF:
      return ("ram", end)

    elif 0x80000 <= end <= 0x8FFFF:
      return ("vram", end - 0x80000)

    elif 0x90000 <= end <= 0x9FBFF:
      return ("reservado", end - 0x90000)

    elif 0x9FC00 <= end <= 0x9FFFF:
      return ("periferico", (end - 0x9FC00) // 4)

    else:
      raise IndexError("Endereço fora da memória")

  def read(self, end):
    reg, idx = self.regiao(end)

    if reg == "ram":
      return self.data[idx]

    elif reg == "vram":
      return self.vram[idx]

    elif reg == "reservado":
      return 0

    elif reg == "periferico":
      return self.perifericos[idx]

  def write(self, end, valor):
    reg, idx = self.regiao(end)

    if reg == "ram":
      self.data[idx] = valor & 0xFF #Mascara de bits

    elif reg == "vram":
      self.vram[idx] = valor & 0xFF

    elif reg == "reservado":
      pass

    elif reg == "periferico":
      self.perifericos[idx] = valor & 0xFF

  def read16(self, end):
    if end + 1 >= self.size:
      raise IndexError("Endereço fora da memória")
    
    valor = 0b0
    for i in range(2):
      valor |= self.read(end + i) << (8 * i)
    return valor

  def read32(self, end):
    if end + 3 >= self.size:
      raise IndexError("Endereço fora da memória")
    
    valor = 0b0
    for i in range(4):
      valor |= self.read(end + i) << (8 * i)
    return valor
  
  def write16(self, end, valor):
    if end + 1 >= self.size:
      raise IndexError("Endereço fora da memória")
    for i in range(2):
      self.write(end + i, (valor >> (i * 8)) & 0xFF)

  def write32(self, end, valor):
    if end + 3 >= self.size:
      raise IndexError("Endereço fora da memória")
    for i in range (4):
      self.write(end + i, (valor >> (i * 8)) & 0xFF)