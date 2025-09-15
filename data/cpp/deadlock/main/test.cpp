#include <resource_sharing.h>

int main() {

    std::thread t1(thread1_imageSectionCreation);
    std::thread t2(thread2_mappedPageWriter);

    t1.join();
    t2.join();

    return 0;
}