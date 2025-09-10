# Makefile to build main.cpp

CXX = g++
CXXFLAGS = -Wall -Wextra -std=c++17 -g
TARGET = main
SRC = main.cpp

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SRC)

clean:
	rm -f $(TARGET)