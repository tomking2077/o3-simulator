# Tomasulo multi-issue

Each cycle runs in one order: issue, execute, memory, writeback, commit. The same rules below are used for every instruction. The loop keeps going while the reorder buffer is not empty, on the first cycle, and while a memory unit is still writing. A store can leave the reorder buffer when it enters memory, and the write finishes later.

## Read the machine from the input

`parse_input` reads the input file in one pass. The file sets the reservation-station counts, the functional-unit counts, the execute and memory latencies, the ROB size, and the initial registers and memory. Issue width is the optional second command-line argument and is clamped to 1–4. Omitting it uses width 1. A file that contains only instructions still loads, using the default machine. `Bne` and `Beq` are ordinary opcodes in that same table.

With no file argument, `python main.py` reads `code.in`.

## Issue up to the width, in order

Each cycle issues at most `issue_width` instructions, in program order, and stops at the first one that cannot issue. That width is also the writeback width and the commit width.

A load or store needs a load/store queue entry. An integer operation or a branch needs an integer reservation station. A floating-point add and a multiply need their own stations. Each of those still places its own operands. The refusal is shared: `station_stall` returns `no reservation station` when the station or the queue is full, and returns nothing when the only limit is the ROB. A full station blocks that instruction and everything behind it for the cycle. The station stays occupied until the operation is dispatched. Issue stalls are held until that instruction issues, then copied onto its ROB entry.

The timing table prints an instruction number in the `Insn` column. The number is one more than the program counter, so the first instruction is 1. It is a label for reading the table. The simulator does not use it to name dependencies.

## Execute: age what is already running, then start free units

Execute ages work that is already in a unit, retires what finished, and only then starts new operations.

`age_entry` increments an entry’s cycle count and records the execute-start cycle when that count becomes 1. `fu_exe` ages every entry already in an adder or multiplier queue, then retires every finished head, so two operations that started together finish together. `advance_new` ages only the instruction that just entered, so older work is not stepped twice. An operation issued and dispatched in the same cycle stays at cycle 0 until the next cycle’s `fu_exe`. An operation issued on an earlier cycle can start execute in the cycle it is dispatched.

`dispatch_alu` then starts ready reservation-station entries. The number started is the number of free units of that type, counted once after the advance. A unit is not given a second new operation in the same cycle.

The floating-point adder and the floating-point multiplier are pipelined, so each unit can take one new operation per cycle even while older operations are still in the pipeline. The integer adder is not pipelined: a free slot is a unit that is empty after `fu_exe`. With latency 1, a unit that finished in that advance can take a new add in the same cycle.

Address calculation uses the load/store unit count and is not pipelined. Busy address units advance first. `dispatch_address` then fills the units that are free, and it will not put a second instruction on an address unit that is already busy.

## Memory

Memory runs after execute. A load can take its value from an earlier store in the queue. Busy memory units then advance. A load that finishes places its result in the results buffer. A store writes memory when its unit finishes, and its commit cycle is the cycle it entered memory.

Free memory units are filled once from `ready_mem`. A ready head store is the only candidate until it is taken. Otherwise the candidates are the ready loads the queue will accept. The load/store unit count is the number of memory slots, and those units are not pipelined. If every memory unit is busy after that fill, each leftover ready entry is marked `no load/store unit`. Address waits and memory waits share that phrase, so a gap prints as two spans.

## Write back and commit up to the same width

Writeback broadcasts up to `issue_width` results that were latched on an earlier cycle, then latches up to that many new results from the results buffer. The rename map is updated only when the register still points at this ROB tag, so an older result cannot overwrite a newer rename.

Commit retires up to `issue_width` ready ROB heads and stops at the first head that is not ready. An arithmetic instruction or a load commits on the cycle after it writes back, and that commit writes the architectural register. A store is retired when its commit cycle is already recorded. A branch is retired once its execute range is recorded. The branch commit column stays empty, and the branch writes no architectural register.

## Record a stall only when a rule blocks an instruction

The `COMMENTS` column is written only when one of the rules above actually stops an instruction. The blocked cycles follow the reason. A run of cycles is `[16-17]`, and one cycle is `[8]`. A gap under the same reason is two spans, as in `[4-5] [9-10]`. The cycle the instruction issues, starts, or takes the bus is not included.

- `no reservation station [16-17]` when issue cannot get a station or a load/store queue entry
- `no integer adder`, `no fp adder`, `no fp multiplier`, or `no load/store unit` when the instruction is ready and every unit of that type is taken
- `bus busy [28]` when more results are ready than the writeback width. The number is the writeback cycle that was missed. A result that finishes on cycle 27 can first write back on cycle 28, so a writeback on cycle 29 is `bus busy [28]`. If three results are waiting and one writes back on cycle `x`, the second is `bus busy [x]` and the third is `bus busy [x-x+1]`

The ordinary one-cycle result latch is not a stall. A full reorder buffer stops issue and does not add a comment.

## Branches use the integer adder and then fall through

`Bne` and `Beq` take an integer reservation station and the integer adder, the same way a compare would. Fetch is not stalled and the PC is not changed in execute. The PC advances when the branch issues, so the next instruction is the one after the branch and a loop body runs once.

## How to run

From `code`:

```
python main.py test_cases/test_case.txt
python main.py test_cases/test_case.txt 4
```

The first command uses issue width 1. The second argument, when present, is the issue width for that run.

## Results

The same program at issue widths 1, 2, 3, and 4 ends with the same registers and memory. `test_cases/test_case.txt` runs the body once, so `R1` is 8 and `R2` is 28. `F2` is 1.0, `F4` is 3.0, `F6` is 7.0, and `F20` is 2.0. `Mem[32]` is 7.0. `sample_report_01` and `sample_report_02` also keep one architectural result at every width from 1 to 4.

`sample_report_02` has 2 floating-point adders, 2 multipliers, 2 load/store units, and 2 multiplier reservation stations. The third `Mult.d` waits with `no reservation station`, and two multiplies can start on the same cycle.

Issue width 1, `test_cases/test_case.txt`:

```
Insn                                ISSUE          EXE            MEM            WB             COMMIT         COMMENTS
1     Ld F2 0(R1)                   [1]            [2, 2]         [3, 7]         [9]            [10]           bus busy [8]
2     Mult.d F4 F2 F20              [2]            [10, 24]       []             [25]           [26]
3     Ld F6 0(R2)                   [3]            [4, 4]         [8, 12]        [13]           [27]           no load/store unit [4-6]
4     Add.d F6 F4 F6                [4]            [26, 29]       []             [30]           [31]
5     Sd F6 0(R2)                   [5]            [6, 6]         [32, 36]       []             [32]
6     Addi R1 R1 -4                 [6]            [7, 7]         []             [8]            [34]
7     Addi R2 R2 -4                 [7]            [8, 8]         []             [10]           [35]           bus busy [9]
8     Bne R1 R0 -12                 [8]            [9, 9]         []             []             []
9     Add.d F20 F2 F2               [9]            [10, 13]       []             [14]           [37]
```

Issue width 4, `python main.py test_cases/test_case.txt 4`. One integer adder, so the second `Addi` waits:

```
Insn                                ISSUE          EXE            MEM            WB             COMMIT         COMMENTS
1     Ld F2 0(R1)                   [1]            [2, 2]         [3, 7]         [8]            [9]
2     Mult.d F4 F2 F20              [1]            [9, 23]        []             [24]           [25]
3     Ld F6 0(R2)                   [1]            [2, 2]         [8, 12]        [13]           [25]           no load/store unit [1-6]
4     Add.d F6 F4 F6                [1]            [25, 28]       []             [29]           [30]
5     Sd F6 0(R2)                   [2]            [3, 3]         [31, 35]       []             [31]           no load/store unit [2]
6     Addi R1 R1 -4                 [2]            [3, 3]         []             [4]            [32]
7     Addi R2 R2 -4                 [2]            [3, 3]         []             [4]            [32]           no integer adder [2]
8     Bne R1 R0 -12                 [2]            [5, 5]         []             []             []
9     Add.d F20 F2 F2               [3]            [9, 12]        []             [13]           [33]
```

## Limitations

There is no branch predictor and no taken-branch redirect. A branch is only the comparison. The ordinary one-cycle result latch is not marked as `bus busy`.
