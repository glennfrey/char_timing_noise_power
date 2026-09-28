* tb_leak — leakage current at a pinned input bias (DC operating point)
* Run once per input state (INB=0 / INB=1.8); parse vdd#branch from the .op printout.
.include {ROOT}/cells/inv.sp

.param CL  = {CL}

Vdd dd 0 1.8
X1 in out dd 0 inv
Cload out 0 {CL}
Vin in 0 {INB}
.op

.end
