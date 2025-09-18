#include <iostream>
using namespace std;

int main() {
    // Null pointer dereference bug
    int* ptr = nullptr;
    
    cout << "About to dereference null pointer..." << endl;
    
    // BUG: Dereferencing null pointer causes segmentation fault
    cout << "Value: " << *ptr << endl;
    
    return 0;
}