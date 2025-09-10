#include <iostream>

int main() {
    int *ptr = nullptr;
    std::cout << "Hello, world!" << std::endl;

    std::cout << "Value: " << *ptr << std::endl;

    delete ptr;

    return 0;
}