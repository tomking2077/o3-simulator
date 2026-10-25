# Qing 
# 21st May 2017 

import sys
from copy import deepcopy
from collections import deque
from init import parse_input, build_rs, ld_sd_exe, ld_sd_mem, PC
from print_status import print_arch_state, note_stall
from issue import issue
from exe import exe 
from mem import mem
from wb import wb 
from commit import commit

def make_units(factory, n):
    units = []
    for _ in range(n):
        unit = factory()
        unit.busy = 0
        units.append(unit)
    return units

def clamp_width(text):
    width = int(text)
    if width < 1:
        return 1
    if width > 4:
        return 4
    return width

'''initialize'''
cfg = parse_input(sys.argv[1] if len(sys.argv) > 1 else 'code.in')
if len(sys.argv) > 2:
    cfg.issue_width = clamp_width(sys.argv[2])
instructions = cfg.instructions
reg_int = cfg.reg_int
rat_int = deepcopy(reg_int)
reg_fp = cfg.reg_fp
rat_fp = deepcopy(reg_fp)
memory = cfg.memory
'''intialize reservation stations'''
rs_int_adder = build_rs(cfg.rs['int'])
rs_fp_adder = build_rs(cfg.rs['fp_add'])
rs_fp_multi = build_rs(cfg.rs['fp_mul'])
'''initilize function unit'''
fu_int_adder = deque()
time_fu_int_adder = cfg.ex['int']
fu_fp_adder = deque()
time_fu_fp_adder = cfg.ex['fp_add']
fu_fp_multi = deque()
time_fu_fp_multi = cfg.ex['fp_mul']
'''initialize load/store queue'''
ld_sd_queue = deque()
size_ld_sd_queue = cfg.rs['lsq']
time_ld_sd_exe = cfg.ex['lsq']
time_ld_sd_mem = cfg.mem_lat['lsq']
address_units = make_units(ld_sd_exe, cfg.fus['lsq'])
mem_units = make_units(ld_sd_mem, cfg.fus['lsq'])
'''initialize ROB'''
ROB = deque()
size_ROB = cfg.rob
'''initialize CDB'''
results_buffer = deque()
cdb_pending = deque()
width = cfg.issue_width
"""issue first instruction"""
# instruction pointer 
PC = PC()
PC.PC = 0
PC.valid = 1 
cycle = 1

# print title 
item = 'Insn'.ljust(6)
item += ''.ljust(30)
item += 'ISSUE'.ljust(15)
item += 'EXE'.ljust(15)
item += 'MEM'.ljust(15)
item += 'WB'.ljust(15)
item += 'COMMIT'.ljust(15)
item += 'COMMENTS'
print (item)

pending_stalls = []
# main. A store can leave the ROB when it enters memory and still be writing.
while (len(ROB)>0) or (cycle==1) or any(unit.busy==1 for unit in mem_units):
    
    '''ISSUE stage'''
    issued = 0
    while (issued<width) and (PC.PC<len(instructions)) and (PC.valid==1):
        before = (PC.PC, PC.valid)
        note = issue(cycle, PC, instructions, ROB, size_ROB, 
                rs_int_adder, 
                rs_fp_adder, 
                rs_fp_multi, 
                ld_sd_queue, size_ld_sd_queue, 
                rat_int, rat_fp)
        if (PC.PC, PC.valid)==before:
            if note:
                note_stall(pending_stalls, note, cycle)
            break
        for item_note, stalled_cycles in pending_stalls:
            for stalled in stalled_cycles:
                note_stall(ROB[-1].stalls, item_note, stalled)
        pending_stalls = []
        issued += 1

    '''EXE stage'''
    exe(fu_int_adder, time_fu_int_adder, 
        fu_fp_adder, time_fu_fp_adder, 
        fu_fp_multi, time_fu_fp_multi, results_buffer,  
        rs_int_adder, rs_fp_adder, rs_fp_multi, 
        address_units, time_ld_sd_exe, ld_sd_queue,
        cycle, ROB, PC, cfg.fus['int'], cfg.fus['fp_add'], cfg.fus['fp_mul'])

    '''MEM stage'''
    mem(ld_sd_queue, mem_units, time_ld_sd_mem, results_buffer,
        memory, ROB, cycle)

    '''CDB stage'''
    wb(rat_int, rat_fp, 
        rs_int_adder, rs_fp_adder, rs_fp_multi,
        ld_sd_queue, ROB, cycle,
        results_buffer, cdb_pending, width) 
    
    '''COMMIT stage'''
    commit(ROB, reg_int, reg_fp, cycle, instructions, width)
    
    # cycle number 
    cycle +=1

print_arch_state(reg_int, reg_fp, memory)
