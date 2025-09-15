#include "resource_sharing.h"

using namespace std;
using namespace std::chrono_literals;

std::mutex mainResource;
std::mutex pagingResource;


void thread1_imageSectionCreation() {
    std::unique_lock<std::mutex> lockMain(mainResource);

    std::this_thread::sleep_for(100ms);  // Simulate work

    std::unique_lock<std::mutex> lockPaging(pagingResource);  // Deadlock if thread 2 holds it
}

void thread2_mappedPageWriter() {
    std::unique_lock<std::mutex> lockPaging(pagingResource);

    std::this_thread::sleep_for(100ms);  // Simulate work

    std::unique_lock<std::mutex> lockMain(mainResource);  // Deadlock if thread 1 holds it
}