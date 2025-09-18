#include <iostream>
#include <vector>
#include <memory>
#include <string>
#include <thread>
#include <chrono>

class DataProcessor {
private:
    std::string* data;
    std::vector<int*> temp_buffers;
    int id;
    bool initialized;

public:
    DataProcessor(int processor_id) : id(processor_id), initialized(false) {
        data = new std::string("Processing data for ID: " + std::to_string(id));
        std::cout << "Created DataProcessor " << id << std::endl;
    }
    
    // Bug: Missing destructor - memory leak
    // Should have: ~DataProcessor() { delete data; cleanup_buffers(); }
    
    void process_batch(int batch_size) {
        if (!initialized) {
            initialize();
        }
        
        // Bug: Allocating memory but not properly cleaning up
        for (int i = 0; i < batch_size; i++) {
            int* buffer = new int[1000]; // Allocate 4KB per buffer
            
            // Simulate some processing
            for (int j = 0; j < 1000; j++) {
                buffer[j] = i * j + id;
            }
            
            temp_buffers.push_back(buffer);
            
            // Bug: Only cleaning up every 10th buffer, causing accumulation
            if (i % 10 == 0 && !temp_buffers.empty()) {
                delete[] temp_buffers.back();
                temp_buffers.pop_back();
            }
        }
        
        std::cout << "Processed batch of " << batch_size 
                  << " items. Current buffer count: " << temp_buffers.size() 
                  << std::endl;
    }
    
    void initialize() {
        initialized = true;
        std::cout << "Initialized processor " << id << std::endl;
    }
    
    // Getter for debugging with GDB
    int get_id() const { return id; }
    size_t get_buffer_count() const { return temp_buffers.size(); }
    bool is_initialized() const { return initialized; }
    const std::string* get_data() const { return data; }
    
private:
    void cleanup_buffers() {
        for (auto* buffer : temp_buffers) {
            delete[] buffer;
        }
        temp_buffers.clear();
    }
};

class ProcessorManager {
private:
    std::vector<DataProcessor*> processors;
    int next_id;
    
public:
    ProcessorManager() : next_id(1) {}
    
    // Bug: Not cleaning up processors in destructor
    ~ProcessorManager() {
        std::cout << "Manager shutting down with " << processors.size() 
                  << " processors" << std::endl;
        // Should delete all processors here
    }
    
    DataProcessor* create_processor() {
        auto* processor = new DataProcessor(next_id++);
        processors.push_back(processor);
        return processor;
    }
    
    void run_simulation(int rounds) {
        for (int round = 1; round <= rounds; round++) {
            std::cout << "\n--- Round " << round << " ---" << std::endl;
            
            // Create some processors
            for (int i = 0; i < 3; i++) {
                auto* processor = create_processor();
                processor->process_batch(50); // Each batch creates memory leaks
                
                // Bug: Not deleting processors, just removing from vector occasionally  
                if (processors.size() > 5) {
                    processors.erase(processors.begin());
                }
            }
            
            // Simulate some work
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            
            std::cout << "Active processors: " << processors.size() << std::endl;
        }
    }
    
    // Debugging helpers for GDB inspection
    size_t get_processor_count() const { return processors.size(); }
    DataProcessor* get_processor(size_t index) const {
        if (index < processors.size()) {
            return processors[index];
        }
        return nullptr;
    }
};

int main() {
    std::cout << "Starting Object Leak Simulation..." << std::endl;
    std::cout << "This program simulates a data processing system with memory leaks." << std::endl;
    std::cout << "Use GDB to inspect object states and identify leak sources." << std::endl;
    
    ProcessorManager manager;
    
    // Run simulation with multiple rounds
    manager.run_simulation(5);
    
    std::cout << "\nSimulation complete. Check memory usage and object states with GDB." << std::endl;
    std::cout << "Suggested GDB breakpoints:" << std::endl;
    std::cout << "  - DataProcessor::process_batch (line ~35)" << std::endl;
    std::cout << "  - ProcessorManager::create_processor (line ~74)" << std::endl;
    std::cout << "  - main before manager.run_simulation (line ~107)" << std::endl;
    
    return 0;
}