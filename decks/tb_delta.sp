* tb_delta — crosstalk DELAY on a passive victim route (aggressor switching vs quiet)
* Victim: driver -> wire RC (1k / 20f) -> receiver; aggressor couples into the route
* midpoint, where coupling actually matters (actively driven nodes absorb it).
*
* Run twice by setting the aggressor pulse AMPLITUDE:
*   VA=1.8  -> aggressor switching (coupling active)
*   VA=0    -> aggressor input pinned low, output constant -> coupling inactive
* (Note: a parallel resistor cannot disable an ideal voltage source — the source
*  always wins. The stimulus amplitude is the correct switch.)
.include {ROOT}/cells/inv.sp

.param TRF = {TRF}
.param CL  = {CL}
.param Cc  = {CC}
.param VA  = {VA}

Vdd dd 0 1.8
Vin in 0 PULSE(0 1.8 2n {TRF} {TRF} 8n 20n)

* Victim chain
Xv1 in vdrv dd 0 inv
Rwire vdrv vnode 1000
Cv1 vnode 0 20f
Xv2 vnode vout dd 0 inv
Cout vout 0 {CL}

* Aggressor, coupled into the route midpoint
Xa a_in aout dd 0 inv
Caout aout 0 {CL}
Ca aout vnode {{Cc}}
Va a_in 0 PULSE(0 {VA} 2n {TRF} {TRF} 8n 20n)

.tran 2p 22n
* Victim path is non-inverting overall (two inverters): in rise -> vout rise.
.meas tran tpLH TRIG v(in) VAL=0.9 RISE=1 TARG v(vout) VAL=0.9 RISE=1

.end
