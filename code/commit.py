# Qing 
# 29th may 2017
'''
1. commit ROB_buffer
2. fetch header into ROB_buffer
'''

from print_status import format_stalls

# function: print ROB entry 
def print_ROB(entry, instructions):
    item = str(entry.PC + 1).ljust(6)
    item += instructions[entry.PC].ljust(30)
    item += str(entry.issue).ljust(15) 
    item += str(entry.exe).ljust(15) 
    item += str(entry.mem).ljust(15)
    item += str(entry.cdb).ljust(15)
    item += str(entry.commit).ljust(15)
    item += format_stalls(getattr(entry, 'stalls', []) or [])
    print(item)
# function: modify architectual reg
def modify_arch_reg(entry, reg_int, reg_fp):
    if entry.dest_tag[0] == 'F':
        reg_fp[int(entry.dest_tag[1:])] = entry.value
    elif entry.dest_tag[0] == 'R':
        reg_int[int(entry.dest_tag[1:])] = entry.value
    else:
        pass

# function: commit
def commit(ROB, reg_int, reg_fp, cycle, instructions, width):
    retired = 0
    while retired < width and len(ROB) > 0:
        op = instructions[ROB[0].PC].split(' ')[0]
        if op in ('Bne', 'Beq'):
            if len(ROB[0].exe) == 0:
                break
            print_ROB(ROB.popleft(), instructions)
        elif len(ROB[0].cdb) != 0:
            ROB[0].commit.append(cycle+1)
            entry = ROB.popleft()
            modify_arch_reg(entry, reg_int, reg_fp)
            print_ROB(entry, instructions)
        elif len(ROB[0].commit) != 0:
            print_ROB(ROB.popleft(), instructions)
        else:
            break
        retired += 1
