# Makefile to build libressharing.a (static library)

CXX = g++
INC = -I../inc
CXXFLAGS = -Wall -Wextra -std=c++17 -g -fPIC
AR = ar
TARGET = ../output/libressharing.a
SRC = resource_sharing.cpp
OBJ = resource_sharing.o

all: $(TARGET)

$(OBJ): $(SRC)
	$(CXX) $(CXXFLAGS) -c $(SRC) $(INC) -o $(OBJ)

$(TARGET): $(OBJ)
	$(AR) rcs $(TARGET) $(OBJ)

clean:
	rm -f $(TARGET) $(OBJ)