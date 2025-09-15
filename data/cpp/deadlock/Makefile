# Root Makefile to build src and main targets

.PHONY: all src main clean

all: src main

src:
	$(MAKE) -C src

main: src
	LD_srcRARY_PATH=output:src $(MAKE) -C main

clean:
	$(MAKE) -C src clean
	$(MAKE) -C main clean