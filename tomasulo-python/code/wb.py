# Qing 
# 29th May 2017 

'''
1. broadcast data on cdb 
2. fetch data from results queue 
3. remove entry in results queue

'''
from init import cdb as make_cdb
from print_status import add_stall
# function: find ROB entry by tag
def find_ROB_entry(ROB, tag):
    for index in range(len(ROB)):
        if ROB[index].ROB_tag == tag:
            break
    return index

# function: boroadcast
# rat_int, rat_fp, reservation stations, ld_sd_queue, ROB
def boroadcast(cdb, rat_int, rat_fp, 
                rs_int_adder, rs_fp_adder, rs_fp_multi,
                ld_sd_queue, ROB, cycle):
    # dest_tag
    dest_tag = cdb.dest_tag
    index = find_ROB_entry(ROB, dest_tag)
    reg_tag = ROB[index].dest_tag
    # rat keeps the value only while this instruction still owns the rename
    if isinstance(reg_tag, str) and reg_tag[:1] == 'R' and rat_int[int(reg_tag[1:])] == dest_tag:
        rat_int[int(reg_tag[1:])] = cdb.value
    if isinstance(reg_tag, str) and reg_tag[:1] == 'F' and rat_fp[int(reg_tag[1:])] == dest_tag:
        rat_fp[int(reg_tag[1:])] = cdb.value 
    # rs list
    rs_list = [rs_int_adder, rs_fp_adder, rs_fp_multi]
    for rs in rs_list:
        for element in rs:
            if (element.tag_1st==dest_tag)&(element.valid_1st==0):
                element.value_1st = cdb.value
                element.valid_1st = 1
            if (element.tag_2nd==dest_tag)&(element.valid_2nd==0):
                element.value_2nd = cdb.value
                element.valid_2nd = 1
    # ld_sd_queue 
    for element in ld_sd_queue:
        if (element.data==dest_tag)&(element.op=='Sd'):
            element.data = cdb.value
        if (element.reg_tag==dest_tag)&(element.valid==0):
            element.reg_value = cdb.value
            element.valid = 1
    # ROB
    for element in ROB:
        if element.ROB_tag == dest_tag:
            element.value = cdb.value
            element.cdb.append(cycle)

# function: wb 
def wb(rat_int, rat_fp, 
        rs_int_adder, rs_fp_adder, rs_fp_multi,
        ld_sd_queue, ROB, cycle,
        results_buffer, pending, width):
    # broadcast results latched last cycle; latching a new result is the normal one-cycle bus delay
    for _ in range(min(width, len(pending))):
        boroadcast(pending.popleft(), rat_int, rat_fp, 
                    rs_int_adder, rs_fp_adder, rs_fp_multi,
                    ld_sd_queue, ROB, cycle)
    latched = 0
    while latched < width and len(results_buffer) > 0:
        slot = make_cdb()
        slot.valid = 1
        slot.value = results_buffer[0].value
        slot.dest_tag = results_buffer[0].dest_tag
        results_buffer.popleft()
        pending.append(slot)
        latched += 1
    for item in results_buffer:
        # The result is ready now and can first write back next cycle.
        add_stall(ROB, item.dest_tag, 'bus busy', cycle + 1)

