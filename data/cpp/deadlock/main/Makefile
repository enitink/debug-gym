# Makefile to build test.cpp and statically link with libressharing.a

CXX = g++
CXXFLAGS = -Wall -Wextra -std=c++17 -g -fdebug-prefix-map=$(PWD)=.
TARGET = ../output/test
INC = -I../inc
SRC = test.cpp
LIBDIR = ../output
LIBS = -L$(LIBDIR) -lressharing

LIBRARY = ../output/libressharing.a

all: $(TARGET)

$(TARGET): $(SRC) $(LIBRARY)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SRC) $(INC) $(LIBS)

clean:
	rm -f $(TARGET)