* tb_noise — crosstalk glitch + delta-delay on a victim net with a coupled aggressor
* Victim: inverter held quiet (input tied low -> output should stay at VDD).
* Aggressor: parallel inverter switching; coupling cap Cc injects glitch onto victim.
* Rwire/Cwire model a victim route segment between driver output and load.
.include {ROOT}/cells/inv.sp

.param Cc = {CC}
.param TRF = {TRF}
.param CL  = {CL}

Vdd dd 0 1.8

* Victim chain: driver -> wire RC -> load
Xv inv_in vdrv dd 0 inv
Rv vdrv vnode 100
Cv1 vnode 0 20f
* receiver inverter on victim route
Xv2 vnode vout dd 0 inv
Cvout vout 0 {CL}
* victim input held quiet
Vin_v inv_in 0 0

* Aggressor runs parallel, coupled into the middle of the victim route
Xa a_in aout dd 0 inv
Caout aout 0 {CL}
* coupling capacitance between routes
Ca aout vnode {{Cc}}
Va a_in 0 PULSE(0 1.8 2n {TRF} {TRF} 8n 20n)

.tran 2p 22n

* Victim route dips negative; the receiver output (inverting) glitches POSITIVE.
* Route node: deepest negative excursion. Receiver output: peak positive excursion.
.meas tran glitch_vpp MAX v(vout) FROM=0 TO=22n
* Also on the route node itself
.meas tran glitch_route MIN v(vnode) FROM=0 TO=22n

.end
