CXX = g++
CXXFLAGS = -std=c++11 -g -O0 -Wall -Wextra -pthread
TARGET = object_leak
SOURCE = object_leak.cpp

$(TARGET): $(SOURCE)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SOURCE)

clean:
	rm -f $(TARGET)

run: $(TARGET)
	./$(TARGET)

.PHONY: clean run