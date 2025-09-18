CXX = g++
CXXFLAGS = -std=c++11 -g -O0 -Wall -Wextra
TARGET = data_structure_bugs
SOURCE = data_structure_bugs.cpp

$(TARGET): $(SOURCE)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SOURCE)

clean:
	rm -f $(TARGET)

run: $(TARGET)
	./$(TARGET)

.PHONY: clean run