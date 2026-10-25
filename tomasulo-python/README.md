Tomasulo Algorithm Simulation
* includes instructions of int_add, fp_add, fp_multi, load, store, branch;
* implements ROB, RAT, reservation stations, and the load-store queue;
* issues, writes back, and commits up to the issue width given on the command line (1-4, default 1);
* functional-unit counts come from the input file;
* branches compare on the integer adder and fall through (no redirect).

How to run:
cd code
python main.py test_cases/test_case.txt
python main.py test_cases/test_case.txt 4
