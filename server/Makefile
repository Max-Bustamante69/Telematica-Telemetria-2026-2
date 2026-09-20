CC      ?= gcc
CFLAGS  ?= -std=gnu11 -O2 -Wall -Wextra -Wpedantic -pthread
LDFLAGS ?= -pthread

SRC := $(wildcard src/*.c)
OBJ := $(SRC:src/%.c=build/%.o)
BIN := build/telemetry-server

all: $(BIN)

$(BIN): $(OBJ)
	$(CC) $(OBJ) -o $@ $(LDFLAGS)

build/%.o: src/%.c src/*.h
	@mkdir -p build
	$(CC) $(CFLAGS) -c $< -o $@

run: $(BIN)
	./$(BIN)

clean:
	rm -rf build

.PHONY: all run clean
