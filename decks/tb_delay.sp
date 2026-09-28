* tb_delay — propagation delay + output transition, one (slew, load) point
* Driven by run_char.py via Python format substitution.
.include {ROOT}/cells/inv.sp

.param TRF = {TRF}
.param CL  = {CL}

Vdd dd 0 1.8
Vin in 0 PULSE(0 1.8 2n {{TRF}} {{TRF}} 8n 20n)
X1 in out dd 0 inv
Cload out 0 {{CL}}

.tran 2p 22n

* 50% crossing = 0.9 V ; 20%/80% = 0.36 V / 1.44 V
.meas tran tpLH  TRIG v(in)  VAL=0.9 RISE=1 TARG v(out) VAL=0.9 FALL=1
.meas tran tpHL  TRIG v(in)  VAL=0.9 FALL=1 TARG v(out) VAL=0.9 RISE=1
.meas tran trise TRIG v(out) VAL=0.36 RISE=1 TARG v(out) VAL=1.44 RISE=1
.meas tran tfall TRIG v(out) VAL=1.44 FALL=1 TARG v(out) VAL=0.36 FALL=1

.end
