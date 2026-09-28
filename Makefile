# Makefile — open-source std-cell characterization flow
# Requirements: ngspice, python3

.PHONY: char lib lef report clean

char:            ## run full characterization (timing, power, noise) -> .lib + reports
	python3 scripts/run_char.py

lib: char

lef:             ## (docs) LEF is a layout abstract — see lef/README note inside inv.lef
	@echo "LEF comes from layout (Magic: lef write), not from characterization."

report:          ## show QA + noise summary
	@cat output/qa_report.json
	@cat output/noise_report.json

clean:
	rm -f output/_tmp.sp output/*.lib output/*.json
