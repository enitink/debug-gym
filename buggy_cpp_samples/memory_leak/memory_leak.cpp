#include <iostream>
using namespace std;

int main() {
    // Memory leak bug - allocating memory without freeing it
    int* ptr = new int[100];
    
    // Initialize some values
    for (int i = 0; i < 100; i++) {
        ptr[i] = i * 2;
    }
    
    // Print first 10 values
    cout << "First 10 values:" << endl;
    for (int i = 0; i < 10; i++) {
        cout << "ptr[" << i << "] = " << ptr[i] << endl;
    }
    
    // BUG: Missing delete[] ptr; - memory leak!
    return 0;
}