CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror
INCLUDES = -Iinclude
SOURCES = src/tempera.c src/surface_gen.c
TEST_BIN = build/test_sdk

.PHONY: all test clean
all: $(TEST_BIN)

$(TEST_BIN): $(SOURCES) tests/test_sdk.c include/tempera/tempera.h include/tempera/surface_gen.h
	mkdir -p build
	$(CC) $(CFLAGS) $(INCLUDES) $(SOURCES) tests/test_sdk.c -o $(TEST_BIN)

test: $(TEST_BIN)
	./$(TEST_BIN)

clean:
	rm -rf build
