# Qing 
# 21st May 2017 

import re
from collections import namedtuple

'''define data types'''
# reservation station 
def rs_entry():
    rs_entry = namedtuple('rs_entry', 'busy, op, tag_1st, value_1st, valid_1st, tag_2nd, value_2nd, valid_2nd, dest_tag')
    temp = rs_entry
    return temp 
# functional unit 
def fu_entry():
    fu_entry = namedtuple('fu_entry', 'cycle, op, value1, value2, dest_tag')
    temp = fu_entry
    return temp
# function result 
def fu_result():
    fu_result = namedtuple('fu_result', 'value, dest_tag')
    temp = fu_result
    return temp
# ld/sd entry
def ld_sd_entry():
    ld_sd_entry = namedtuple('ld_sd_entry', 'ld_sd_tag, ready, op, address, data, dest_tag, immediate, reg_tag, reg_value, valid')
    temp = ld_sd_entry
    return temp
# ld/sd exe
def ld_sd_exe():
    ld_sd_exe = namedtuple('ld_sd_exe', 'busy, cycle, value1, value2, dest_tag')
    temp = ld_sd_exe
    return temp
# ld/sd mem
def ld_sd_mem():
    ld_sd_mem = namedtuple('ld_sd_mem', 'busy, cycle, op, data, address, dest_tag')
    temp = ld_sd_mem
    return temp
# cdb
def cdb():
    cdb = namedtuple('cdb', 'valid, value, dest_tag')
    temp = cdb
    return temp
# ROB_entry 
def ROB_entry():
    ROB_entry = namedtuple('ROB_entry', 'ROB_tag, PC, value, dest_tag, issue, exe, mem, cdb, commit')
    temp = ROB_entry
    temp.issue = []
    temp.exe = []
    temp.mem = []
    temp.cdb = []
    temp.commit =[]
    temp.stalls = []
    return temp
# PC 
def PC():
    PC = namedtuple('PC', 'PC, valid')
    temp = PC
    return temp
_OPS = {
    'ld': 'Ld', 'sd': 'Sd', 'add': 'Add', 'addi': 'Addi', 'sub': 'Sub',
    'add.d': 'Add.d', 'sub.d': 'Sub.d', 'mult.d': 'Mult.d', 'beq': 'Beq', 'bne': 'Bne',
}
_UNITS = (
    ('integer adder', 'int'),
    ('fp adder', 'fp_add'),
    ('fp multiplier', 'fp_mul'),
    ('load/store unit', 'lsq'),
)
_SCALAR = (
    (re.compile(r'rob entries\s*=\s*(\d+)'), 'rob'),
)
_REG = re.compile(r'([RFrf])(\d+)\s*=\s*([+-]?\d+(?:\.\d+)?)')
_MEM = re.compile(r'[Mm]em\[(\d+)\]\s*=\s*([+-]?\d+(?:\.\d+)?)')

def _number(text):
    return float(text) if '.' in text else int(text)

def _scalar(lowered):
    for pattern, attr in _SCALAR:
        hit = pattern.search(lowered)
        if hit:
            return attr, int(hit.group(1))
    return None

class Program:
    def __init__(self):
        self.rs = {'int': 4, 'fp_add': 3, 'fp_mul': 2, 'lsq': 5}
        self.ex = {'int': 1, 'fp_add': 4, 'fp_mul': 15, 'lsq': 1}
        self.mem_lat = {'lsq': 5}
        self.fus = {'int': 1, 'fp_add': 1, 'fp_mul': 1, 'lsq': 1}
        self.rob = 64
        self.issue_width = 1
        self.reg_int = [0] * 32
        self.reg_fp = [0] * 32
        self.memory = [0] * 256
        self.instructions = []

def _legacy_state(prog):
    prog.reg_int[1] = 12
    prog.reg_int[2] = 32
    prog.reg_fp[20] = 3.0
    for addr, val in ((4, 3.0), (8, 2.0), (12, 1.0), (24, 6.0), (28, 5.0), (32, 4.0)):
        prog.memory[addr] = val

def parse_input(codefile):
    with open(codefile) as f:
        lines = f.read().splitlines()
    prog = Program()
    saw_config = False
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        lowered = line.lower()
        unit = next((key for name, key in _UNITS if lowered.startswith(name)), None)
        if unit:
            nums = [int(n) for n in re.findall(r'\d+', line)]
            prog.rs[unit], prog.ex[unit] = nums[0], nums[1]
            if len(nums) == 4:
                prog.mem_lat[unit], prog.fus[unit] = nums[2], nums[3]
            else:
                prog.fus[unit] = nums[2]
            saw_config = True
            continue
        scalar = _scalar(lowered)
        if scalar:
            setattr(prog, scalar[0], scalar[1])
            saw_config = True
            continue
        regs, mems = _REG.findall(line), _MEM.findall(line)
        if regs or mems:
            for kind, idx, val in regs:
                bank = prog.reg_fp if kind.upper() == 'F' else prog.reg_int
                bank[int(idx)] = _number(val)
            for addr, val in mems:
                prog.memory[int(addr)] = _number(val)
            saw_config = True
            continue
        parts = line.replace(',', ' ').split()
        op = _OPS.get(parts[0].lower())
        if op:
            prog.instructions.append(' '.join([op] + parts[1:]))
    if not saw_config:
        _legacy_state(prog)
    return prog

# function: build rs
def build_rs(num):
    rs = []
    for _ in range(num):
        temp = rs_entry()
        temp.busy = 0
        rs.extend([temp])
    return rs
