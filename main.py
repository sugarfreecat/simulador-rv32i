import ctypes

class Memoria:
  def __init__(self, size):
    self.data = (ctypes.c_ubyte * size)()
    self.size = size
    self.vram = bytearray(0x10000)      # 0x80000 – 0x8FFFF
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
        self.data[idx] = valor & 0xFF

    elif reg == "vram":
        self.vram[idx] = valor & 0xFF

    elif reg == "reservado":
        pass

    elif reg == "periferico":
        self.perifericos[idx] = valor & 0xFF

  def read16(self, end):
    if end + 1 >= self.size:
        raise IndexError("Endereço fora da memória")
    return self.data[end] | (self.data[end+1] << 8)

  def read32(self, end):
    if end + 3 >= self.size:
        raise IndexError("Endereço fora da memória")
    return self.data[end] | (self.data[end+1] << 8) | (self.data[end+2] << 16) | (self.data[end+3] << 24)

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


class Registradores:
  def __init__(self):
    self.reg = [0] * 32

  def read(self, x):
    return self.reg[x]

  def write(self, x, val):
    if x != 0:
      self.reg[x] = val & 0xFFFFFFFF

# class Barramento:
class Barramento:
    def __init__(self, memoria):
        self.mem = memoria
        self.address = 0       # barramento de endereços
        self.data = 0          # barramento de dados
        self.control = "IDLE"  # barramento de controle: READ, WRITE, IDLE

    def read32(self, address):
        self.address = address
        self.control = "READ"
        self.data = self.mem.read32(address)
        self.control = "IDLE"
        return self.data

    def read16(self, address):
        self.address = address
        self.control = "READ"
        self.data = self.mem.read16(address)
        self.control = "IDLE"
        return self.data

    def read(self, address):
        self.address = address
        self.control = "READ"
        self.data = self.mem.read(address)
        self.control = "IDLE"
        return self.data

    def write32(self, address, value):
        self.address = address
        self.data = value & 0xFFFFFFFF
        self.control = "WRITE"
        self.mem.write32(address, self.data)
        self.control = "IDLE"

    def write16(self, address, value):
        self.address = address
        self.data = value & 0xFFFFFFFF
        self.control = "WRITE"
        self.mem.write16(address, self.data)
        self.control = "IDLE"

    def write(self, address, value):
        self.address = address
        self.data = value & 0xFFFFFFFF
        self.control = "WRITE"
        self.mem.write(address, self.data)
        self.control = "IDLE"

class CPU:
  def __init__(self, barramento):
    self.barramento = barramento
    self.regs = Registradores()
    self.pc = 0

    #Escrita na VRAM
    self.countInst = 0
    self.intervaloSaida = 30
    self.inicioVRAM = 0x80000
    self.fimVRAM = 0x8FFFF

  def lerInstrucao(self):
    return self.barramento.read32(self.pc)

  def sign(self, x):
    return x if x < 0x80000000 else x - 0x100000000

  # DECODIFICADOR
  # -------------------------------------------------------------------
  def decodificarInstrucao(self, inst):
    opcode = inst & 0b1111111

    # TIPO R
    if opcode == 0b0110011:
      return {
          "type": "R",
          "opcode": opcode,
          "rd": (inst >> 7) & 0b11111,
          "funct3": (inst >> 12) & 0b111,
          "rs1": (inst >> 15) & 0b11111,
          "rs2": (inst >> 20) & 0b11111,
          "funct7": (inst >> 25) & 0b1111111
      }

    # TIPO I | TIPO I-SHIFT
    elif opcode in (0b0010011, 0b1100111, 0b0000011):
      funct3 = (inst >> 12) & 0b111
      if funct3 in (0b001, 0b101) and opcode == 0b0010011:  # SLLI, SRLI, SRAI
          return {
              "type": "I",
              "subtype": "shift",
              "opcode": opcode,
              "rd": (inst >> 7) & 0b11111,
              "funct3": funct3,
              "rs1": (inst >> 15) & 0b11111,
              "shamt": (inst >> 20) & 0b11111,
              "funct7": (inst >> 25) & 0b1111111
          }
      else:
          imm = (inst >> 20) & 0xFFF
          if imm & 0x800:
              imm -= 0x1000

          return {
              "type": "I",
              "subtype": "",
              "opcode": opcode,
              "rd": (inst >> 7) & 0b11111,
              "funct3": funct3,
              "rs1": (inst >> 15) & 0b11111,
              "imm": imm
          }

    # TIPO S
    elif opcode == 0b0100011:
      imm = (((inst >> 25) & 0b1111111) << 5) | ((inst >> 7) & 0b11111)

      if imm & 0x800:
        imm -= 0x1000

      return {
          "type": "S",
          "opcode": opcode,
          "funct3": (inst >> 12) & 0b111,
          "rs1": (inst >> 15) & 0b11111,
          "rs2": (inst >> 20) & 0b11111,
          "imm": imm
      }

    # TIPO B
    elif opcode == 0b1100011:
      imm12 = (inst >> 31) & 0b1        # bit 31
      imm11 = (inst >> 7)  & 0b1        # bit 7
      imm10_5 = (inst >> 25) & 0b111111 # bits 30–25
      imm4_1 = (inst >> 8)  & 0b1111    # bits 11–8

      imm = (imm12 << 12) | (imm11 << 11) | (imm10_5 << 5) | (imm4_1 << 1)

      if imm & (1 << 12):
        imm -= 1 << 13

      return {
          "type": "B",
          "opcode": opcode,
          "funct3": (inst >> 12) & 0b111,
          "rs1": (inst >> 15) & 0b11111,
          "rs2": (inst >> 20) & 0b11111,
          "imm": imm
      }

    # TIPO U
    elif opcode in (0b0110111, 0b0010111):  # LUI, AUIPC
      imm = inst & 0xFFFFF00

      # sign extend (caso bit 31 seja 1)
      if imm & 0x80000000:
        imm -= 0x100000000

      return {
          "type": "U",
          "opcode": opcode,
          "rd": (inst >> 7) & 0b11111,
          "imm": imm
      }

    # TIPO J
    elif opcode == 0b1101111:
      rd = (inst >> 7) & 0x1F

      imm20 = (inst >> 31) & 0x1
      imm10_1 = (inst >> 21) & 0x3FF
      imm11 = (inst >> 20) & 0x1
      imm19_12 = (inst >> 12) & 0xFF

      imm = (imm20 << 20) | (imm19_12 << 12) | (imm11 << 11) | (imm10_1 << 1)

      # Sign extend 21-bit immediate
      if imm20 == 1:
          imm |= ~((1 << 21) - 1)

      return {
          "type": "J",
          "opcode": opcode,
          "rd": rd,
          "imm": imm
      }

    # SYSTEM
    elif opcode == 0b1110011:
      return {
          "type": "SYSTEM",
          "opcode": opcode,
          "inst": inst
      }

  # INSTRUÇÔES
  # -------------------------------------------------------------------
  def executarInstrucao(self, instDecodificada):
    print(instDecodificada)

    # TIPO R
    #---------------------------------------------------------------------
    if instDecodificada["type"]== "R":
      rs1 = self.regs.read(instDecodificada["rs1"])
      rs2 = self.regs.read(instDecodificada["rs2"])
      rd = instDecodificada["rd"]
      funct3 = instDecodificada["funct3"]
      funct7 = instDecodificada["funct7"]

      #ADD
      if funct3 == 0b000 and funct7 == 0b0000000:
        resultado = (rs1 + rs2) & 0xFFFFFFFF

      #SUB
      elif funct3 == 0b000 and funct7 == 0b0100000:
        resultado = (rs1 - rs2) & 0xFFFFFFFF

      #SLL
      elif funct3 == 0b001:
        resultado = (rs1 << (rs2 & 0x1F)) & 0xFFFFFFFF

      #SLT
      elif funct3 == 0b010:
        s1 = (rs1 ^ 0x80000000) - 0x80000000
        s2 = (rs2 ^ 0x80000000) - 0x80000000
        resultado = 1 if s1 < s2 else 0

      #SLTU
      elif funct3 == 0b011:
        resultado = 1 if (rs1 & 0xFFFFFFFF) < (rs2 & 0xFFFFFFFF) else 0

      #XOR
      elif funct3 == 0b100:
        resultado = (rs1 ^ rs2) & 0xFFFFFFFF

      #SRL
      elif funct3 == 0b101 and funct7 == 0b0000000:
        resultado = (rs1 >> (rs2 & 0b11111)) & 0xFFFFFFFF

      #SRA
      elif funct3 == 0b101 and funct7 == 0b0100000:
        s1 = (rs1 ^ 0x80000000) - 0x80000000
        resultado = (s1 >> (rs2 & 0x1F)) & 0xFFFFFFFF

      #OR
      elif funct3 == 0b110:
        resultado = (rs1 | rs2) & 0xFFFFFFFF

      #AND
      elif funct3 == 0b111:
        resultado = (rs1 & rs2) & 0xFFFFFFFF

      else:
        raise Exception("Instrução R-type não reconhecida")

      self.regs.write(rd, resultado)

    # TIPO I
    #---------------------------------------------------------------------
    elif instDecodificada["type"]== "I":
      subtype = instDecodificada["subtype"]
      opcode =  instDecodificada["opcode"]
      rd = instDecodificada["rd"]
      funct3 = instDecodificada["funct3"]
      rs1 = self.regs.read(instDecodificada["rs1"])

      if subtype == "shift":
        shamt = instDecodificada["shamt"]
        funct7 = instDecodificada["funct7"]

        #SLLI
        if funct3 == 0b001:
          resultado = (rs1 << shamt) & 0xFFFFFFFF

        #SRLI
        elif funct3 == 0b101 and funct7 == 0b0000000:
          resultado = (rs1 & 0xFFFFFFFF) >> shamt

        #SRAI
        elif funct3 == 0b101 and funct7 == 0b0100000:
          rs1_signed = ctypes.c_int32(rs1).value  # garante 32 bits signed
          resultado = rs1_signed >> shamt
          resultado &= 0xFFFFFFFF

      else:
        imm = instDecodificada["imm"]

        #JALR
        if opcode == 0b1100111:
          next_pc = self.pc + 4
          target = (rs1 + imm) & ~1     # zera o bit 0
          self.regs.write(rd, next_pc)
          self.pc = target
          return True

        elif opcode == 0b0000011:

          address = rs1 + imm

          #LB
          if funct3 == 0b000:
            resultado = self.barramento.read(address)
            if resultado & 0x80:
              resultado -= 0x100

          #LH
          elif funct3 == 0b001:
            resultado = self.barramento.read16(address)
            if resultado & 0x8000:
              resultado -= 0x10000

          #LW
          elif funct3 == 0b010:
            resultado = self.barramento.read32(address)

          #LBU
          elif funct3 == 0b100:
            resultado = self.barramento.read(address) & 0xFF

          #LHU
          elif funct3 == 0b101:
            resultado = self.barramento.read16(address) & 0xFFFF

        elif opcode == 0b0010011:
          #ADDI
          if funct3 == 0b000:
            resultado = rs1 + imm

          #SLTI
          elif funct3 == 0b010:
            resultado = 1 if rs1 < imm else 0

          #SLTIU
          elif funct3 == 0b011:
            rs1_u = rs1 & 0xFFFFFFFF
            imm_u = imm & 0xFFFFFFFF
            resultado = 1 if rs1_u < imm_u else 0

          #XORI
          elif funct3 == 0b100:
            resultado = rs1 ^ imm

          #ORI
          elif funct3 == 0b110:
            resultado = rs1 | imm

          #ANDI
          elif funct3 == 0b111:
            resultado = rs1 & imm

      resultado &= 0xFFFFFFFF
      self.regs.write(rd, resultado)

    # TIPO S
    #---------------------------------------------------------------------
    elif instDecodificada["type"]== "S":
      rs1 = self.regs.read(instDecodificada["rs1"])
      rs2 = self.regs.read(instDecodificada["rs2"])
      funct3 = instDecodificada["funct3"]
      imm = instDecodificada["imm"]

      # sign extend de 12 bits
      if imm & 0x800:
          imm -= 0x1000

      address = rs1 + imm

      #SB
      if funct3 == 0b000:
        self.barramento.write(address, rs2 & 0xFF)

      #SH
      elif funct3 == 0b001:
        self.barramento.write16(address, rs2 & 0xFFFF)

      #SW
      elif funct3 == 0b010:
        self.barramento.write32(address, rs2 & 0xFFFFFFFF)

    # TIPO B
    #---------------------------------------------------------------------
    elif instDecodificada["type"]== "B":
      rs1 = self.regs.read(instDecodificada["rs1"])
      rs2 = self.regs.read(instDecodificada["rs2"])
      funct3 = instDecodificada["funct3"]
      imm = instDecodificada["imm"]

      # BEQ
      if funct3 == 0b000:
        if rs1 == rs2:
          self.pc += imm
          return True

      # BNE
      elif funct3 == 0b001:
        if rs1 != rs2:
          self.pc += imm
          return True

      # BLT
      elif funct3 == 0b100:
        if self.sign(rs1) < self.sign(rs2):
          self.pc += imm
          return True

      # BGE
      elif funct3 == 0b101:
        if self.sign(rs1) >= self.sign(rs2):
          self.pc += imm
          return True

      # BLTU
      elif funct3 == 0b110:
        if (rs1 & 0xFFFFFFFF) < (rs2 & 0xFFFFFFFF):
          self.pc += imm
          return True

      # BGEU
      elif funct3 == 0b111:
        if (rs1 & 0xFFFFFFFF) >= (rs2 & 0xFFFFFFFF):
          self.pc += imm
          return True

    # TIPO U
    #---------------------------------------------------------------------
    elif instDecodificada["type"]== "U":
      rd = instDecodificada["rd"]
      imm = instDecodificada["imm"] # verificar se isso ja acontece no decodificador
      opcode = instDecodificada["opcode"]

      # LUI
      if opcode == 0b0110111:
        self.regs.write(rd, imm)

      # AUIPC
      if opcode == 0b0010111:
        self.regs.write(rd, self.pc + imm)

    # TIPO J
    #---------------------------------------------------------------------
    elif instDecodificada["type"] == "J":
      rd = instDecodificada["rd"]
      imm = instDecodificada["imm"]
      opcode = instDecodificada["opcode"]

      # JAL
      if opcode == 0b1101111:
        next_pc = self.pc + 4
        self.regs.write(rd, next_pc)
        self.pc = self.pc + imm
        return True

    # TIPO SYSTEM
    #---------------------------------------------------------------------
    elif instDecodificada["type"] == "SYSTEM":
      inst = instDecodificada["inst"]

      # ECALL
      if inst == 0x00000073:
          print("ECALL chamada")
          raise Exception("ECALL - finalizando execução")

      # EBREAK
      elif inst == 0x00100073:
          print("EBREAK chamada")
          raise Exception("EBREAK - breakpoint")

      else:
          print(f"Instrucao SYSTEM desconhecida: 0x{inst:08x}")

    if(not(instDecodificada["type"] in ["J", "B", "SYSTEM"])):
      print(f"Resultado dessa operacao: {self.regs.read(rd)}\n")

    return False

  def passo(self):
    if self.pc + 3 >= self.barramento.mem.size:
        return 0

    inst = self.lerInstrucao()

    if (inst == 0):
      return 0

    instDecodificada = self.decodificarInstrucao(inst)
    mudou_pc = self.executarInstrucao(instDecodificada)

    if (not mudou_pc):
      self.pc += 4

    self.countInst += 1

    if (self.countInst % self.intervaloSaida) == 0:
      self.printVRAM()

    return 1

  def printVRAM(self):
    print("\n===== VRAM =====")

    for addr in range(self.inicioVRAM, self.inicioVRAM + 1):
        val = self.barramento.read32(addr)
        char = chr(val) if 32 <= val <= 126 else "."  # ASCII
        print(char)

    print("\n================\n")

  def iniciarCPU(self):
    count = 0
    while True:
      continuar = self.passo()
      count += 1
      if (not continuar):
        break
      
# Inicializa a memoria, barramento e CPU
memoria = Memoria(640 * 1024)
barramento = Barramento(memoria)
cpu = CPU(barramento)

# Instruções para calcular o quadrado de um número
instrucoes = [
    0x00000313, #addi x6, x0, 0
    0x00028393, #addi x7, x5, 0
    0x00038863, #beq x7, x0, 16
    0x00530333, #add x6, x6, x5
    0xFFF38393, #addi x7, x7, -1
    0xff5ff06f, #jal x0, -12
    0x00030513, #addi x10, x6, 0
    0x0          # HALT / fim
]

# Registrador que guarda o numero a ser calculado
cpu.regs.write(5, 4)

# Carrega as instrucoes na memoria
for i in range(len(instrucoes)):
  cpu.barramento.write32(i * 4, instrucoes[i])

# Inicia a CPU
cpu.iniciarCPU()

# Imprime o resultado (armazenado no registrador x10)
print(f"Resultado: {cpu.regs.read(10)}")