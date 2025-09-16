# Makefile to build main.cpp

CXX = g++
CXXFLAGS = -Wall -Wextra -std=c++17 -g
TARGET = ./output/test
SRC = main.cpp

all: $(TARGET)

$(TARGET): $(SRC)
	mkdir -p ./output
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SRC)

clean:
	rm -f ./output/test