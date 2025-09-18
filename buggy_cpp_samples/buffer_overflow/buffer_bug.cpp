#include <iostream>
using namespace std;

int main() {
    int arr[5] = {1, 2, 3, 4, 5};
    
    // Buffer overflow bug - accessing beyond array bounds
    for (int i = 0; i <= 7; i++) {
        cout << "arr[" << i << "] = " << arr[i] << endl;
    }
    
    return 0;
}