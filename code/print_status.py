# Qing 
# 21st May 2017

# function: print RS/ROB status
def ps(unit):
    if(len(unit)==0):
        print('empty!')
    else:
        # get all fields in namedtuple
        fields_list = unit[0]._fields
        for unit_item in unit:
            print ('******')
            for field in fields_list:
                print(field+': ', str(getattr(unit_item, field)))

# function: print single namedtuple
def pss(snt):
    fields_list = snt._fields
    for field in fields_list:
        print (field+': ', str(getattr(snt, field)))

def note_stall(stalls, note, cycle):
    for item in stalls:
        if item[0] == note:
            if cycle not in item[1]:
                item[1].append(cycle)
            return
    stalls.append([note, [cycle]])

def add_stall(ROB, tag, note, cycle):
    for entry in ROB:
        if entry.ROB_tag == tag:
            note_stall(entry.stalls, note, cycle)
            return

def format_stalls(stalls):
    parts = []
    for note, cycles in stalls:
        parts.append(note + ' ' + format_spans(cycles))
    return ', '.join(parts)

def format_spans(cycles):
    spans = []
    start = prev = cycles[0]
    for cycle in cycles[1:]:
        if cycle == prev + 1:
            prev = cycle
            continue
        spans.append(format_span(start, prev))
        start = prev = cycle
    spans.append(format_span(start, prev))
    return ' '.join(spans)

def format_span(start, end):
    if start == end:
        return '[' + str(start) + ']'
    return '[' + str(start) + '-' + str(end) + ']'

def print_regs(prefix, regs):
    names = ''
    values = ''
    for i, value in enumerate(regs):
        names += (prefix + str(i)).ljust(8)
        values += str(value).ljust(8)
        if (i + 1) % 8 == 0:
            print(names)
            print(values)
            names = ''
            values = ''

def print_arch_state(reg_int, reg_fp, memory):
    print('\nREGISTER VALUES\n')
    print_regs('R', reg_int)
    print_regs('F', reg_fp)
    print('\nNON-ZERO MEMORY VALUES\n')
    print('Addresses'.ljust(12) + 'Values')
    for addr, value in enumerate(memory):
        if value != 0:
            print(str(addr).ljust(12) + str(value))

