#pragma once

#include <iostream>
#include <thread>
#include <mutex>
#include <chrono>
#include <string>
#include <iomanip>
#include <sstream>

void thread1_imageSectionCreation();
void thread2_mappedPageWriter();

extern std::mutex mainResource;
extern std::mutex pagingResource;