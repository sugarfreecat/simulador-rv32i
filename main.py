from Memoria import Memoria
from Barramento import Barramento
from CPU import CPU

# Inicializa a memoria, barramento e CPU
memoria = Memoria(640 * 1024)
barramento = Barramento(memoria)
cpu = CPU(barramento)

# Guarda o numero a ser calculado na memoria
cpu.barramento.write32(1024, 10)

# Instruções para calcular o quadrado de um número
instrucoes = [
    0x40002283, #lw x5, 1024(x0)
    0x00000313, #addi x6, x0, 0
    0x00028393, #addi x7, x5, 0
    0x00038863, #beq x7, x0, 16
    0x00530333, #add x6, x6, x5
    0xFFF38393, #addi x7, x7, -1
    0xff5ff06f, #jal x0, -12
    0x00030513, #addi x10, x6, 0
    0x0          # HALT / fim
]

# Carrega as instrucoes na memoria
for i in range(len(instrucoes)):
  cpu.barramento.write32(i * 4, instrucoes[i])

# Inicia a CPU
cpu.iniciarCPU()

# Imprime o resultado (armazenado no registrador x10)
print(f"Resultado: {cpu.regs.read(10)}")