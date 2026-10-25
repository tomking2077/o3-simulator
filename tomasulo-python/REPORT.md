# Tomasulo multi-issue

The starter already ran a single-issue Tomasulo pipeline. The additions below follow one cycle, in the order the simulator runs that cycle. Each rule lives in one place and is used by every instruction that needs it.

## Read the machine from the input

`parse_input` reads the input file in one pass. The file sets the reservation-station counts, the functional-unit counts, the execute and memory latencies, the ROB size, and the initial registers and memory. Issue width is the optional second command-line argument and is clamped to 1–4. Omitting it uses width 1. A file that contains only instructions still loads, using the starter’s default machine. `Bne` and `Beq` are ordinary opcodes in that same table.

## Issue up to the width, in order

Each cycle issues at most `issue_width` instructions, in program order, and stops at the first one that cannot issue. That width is also the writeback width and the commit width.

A load or store still needs a load/store queue entry. An integer operation or a branch still needs an integer reservation station. A floating-point add and a multiply still need their own stations. The operand placement for each of those is unchanged. The ending is shared: `station_stall` returns `no reservation station` when the station or the queue is full, and returns nothing when the only limit is the ROB. A full station blocks that instruction and everything behind it for the cycle. The station stays occupied until the operation is dispatched.

## Start as many ready operations as there are free units

`dispatch_alu` starts ready reservation-station entries for the integer adder, the floating-point adder, and the floating-point multiplier. The number started is the number of free units of that type, counted once at the start of the cycle. A unit that finishes later in the same cycle is not refilled.

The floating-point units are pipelined, so each unit can take one new operation per cycle. The integer adder is not pipelined: a free slot is a unit that is empty after the cycle’s advance. With latency 1, a unit that finished at the beginning of the cycle can take a new add in that cycle. Address calculation and memory use the same load/store unit count, and each of those units is unpipelined. Address dispatch fills the free address units. Memory dispatch fills the free memory units from `ready_mem`, which is the starter’s head-store check followed by the same load scan. A ready head store is the only candidate until it is taken. Two functional units and three ready operations means two start.

## Age each functional-unit entry once per cycle

`age_entry` increments an entry’s cycle count and records the execute-start cycle when that count becomes 1. `fu_exe` ages every entry already in a queue, then retires every finished head, so two operations that started together finish together. `advance_new` ages only the instruction that just entered, so older work is not stepped twice. An operation issued and dispatched in the same cycle stays at cycle 0 until the next cycle’s `fu_exe`.

## Write back and commit up to the same width

Writeback broadcasts up to `issue_width` results that were latched on an earlier cycle, then latches up to that many new results. The rename map is updated only when the register still points at this ROB tag, so an older result cannot overwrite a newer rename. Commit retires up to `issue_width` ready ROB heads and stops at the first head that is not ready. A store’s commit cycle is the cycle it enters memory. A branch commits with an empty commit column once its execute range is recorded, and it writes no architectural register.

## Record a stall only when a rule blocks an instruction

The `COMMENTS` column is written only when one of the rules above actually stops an instruction. The blocked cycles follow the reason. A run of cycles is `[16-17]`, and one cycle is `[8]`. A gap under the same reason is two spans, as in `[4-5] [9-10]`. The cycle the instruction issues, starts, or takes the bus is not included.

- `no reservation station [16-17]` when issue cannot get a station or a load/store queue entry
- `no integer adder`, `no fp adder`, `no fp multiplier`, or `no load/store unit` when the instruction is ready and every unit of that type is taken
- `bus busy [28]` when more results are ready than the writeback width. The number is the writeback cycle that was missed. A result that finishes on cycle 27 can first write back on cycle 28, so a writeback on cycle 29 is `bus busy [28]`

The ordinary one-cycle result latch is not a stall. Address waits and memory waits share `no load/store unit`, so both spans appear after that one phrase.

## Branches use the integer adder and then fall through

`Bne` and `Beq` take an integer reservation station and the integer adder, the same way a compare would. Fetch is not stalled and the PC is not changed in execute. The next instruction is the one after the branch, so a loop body runs once.

## Results

The same program at issue widths 1, 2, 3, and 4 ends with the same registers and memory. `test_cases/test_case.txt` runs the body once, so `R1` is 8 and `R2` is 28. `Mem[32]` is 7.0. `sample_report_01` and `sample_report_02` also keep one architectural result at every width from 1 to 4.

`sample_report_02` has 2 floating-point adders, 2 multipliers, 2 load/store units, and 2 multiplier reservation stations. The third `Mult.d` waits with `no reservation station`, and two multiplies start on the same cycle.

Issue width 1, `test_cases/test_case.txt`:

```
                              ISSUE          EXE            MEM            WB             COMMIT         COMMENTS
Ld F2 0(R1)                   [1]            [2, 2]         [3, 7]         [9]            [10]           bus busy [8]
Mult.d F4 F2 F20              [2]            [10, 24]       []             [25]           [26]
Ld F6 0(R2)                   [3]            [4, 4]         [8, 12]        [13]           [27]           no load/store unit [4-6]
Add.d F6 F4 F6                [4]            [26, 29]       []             [30]           [31]
Sd F6 0(R2)                   [5]            [6, 6]         [32, 36]       []             [32]
Addi R1 R1 -4                 [6]            [7, 7]         []             [8]            [34]
Addi R2 R2 -4                 [7]            [8, 8]         []             [10]           [35]           bus busy [9]
Bne R1 R0 -12                 [8]            [9, 9]         []             []             []
Add.d F20 F2 F2               [9]            [10, 13]       []             [14]           [37]
```

Issue width 4, `python main.py test_cases/test_case.txt 4`. One integer adder, so the second `Addi` in a cycle waits:

```
                              ISSUE          EXE            MEM            WB             COMMIT         COMMENTS
Ld F2 0(R1)                   [1]            [2, 2]         [3, 7]         [8]            [9]
Mult.d F4 F2 F20              [1]            [9, 23]        []             [24]           [25]
Ld F6 0(R2)                   [1]            [2, 2]         [8, 12]        [13]           [25]           no load/store unit [1-6]
Add.d F6 F4 F6                [1]            [25, 28]       []             [29]           [30]
Sd F6 0(R2)                   [2]            [3, 3]         [31, 35]       []             [31]           no load/store unit [2]
Addi R1 R1 -4                 [2]            [3, 3]         []             [4]            [32]
Addi R2 R2 -4                 [2]            [3, 3]         []             [4]            [32]           no integer adder [2]
Bne R1 R0 -12                 [2]            [5, 5]         []             []             []
Add.d F20 F2 F2               [3]            [9, 12]        []             [13]           [33]
```

## Limitations

There is no branch predictor and no taken-branch redirect. A branch is only the comparison. The ordinary one-cycle result latch is not marked as `bus busy`.
