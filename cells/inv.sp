* inv.sp — CMOS inverter subcircuit with inline educational model cards
* Models are simplified LEVEL=1 (Shichman-Hodges) — fine for flow demonstration.
* For PDK-grade results, replace the .model cards with foundry includes,
* e.g.  .lib '/path/to/sky130A/libs.tech/ngspice/sky130.lib' tt
* and resize W/L to the PDK's minimum device rules.

.model NMOS NMOS (LEVEL=1 VTO=0.40  KP=120u  GAMMA=0.40 LAMBDA=0.05 PHI=0.70
+ CGSO=200p CGDO=200p CBD=2f CBS=2f PB=0.9 CJ=1m CJSW=0.2n)
.model PMOS PMOS (LEVEL=1 VTO=-0.45 KP=55u   GAMMA=0.50 LAMBDA=0.06 PHI=0.80
+ CGSO=200p CGDO=200p CBD=2f CBS=2f PB=0.9 CJ=1m CJSW=0.2n)

.subckt inv A Y VDD VSS
M1 Y A VDD VDD PMOS W=0.54u L=0.18u
M2 Y A VSS VSS NMOS W=0.36u L=0.18u
.ends inv
