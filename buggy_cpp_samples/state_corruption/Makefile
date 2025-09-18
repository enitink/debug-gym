CXX = g++
CXXFLAGS = -std=c++11 -g -O0 -Wall -Wextra
TARGET = state_corruption
SOURCE = state_corruption.cpp

$(TARGET): $(SOURCE)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SOURCE)

clean:
	rm -f $(TARGET)

run: $(TARGET)
	./$(TARGET)

.PHONY: clean run