CXX = g++
CXXFLAGS = -std=c++11 -g -O0 -Wall -Wextra -pthread -fdebug-prefix-map=$(PWD)=.
TARGET = resource_leaks
SOURCE = resource_leaks.cpp

$(TARGET): $(SOURCE)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SOURCE)

clean:
	rm -f $(TARGET) *.txt

run: $(TARGET)
	./$(TARGET)

.PHONY: clean run