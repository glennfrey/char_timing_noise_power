* tb_dyn — dynamic power: toggle at 100 MHz, average supply current over a steady window
.include {ROOT}/cells/inv.sp

.param CL  = {CL}

Vdd dd 0 1.8
X1 in out dd 0 inv
Cload out 0 {CL}
Vin in 0 PULSE(0 1.8 2n 100p 100p 3n 10n)
.tran 5p 42n
.meas tran iavg AVG i(Vdd) FROM=22n TO=42n

.end
