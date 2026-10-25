# Qing 
# 26th May 2017

''' 
1. Ld forward check from Sd in ld_sd_queue
    -- only check nearest Sd instruction
2. execute LD/SD instruction in ld_sd_mem
    -- once LD instruction gets data, write back to ld_sd_queue
    -- LD instruction should be removed after get data  
    -- SD instruction should be removed at commit stage 
3. fetch new LD/SD instruction into ld_sd_mem
    -- if first element is SD, ready and has valid data, only SD to be committed can be fetched into ld_sd_mem 
    -- else put the first no-matched Ld into ld_sd_mem    
'''
from init import fu_result
from print_status import add_stall

# function: forward check from sd
# only check nearest sd
def forward_check_from_sd(ld_sd_queue, index):
    data = []
    for i in reversed(range(index)):
        if (ld_sd_queue[i].op=='Sd'):
            if (ld_sd_queue[i].address == ld_sd_queue[index].address):
                if (type(ld_sd_queue[i].data)==int)|(type(ld_sd_queue[i].data)==float):
                    data.append(ld_sd_queue[i].data)
            break
    return data

# function: check if previous all Sds are ready and un-matched
def check_all_previous_Sd_no_match(ld_sd_queue, index):
    flag = True
    for i in range(index):
        # all Sd instructions
        if (ld_sd_queue[i].op=='Sd'):
            if ld_sd_queue[i].ready == 0:
                flag = False
                break 
            elif (ld_sd_queue[i].address==ld_sd_queue[index].address):
                flag = False
                break
            else:
                pass
    return flag
 
# function: find ROB entry by tag
def find_ROB_entry(ROB, tag):
    for index in range(len(ROB)):
        if ROB[index].ROB_tag == tag:
            break
    return index

# function: put entry into ld_sd_mem
def put_entry_into_ld_sd_mem(ld_sd_mem, entry):
    ld_sd_mem.busy = 1
    ld_sd_mem.cycle = 0
    ld_sd_mem.address = entry.address
    ld_sd_mem.dest_tag = entry.dest_tag
    ld_sd_mem.op = entry.op
    if ld_sd_mem.op == 'Sd':
        ld_sd_mem.data = entry.data

# function: check if Sd to be committed in next cycle 
def check_if_sd_committable(ld_sd_queue, ROB):
    flag = False
    if ld_sd_queue[0].ldsd_tag == ROB[0].dest_tag:
        flag = True
    if ld_sd_queue[0].ldsd_tag == ROB[1].dest_tag:
        # previous ins has been broadcasted
        if len(ROB[0].cdb)!=0:
            flag = True
    return flag

# Entries the starter would send to memory, head store first.
# A ready head store hides the loads behind it, matching the original fetch.
def ready_mem(ld_sd_queue):
    if len(ld_sd_queue)==0:
        return []
    head = ld_sd_queue[0]
    if (head.op=='Sd') and (head.ready==1) and check_if_sd_committable:
        if (type(head.data)==int)|(type(head.data)==float):
            return [head]
    ready = []
    for index in range(len(ld_sd_queue)):
        element = ld_sd_queue[index]
        if (element.op=='Ld')&(element.ready==1):
            if (type(head.data)!=int)&(type(head.data)!=float):
                if check_all_previous_Sd_no_match(ld_sd_queue, index):
                    ready.append(element)
    return ready

def advance_mem_unit(unit, time_ld_sd_mem, results_buffer, memory, ROB, cycle):
    if unit.busy != 1:
        return
    if unit.cycle == 0:
        index = find_ROB_entry(ROB, unit.dest_tag)
        ROB[index].mem.extend([cycle, cycle+time_ld_sd_mem-1])
        if unit.op == 'Sd':
            ROB[index].commit.append(cycle)
    unit.cycle += 1
    if unit.cycle == time_ld_sd_mem:
        unit.busy = 0
        if unit.op == 'Ld':
            address = unit.address
            data = memory[address]
            results_buffer.append(fu_result())
            results_buffer[-1].value = data
            results_buffer[-1].dest_tag = unit.dest_tag
        else:
            memory[unit.address] = unit.data

# function: mem 
def mem(ld_sd_queue, mem_units, time_ld_sd_mem, results_buffer, 
        memory, ROB, cycle):
    '''look forward check for all Ld instructions'''
    index = -1
    remove_list = []
    for element in ld_sd_queue:
        index += 1
        if (index>=1)&(element.op=='Ld')&(element.ready==1):
            data = forward_check_from_sd(ld_sd_queue, index)
            if len(data)>0:
                # Ld gets data 
                results_buffer.append(fu_result())
                results_buffer[-1].value = data[0]
                results_buffer[-1].dest_tag = element.dest_tag
                # remove the Ld instruction
                remove_list.append(element)
                # write mem cylce in ROB
                index = find_ROB_entry(ROB, element.dest_tag)
                ROB[index].mem.append(cycle)
    # remove lookforwared Ld
    for element in remove_list:
        ld_sd_queue.remove(element)
    for unit in mem_units:
        advance_mem_unit(unit, time_ld_sd_mem, results_buffer, memory, ROB, cycle)
    for unit in mem_units:
        if unit.busy == 1:
            continue
        ready = ready_mem(ld_sd_queue)
        if len(ready)==0:
            break
        ld_sd_queue.remove(ready[0])
        put_entry_into_ld_sd_mem(unit, ready[0])
    if len(mem_units)>0 and all(unit.busy==1 for unit in mem_units):
        for entry in ready_mem(ld_sd_queue):
            add_stall(ROB, entry.dest_tag, 'no load/store unit', cycle) 

