# Root Makefile to build lib and test targets

.PHONY: all lib test clean

all: lib test

lib:
	$(MAKE) -C lib

test: lib
	LD_LIBRARY_PATH=output:lib $(MAKE) -C test

clean:
	$(MAKE) -C lib clean
	$(MAKE) -C test clean