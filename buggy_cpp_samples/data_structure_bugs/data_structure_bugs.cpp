#include <iostream>
#include <vector>
#include <memory>
#include <string>
#include <cassert>

// Binary Search Tree with invariant violations
class BSTreeNode {
public:
    int data;
    std::shared_ptr<BSTreeNode> left;
    std::shared_ptr<BSTreeNode> right;
    int height;  // For AVL balancing
    int subtree_size;  // Should always equal 1 + left_size + right_size
    
    BSTreeNode(int value) : data(value), left(nullptr), right(nullptr), height(1), subtree_size(1) {}
};

class BinarySearchTree {
private:
    std::shared_ptr<BSTreeNode> root;
    int total_nodes;
    
public:
    BinarySearchTree() : root(nullptr), total_nodes(0) {}
    
    void insert(int value) {
        std::cout << "Inserting " << value << std::endl;
        root = insert_recursive(root, value);
        total_nodes++; // Bug: Should increment after successful insertion only
    }
    
    bool search(int value) {
        return search_recursive(root, value);
    }
    
    void remove(int value) {
        std::cout << "Removing " << value << std::endl;
        root = remove_recursive(root, value);
        // Bug: Always decrementing even if node wasn't found
        total_nodes--; 
    }
    
    // Method to check BST invariants
    bool check_bst_invariant() const {
        std::cout << "\n--- Checking BST Invariants ---" << std::endl;
        
        bool is_valid_bst = check_bst_recursive(root, INT_MIN, INT_MAX);
        bool sizes_correct = check_subtree_sizes(root);
        int actual_count = count_nodes(root);
        bool count_correct = (actual_count == total_nodes);
        
        std::cout << "Valid BST ordering: " << (is_valid_bst ? "YES" : "NO") << std::endl;
        std::cout << "Subtree sizes correct: " << (sizes_correct ? "YES" : "NO") << std::endl;
        std::cout << "Node count correct: " << (count_correct ? "YES" : "NO")
                  << " (expected: " << total_nodes << ", actual: " << actual_count << ")" << std::endl;
        
        return is_valid_bst && sizes_correct && count_correct;
    }
    
    void print_tree() const {
        std::cout << "Tree structure:" << std::endl;
        print_recursive(root, "", true);
    }
    
    // Debugging helpers
    int get_total_nodes() const { return total_nodes; }
    std::shared_ptr<BSTreeNode> get_root() const { return root; }
    
private:
    std::shared_ptr<BSTreeNode> insert_recursive(std::shared_ptr<BSTreeNode> node, int value) {
        if (!node) {
            return std::make_shared<BSTreeNode>(value);
        }
        
        if (value < node->data) {
            node->left = insert_recursive(node->left, value);
        } else if (value > node->data) {
            node->right = insert_recursive(node->right, value);
        } else {
            // Duplicate value - don't insert
            return node;
        }
        
        // Bug: Incorrect subtree size calculation
        node->subtree_size = 1;
        if (node->left) node->subtree_size += node->left->subtree_size;
        if (node->right) node->subtree_size += node->right->subtree_size;
        node->subtree_size += 1; // Bug: Adding 1 twice!
        
        // Bug: Height calculation is wrong
        int left_height = node->left ? node->left->height : 0;
        int right_height = node->right ? node->right->height : 0;
        node->height = left_height + right_height; // Should be max + 1, not sum
        
        return node;
    }
    
    std::shared_ptr<BSTreeNode> remove_recursive(std::shared_ptr<BSTreeNode> node, int value) {
        if (!node) {
            return nullptr; // Value not found
        }
        
        if (value < node->data) {
            node->left = remove_recursive(node->left, value);
        } else if (value > node->data) {
            node->right = remove_recursive(node->right, value);
        } else {
            // Node to be deleted found
            if (!node->left) {
                return node->right;
            } else if (!node->right) {
                return node->left;
            } else {
                // Node with two children
                auto min_node = find_min(node->right);
                node->data = min_node->data;
                node->right = remove_recursive(node->right, min_node->data);
            }
        }
        
        // Bug: Not updating subtree_size after removal
        // Should recalculate: node->subtree_size = 1 + left_size + right_size
        
        return node;
    }
    
    std::shared_ptr<BSTreeNode> find_min(std::shared_ptr<BSTreeNode> node) {
        while (node->left) {
            node = node->left;
        }
        return node;
    }
    
    bool search_recursive(std::shared_ptr<BSTreeNode> node, int value) const {
        if (!node) return false;
        if (value == node->data) return true;
        if (value < node->data) return search_recursive(node->left, value);
        return search_recursive(node->right, value);
    }
    
    bool check_bst_recursive(std::shared_ptr<BSTreeNode> node, int min_val, int max_val) const {
        if (!node) return true;
        
        if (node->data <= min_val || node->data >= max_val) {
            std::cout << "BST violation: node " << node->data 
                     << " not in range (" << min_val << ", " << max_val << ")" << std::endl;
            return false;
        }
        
        return check_bst_recursive(node->left, min_val, node->data) &&
               check_bst_recursive(node->right, node->data, max_val);
    }
    
    bool check_subtree_sizes(std::shared_ptr<BSTreeNode> node) const {
        if (!node) return true;
        
        int left_size = node->left ? node->left->subtree_size : 0;
        int right_size = node->right ? node->right->subtree_size : 0;
        int expected_size = 1 + left_size + right_size;
        
        if (node->subtree_size != expected_size) {
            std::cout << "Size violation: node " << node->data 
                     << " has size " << node->subtree_size 
                     << ", expected " << expected_size << std::endl;
            return false;
        }
        
        return check_subtree_sizes(node->left) && check_subtree_sizes(node->right);
    }
    
    int count_nodes(std::shared_ptr<BSTreeNode> node) const {
        if (!node) return 0;
        return 1 + count_nodes(node->left) + count_nodes(node->right);
    }
    
    void print_recursive(std::shared_ptr<BSTreeNode> node, const std::string& prefix, bool is_last) const {
        if (!node) return;
        
        std::cout << prefix << (is_last ? "└── " : "├── ") 
                  << node->data << " (size:" << node->subtree_size 
                  << ", height:" << node->height << ")" << std::endl;
        
        if (node->left || node->right) {
            if (node->right) {
                print_recursive(node->right, prefix + (is_last ? "    " : "│   "), !node->left);
            }
            if (node->left) {
                print_recursive(node->left, prefix + (is_last ? "    " : "│   "), true);
            }
        }
    }
};

// Priority Queue with heap invariant violations
class PriorityQueue {
private:
    std::vector<int> heap;
    bool is_max_heap;
    
public:
    PriorityQueue(bool max_heap = true) : is_max_heap(max_heap) {}
    
    void insert(int value) {
        heap.push_back(value);
        heap_up(heap.size() - 1);
        std::cout << "Inserted " << value << " into " 
                  << (is_max_heap ? "max" : "min") << " heap" << std::endl;
    }
    
    int extract_top() {
        if (heap.empty()) {
            throw std::runtime_error("Heap is empty");
        }
        
        int top = heap[0];
        heap[0] = heap.back();
        heap.pop_back();
        
        if (!heap.empty()) {
            // Bug: Sometimes forgetting to heapify down
            if (heap.size() > 3) {  // Only heapify for larger heaps
                heap_down(0);
            }
        }
        
        std::cout << "Extracted " << top << std::endl;
        return top;
    }
    
    bool check_heap_property() const {
        std::cout << "\n--- Checking Heap Property ---" << std::endl;
        
        for (size_t i = 0; i < heap.size(); i++) {
            size_t left_child = 2 * i + 1;
            size_t right_child = 2 * i + 2;
            
            if (left_child < heap.size()) {
                bool valid = is_max_heap ? (heap[i] >= heap[left_child]) : (heap[i] <= heap[left_child]);
                if (!valid) {
                    std::cout << "Heap violation: parent " << heap[i] << " at index " << i
                             << " vs left child " << heap[left_child] << " at index " << left_child << std::endl;
                    return false;
                }
            }
            
            if (right_child < heap.size()) {
                bool valid = is_max_heap ? (heap[i] >= heap[right_child]) : (heap[i] <= heap[right_child]);
                if (!valid) {
                    std::cout << "Heap violation: parent " << heap[i] << " at index " << i
                             << " vs right child " << heap[right_child] << " at index " << right_child << std::endl;
                    return false;
                }
            }
        }
        
        std::cout << "Heap property: VALID" << std::endl;
        return true;
    }
    
    void print_heap() const {
        std::cout << "Heap contents: [";
        for (size_t i = 0; i < heap.size(); i++) {
            std::cout << heap[i];
            if (i < heap.size() - 1) std::cout << ", ";
        }
        std::cout << "]" << std::endl;
    }
    
    // Debugging helpers
    size_t size() const { return heap.size(); }
    const std::vector<int>& get_heap() const { return heap; }
    
private:
    void heap_up(size_t index) {
        if (index == 0) return;
        
        size_t parent = (index - 1) / 2;
        bool should_swap = is_max_heap ? (heap[index] > heap[parent]) : (heap[index] < heap[parent]);
        
        if (should_swap) {
            std::swap(heap[index], heap[parent]);
            heap_up(parent);
        }
    }
    
    void heap_down(size_t index) {
        size_t left_child = 2 * index + 1;
        size_t right_child = 2 * index + 2;
        size_t target = index;
        
        if (left_child < heap.size()) {
            bool should_swap = is_max_heap ? (heap[left_child] > heap[target]) : (heap[left_child] < heap[target]);
            if (should_swap) target = left_child;
        }
        
        if (right_child < heap.size()) {
            bool should_swap = is_max_heap ? (heap[right_child] > heap[target]) : (heap[right_child] < heap[target]);
            if (should_swap) target = right_child;
        }
        
        if (target != index) {
            std::swap(heap[index], heap[target]);
            heap_down(target);
        }
    }
};

int main() {
    std::cout << "Starting Data Structure Invariant Violation Simulation..." << std::endl;
    std::cout << "This program tests BST and Heap data structures with invariant bugs." << std::endl;
    std::cout << "Use GDB to inspect data structure states and verify invariants." << std::endl;
    
    std::cout << "\n=== Testing Binary Search Tree ===" << std::endl;
    BinarySearchTree bst;
    
    // Insert values
    std::vector<int> values = {50, 30, 70, 20, 40, 60, 80, 10};
    for (int val : values) {
        bst.insert(val);
    }
    
    bst.print_tree();
    bst.check_bst_invariant();
    
    // Remove some values
    bst.remove(30);
    bst.remove(100); // Non-existent value
    
    bst.print_tree();
    bst.check_bst_invariant();
    
    std::cout << "\n=== Testing Priority Queue ===" << std::endl;
    PriorityQueue pq(true); // Max heap
    
    // Insert values
    std::vector<int> heap_values = {5, 10, 3, 8, 15, 2, 12, 7};
    for (int val : heap_values) {
        pq.insert(val);
    }
    
    pq.print_heap();
    pq.check_heap_property();
    
    // Extract some values
    for (int i = 0; i < 4; i++) {
        try {
            pq.extract_top();
            pq.print_heap();
            pq.check_heap_property();
        } catch (const std::exception& e) {
            std::cout << "Error: " << e.what() << std::endl;
        }
    }
    
    std::cout << "\nSimulation complete. Use GDB to inspect data structure invariants:" << std::endl;
    std::cout << "Suggested GDB breakpoints:" << std::endl;
    std::cout << "  - BinarySearchTree::insert_recursive (line ~46)" << std::endl;
    std::cout << "  - BinarySearchTree::check_bst_invariant (line ~34)" << std::endl;
    std::cout << "  - PriorityQueue::extract_top (line ~132)" << std::endl;
    std::cout << "  - PriorityQueue::check_heap_property (line ~152)" << std::endl;
    
    return 0;
}