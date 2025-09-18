#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <map>
#include <memory>
#include <thread>
#include <chrono>

class FileManager {
private:
    std::map<std::string, std::ifstream*> open_files;
    std::map<std::string, std::ofstream*> output_files;
    int max_open_files;
    int current_file_count;
    
public:
    FileManager(int max_files = 10) : max_open_files(max_files), current_file_count(0) {
        std::cout << "FileManager created with max " << max_files << " files" << std::endl;
    }
    
    // Bug: Missing destructor - file handles not closed
    // ~FileManager() should close all open files
    
    bool open_file_for_reading(const std::string& filename) {
        if (current_file_count >= max_open_files) {
            std::cout << "Cannot open " << filename << " - too many open files" << std::endl;
            return false;
        }
        
        // Check if already open
        if (open_files.find(filename) != open_files.end()) {
            std::cout << "File " << filename << " already open" << std::endl;
            return true;
        }
        
        std::ifstream* file = new std::ifstream(filename);
        if (!file->is_open()) {
            std::cout << "Failed to open " << filename << " for reading" << std::endl;
            delete file;
            return false;
        }
        
        open_files[filename] = file;
        current_file_count++;
        std::cout << "Opened " << filename << " for reading. Open files: " << current_file_count << std::endl;
        return true;
    }
    
    bool create_output_file(const std::string& filename) {
        if (current_file_count >= max_open_files) {
            std::cout << "Cannot create " << filename << " - too many open files" << std::endl;
            return false;
        }
        
        std::ofstream* file = new std::ofstream(filename, std::ios::out | std::ios::trunc);
        if (!file->is_open()) {
            std::cout << "Failed to create " << filename << std::endl;
            delete file;
            return false;
        }
        
        output_files[filename] = file;
        current_file_count++;
        std::cout << "Created " << filename << " for writing. Open files: " << current_file_count << std::endl;
        return true;
    }
    
    bool write_to_file(const std::string& filename, const std::string& data) {
        auto it = output_files.find(filename);
        if (it == output_files.end()) {
            std::cout << "Output file " << filename << " not open" << std::endl;
            return false;
        }
        
        *(it->second) << data << std::endl;
        return true;
    }
    
    std::string read_line_from_file(const std::string& filename) {
        auto it = open_files.find(filename);
        if (it == open_files.end()) {
            return "";
        }
        
        std::string line;
        if (std::getline(*(it->second), line)) {
            return line;
        }
        return "";
    }
    
    void close_file(const std::string& filename) {
        // Bug: Only closes input files, not output files
        auto it = open_files.find(filename);
        if (it != open_files.end()) {
            it->second->close();
            delete it->second;
            open_files.erase(it);
            current_file_count--; // Bug: Decrementing even if file wasn't actually open
            std::cout << "Closed " << filename << ". Open files: " << current_file_count << std::endl;
        } else {
            std::cout << "File " << filename << " not found for closing" << std::endl;
            current_file_count--; // Bug: Still decrementing counter
        }
    }
    
    void list_open_files() const {
        std::cout << "\n--- Open Files Report ---" << std::endl;
        std::cout << "Current file count: " << current_file_count << std::endl;
        std::cout << "Input files (" << open_files.size() << "):" << std::endl;
        for (const auto& pair : open_files) {
            std::cout << "  - " << pair.first << std::endl;
        }
        std::cout << "Output files (" << output_files.size() << "):" << std::endl;
        for (const auto& pair : output_files) {
            std::cout << "  - " << pair.first << std::endl;
        }
    }
    
    // Debugging helpers
    int get_file_count() const { return current_file_count; }
    size_t get_input_files_size() const { return open_files.size(); }
    size_t get_output_files_size() const { return output_files.size(); }
};

class NetworkConnection {
private:
    std::string host;
    int port;
    bool is_connected;
    int connection_id;
    static int next_connection_id;
    
public:
    NetworkConnection(const std::string& hostname, int port_num) 
        : host(hostname), port(port_num), is_connected(false) {
        connection_id = next_connection_id++;
        std::cout << "NetworkConnection " << connection_id << " created for " 
                  << host << ":" << port << std::endl;
    }
    
    // Bug: Missing destructor - connections not properly closed
    // ~NetworkConnection() should call disconnect()
    
    bool connect() {
        if (is_connected) {
            std::cout << "Connection " << connection_id << " already connected" << std::endl;
            return true;
        }
        
        // Simulate connection
        std::cout << "Connecting to " << host << ":" << port << "..." << std::endl;
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        is_connected = true;
        
        std::cout << "Connection " << connection_id << " established" << std::endl;
        return true;
    }
    
    void send_data(const std::string& data) {
        if (!is_connected) {
            std::cout << "Connection " << connection_id << " not connected" << std::endl;
            return;
        }
        
        std::cout << "Sending via connection " << connection_id << ": " << data << std::endl;
    }
    
    void disconnect() {
        if (is_connected) {
            std::cout << "Disconnecting connection " << connection_id << std::endl;
            is_connected = false;
        }
    }
    
    // Debugging helpers
    int get_id() const { return connection_id; }
    bool get_connected_status() const { return is_connected; }
    const std::string& get_host() const { return host; }
    int get_port() const { return port; }
};

int NetworkConnection::next_connection_id = 1;

class ConnectionPool {
private:
    std::vector<std::shared_ptr<NetworkConnection>> connections;
    int max_connections;
    int active_connections;
    
public:
    ConnectionPool(int max_conn = 5) : max_connections(max_conn), active_connections(0) {
        std::cout << "ConnectionPool created with max " << max_conn << " connections" << std::endl;
    }
    
    // Bug: Not properly closing connections in destructor
    ~ConnectionPool() {
        std::cout << "ConnectionPool shutting down with " << active_connections 
                  << " active connections" << std::endl;
        // Should disconnect all connections
    }
    
    std::shared_ptr<NetworkConnection> get_connection(const std::string& host, int port) {
        if (active_connections >= max_connections) {
            std::cout << "Cannot create new connection - pool full" << std::endl;
            return nullptr;
        }
        
        auto connection = std::make_shared<NetworkConnection>(host, port);
        if (connection->connect()) {
            connections.push_back(connection);
            active_connections++;
            std::cout << "Added connection to pool. Active: " << active_connections << std::endl;
            return connection;
        }
        
        return nullptr;
    }
    
    void release_connection(int connection_id) {
        for (auto it = connections.begin(); it != connections.end(); ++it) {
            if ((*it)->get_id() == connection_id) {
                (*it)->disconnect();
                connections.erase(it);
                // Bug: Not decrementing active_connections counter
                std::cout << "Released connection " << connection_id 
                         << ". Active: " << active_connections << std::endl;
                return;
            }
        }
        
        std::cout << "Connection " << connection_id << " not found for release" << std::endl;
    }
    
    void cleanup_disconnected() {
        int cleaned = 0;
        auto it = connections.begin();
        while (it != connections.end()) {
            if (!(*it)->get_connected_status()) {
                it = connections.erase(it);
                cleaned++;
                // Bug: Not updating active_connections counter
            } else {
                ++it;
            }
        }
        
        std::cout << "Cleaned up " << cleaned << " disconnected connections. "
                  << "Active: " << active_connections << std::endl;
    }
    
    void status_report() const {
        std::cout << "\n--- Connection Pool Status ---" << std::endl;
        std::cout << "Active connections counter: " << active_connections << std::endl;
        std::cout << "Actual connections in pool: " << connections.size() << std::endl;
        
        for (const auto& conn : connections) {
            std::cout << "  Connection " << conn->get_id() 
                     << " to " << conn->get_host() << ":" << conn->get_port()
                     << " - " << (conn->get_connected_status() ? "CONNECTED" : "DISCONNECTED")
                     << std::endl;
        }
    }
    
    // Debugging helpers
    int get_active_count() const { return active_connections; }
    size_t get_actual_count() const { return connections.size(); }
};

int main() {
    std::cout << "Starting Resource Management Bug Simulation..." << std::endl;
    std::cout << "This program demonstrates file handle and network connection leaks." << std::endl;
    std::cout << "Use GDB to inspect resource states and identify leaks." << std::endl;
    
    {
        std::cout << "\n=== Testing File Manager ===" << std::endl;
        FileManager file_mgr(5);
        
        // Create some test files first
        std::ofstream temp1("test1.txt");
        temp1 << "This is test file 1\nWith some content\n";
        temp1.close();
        
        std::ofstream temp2("test2.txt");
        temp2 << "This is test file 2\nWith different content\n";
        temp2.close();
        
        // Open files for reading
        file_mgr.open_file_for_reading("test1.txt");
        file_mgr.open_file_for_reading("test2.txt");
        file_mgr.open_file_for_reading("nonexistent.txt");
        
        // Create output files
        file_mgr.create_output_file("output1.txt");
        file_mgr.create_output_file("output2.txt");
        
        // Write some data
        file_mgr.write_to_file("output1.txt", "Writing to output file 1");
        file_mgr.write_to_file("output2.txt", "Writing to output file 2");
        
        // Read some data
        std::cout << "Read from test1.txt: " << file_mgr.read_line_from_file("test1.txt") << std::endl;
        
        file_mgr.list_open_files();
        
        // Close some files (but not all)
        file_mgr.close_file("test1.txt");
        file_mgr.close_file("nonexistent.txt"); // Tries to close non-open file
        
        file_mgr.list_open_files();
        
        // FileManager destructor will be called here - resource leak!
    }
    
    {
        std::cout << "\n=== Testing Connection Pool ===" << std::endl;
        ConnectionPool pool(3);
        
        // Create connections
        auto conn1 = pool.get_connection("server1.com", 8080);
        auto conn2 = pool.get_connection("server2.com", 9090);
        auto conn3 = pool.get_connection("server3.com", 3000);
        auto conn4 = pool.get_connection("server4.com", 4000); // Should fail - pool full
        
        pool.status_report();
        
        // Use connections
        if (conn1) conn1->send_data("Hello from connection 1");
        if (conn2) conn2->send_data("Hello from connection 2");
        if (conn3) conn3->send_data("Hello from connection 3");
        
        // Disconnect one connection manually
        if (conn2) {
            conn2->disconnect();
        }
        
        // Clean up disconnected (but counter bug will remain)
        pool.cleanup_disconnected();
        pool.status_report();
        
        // Release a connection
        if (conn1) {
            pool.release_connection(conn1->get_id());
        }
        
        pool.status_report();
        
        // ConnectionPool destructor will be called here - resource leak!
    }
    
    std::cout << "\nSimulation complete. Use GDB to inspect resource management:" << std::endl;
    std::cout << "Suggested GDB breakpoints:" << std::endl;
    std::cout << "  - FileManager::open_file_for_reading (line ~28)" << std::endl;
    std::cout << "  - FileManager::close_file (line ~72)" << std::endl;
    std::cout << "  - ConnectionPool::get_connection (line ~154)" << std::endl;
    std::cout << "  - ConnectionPool::release_connection (line ~170)" << std::endl;
    
    return 0;
}