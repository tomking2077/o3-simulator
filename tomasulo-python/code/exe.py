# Qing 
# 24th May 2017

''' 
1. calculate valid instructions
    -- for ALU instructions, write results into fu_results, remove that fu entry  
    -- for LD/SD, write address result immediately back to ld_sd_queue
2. fetch instructions into function unit with spare space
    -- remove ALU instructions from rs
    -- don't remove ld/sd instructions
'''
from init import fu_entry, fu_result
from print_status import add_stall

# function: check rs and return valid instruction index
def check_valid_ins_in_rs(rs):
    index = -1
    if len(rs)!=0:
        for i in range(len(rs)):
            if (rs[i].valid_1st==1)&(rs[i].valid_2nd==1)&(rs[i].busy==1):
                index = i
                break
    return index

# function: check ld_sd_queue and return valid instruction index
def check_valid_ins_in_ldsd(ldsd, skip=()):
    index = -1
    if len(ldsd)!=0:
        for i in range(len(ldsd)):
            if (ldsd[i].valid==1) & (ldsd[i].ready==0) & (ldsd[i].ld_sd_tag not in skip):
                index = i
                break
    return index

# function: add entry into fu 
def add_entry_into_fu(fu, ins_in_rs):
    fu[-1].cycle = 0
    fu[-1].op = ins_in_rs.op
    fu[-1].value1 = ins_in_rs.value_1st
    fu[-1].value2 = ins_in_rs.value_2nd
    fu[-1].dest_tag = ins_in_rs.dest_tag

# function: find ROB entry by tag
def find_ROB_entry(ROB, tag):
    for index in range(len(ROB)):
        if ROB[index].ROB_tag == tag:
            break
    return index

def record_exe_start(ROB, tag, cycle):
    ROB[find_ROB_entry(ROB, tag)].exe.append(cycle)

def finish_fu_entry(element, fu_results, ROB, cycle, PC):
    index = find_ROB_entry(ROB, element.dest_tag)
    ROB[index].exe.append(cycle)
    if element.op in ('Bne', 'Beq'):
        return
    fu_results.append(fu_result())
    fu_results[-1].dest_tag = element.dest_tag
    if (element.op=='Add')|(element.op=='Add.d')|(element.op=='Addi'):
        fu_results[-1].value = element.value1 + element.value2
    elif (element.op=='Sub')|(element.op=='Sub.d'):
        fu_results[-1].value = element.value1 - element.value2
    elif element.op=='Mult.d':
        fu_results[-1].value = element.value1 * element.value2

def age_entry(element, ROB, cycle):
    element.cycle += 1
    if element.cycle == 1:
        record_exe_start(ROB, element.dest_tag, cycle)

# function: functional units execution. One advance per cycle; every finished head leaves.
def fu_exe(fu, fu_results, ROB, time_fu, cycle, PC):
    if len(fu)==0:
        return
    for element in fu:
        age_entry(element, ROB, cycle)
    while len(fu)!=0 and fu[0].cycle == time_fu:
        finish_fu_entry(fu[0], fu_results, ROB, cycle, PC)
        fu.popleft()

# Age only the instruction that just entered, so older work is not advanced twice.
def advance_new(fu, element, fu_results, ROB, time_fu, cycle, PC):
    age_entry(element, ROB, cycle)
    if element.cycle == time_fu:
        finish_fu_entry(element, fu_results, ROB, cycle, PC)
        fu.remove(element)

# function: ld_sd_execution 
def ld_sd_execution(ld_sd_exe, time_ld_sd_exe, ld_sd_queue, ROB, cycle):
    if ld_sd_exe.busy == 1:
        # write down starting cycle
        if ld_sd_exe.cycle == 0:            
            for element in ld_sd_queue:
                if element.ld_sd_tag == ld_sd_exe.dest_tag:
                    break
            index = find_ROB_entry(ROB, element.dest_tag)
            ROB[index].exe.append(cycle)
            # execute 
            ld_sd_exe.cycle += 1
        # write address back to ld_sd_queue
        if ld_sd_exe.cycle == time_ld_sd_exe:
            address = ld_sd_exe.value1 + ld_sd_exe.value2
            for element in ld_sd_queue:
                if element.ld_sd_tag == ld_sd_exe.dest_tag:
                    element.address = address
                    element.ready = 1
                    break
            # write down finish cycle
            index = find_ROB_entry(ROB, element.dest_tag)
            ROB[index].exe.append(cycle)
            ld_sd_exe.busy = 0

def dispatch_alu(fu, rs, slots, note, time_fu, results_buffer, ROB, cycle, PC):
    started = 0
    while started < slots:
        index = check_valid_ins_in_rs(rs)
        if index < 0:
            break
        fu.append(fu_entry())
        add_entry_into_fu(fu, rs[index])
        issued = ROB[find_ROB_entry(ROB, rs[index].dest_tag)].issue[0]
        if issued < cycle:
            advance_new(fu, fu[-1], results_buffer, ROB, time_fu, cycle, PC)
        rs[index].busy = 0
        started += 1
    for entry in rs:
        if (entry.busy==1) & (entry.valid_1st==1) & (entry.valid_2nd==1):
            add_stall(ROB, entry.dest_tag, note, cycle)

def dispatch_address(address_units, time_ld_sd_exe, ld_sd_queue, ROB, cycle):
    busy_tags = set()
    for unit in address_units:
        if unit.busy == 0:
            continue
        busy_tags.add(unit.dest_tag)
    for unit in address_units:
        if unit.busy == 1:
            continue
        index = check_valid_ins_in_ldsd(ld_sd_queue, busy_tags)
        if index < 0:
            break
        unit.busy = 1
        unit.cycle = 0
        unit.value1 = ld_sd_queue[index].reg_value
        unit.value2 = ld_sd_queue[index].immediate
        unit.dest_tag = ld_sd_queue[index].ld_sd_tag
        busy_tags.add(unit.dest_tag)
        issued = ROB[find_ROB_entry(ROB, ld_sd_queue[index].dest_tag)].issue[0]
        if issued < cycle:
            ld_sd_execution(unit, time_ld_sd_exe, ld_sd_queue, ROB, cycle)
    for element in ld_sd_queue:
        if (element.valid==1) & (element.ready==0) & (element.ld_sd_tag not in busy_tags):
            add_stall(ROB, element.dest_tag, 'no load/store unit', cycle)

# function: execution
def exe(fu_int_adder, time_fu_int_adder,
        fu_fp_adder, time_fu_fp_adder,
        fu_fp_multi, time_fu_fp_multi, results_buffer,
        rs_int_adder, rs_fp_adder, rs_fp_multi, 
        address_units, time_ld_sd_exe, ld_sd_queue,
        cycle, ROB, PC, n_int, n_fp_add, n_fp_mul):
    '''execution in fu and ld_sd address calculation'''
    for unit in address_units:
        ld_sd_execution(unit, time_ld_sd_exe, ld_sd_queue, ROB, cycle)
    # functional units 
    fu_exe(fu_int_adder, results_buffer, ROB, time_fu_int_adder, cycle, PC)
    fu_exe(fu_fp_adder, results_buffer, ROB, time_fu_fp_adder, cycle, PC)
    fu_exe(fu_fp_multi, results_buffer, ROB, time_fu_fp_multi, cycle, PC)
    '''fetch instructions from rs and ld_sd_queue'''
    dispatch_address(address_units, time_ld_sd_exe, ld_sd_queue, ROB, cycle)
    # integer adder is unpipelined: a busy unit is not free
    dispatch_alu(fu_int_adder, rs_int_adder, max(0, n_int - len(fu_int_adder)),
                 'no integer adder', time_fu_int_adder, results_buffer, ROB, cycle, PC)
    # fp units are pipelined: each unit accepts one new instruction every cycle
    dispatch_alu(fu_fp_adder, rs_fp_adder, n_fp_add,
                 'no fp adder', time_fu_fp_adder, results_buffer, ROB, cycle, PC)
    dispatch_alu(fu_fp_multi, rs_fp_multi, n_fp_mul,
                 'no fp multiplier', time_fu_fp_multi, results_buffer, ROB, cycle, PC)

