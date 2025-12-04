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