#include <iostream>
#include <vector>
#include <map>
#include <string>
#include <cassert>
#include <algorithm>

class BankAccount {
private:
    std::string account_id;
    double balance;
    std::vector<double> transaction_history;
    bool is_frozen;
    int transaction_count;
    
    // Class invariants that should always hold:
    // 1. balance should equal sum of all transactions
    // 2. transaction_count should equal transaction_history.size()
    // 3. balance should never be negative for savings accounts
    // 4. frozen accounts shouldn't allow transactions
    
public:
    BankAccount(const std::string& id, double initial_balance) 
        : account_id(id), balance(initial_balance), is_frozen(false), transaction_count(0) {
        transaction_history.push_back(initial_balance);
        transaction_count = 1; // Bug: Should be set after adding to history
        std::cout << "Created account " << id << " with balance $" << balance << std::endl;
    }
    
    bool deposit(double amount) {
        if (is_frozen) {
            std::cout << "Account " << account_id << " is frozen!" << std::endl;
            return false;
        }
        
        if (amount <= 0) {
            std::cout << "Invalid deposit amount: $" << amount << std::endl;
            return false;
        }
        
        // Bug: Updating balance before recording transaction
        balance += amount;
        transaction_history.push_back(amount);
        
        // Bug: Not incrementing transaction_count properly
        // transaction_count++; // This line is missing!
        
        std::cout << "Deposited $" << amount << " to " << account_id 
                  << ". New balance: $" << balance << std::endl;
        return true;
    }
    
    bool withdraw(double amount) {
        if (is_frozen) {
            std::cout << "Account " << account_id << " is frozen!" << std::endl;
            return false;
        }
        
        if (amount <= 0) {
            std::cout << "Invalid withdrawal amount: $" << amount << std::endl;
            return false;
        }
        
        // Bug: Allowing withdrawal that makes balance negative
        // Should check: if (balance - amount < 0) return false;
        
        balance -= amount;
        transaction_history.push_back(-amount); // Negative for withdrawal
        transaction_count++;
        
        std::cout << "Withdrew $" << amount << " from " << account_id 
                  << ". New balance: $" << balance << std::endl;
        return true;
    }
    
    void freeze_account() {
        is_frozen = true;
        std::cout << "Account " << account_id << " has been frozen." << std::endl;
    }
    
    void unfreeze_account() {
        is_frozen = false;
        std::cout << "Account " << account_id << " has been unfrozen." << std::endl;
    }
    
    // Method to check invariants - useful for GDB inspection
    bool check_invariants() const {
        // Invariant 1: Balance should equal sum of transactions
        double calculated_balance = 0.0;
        for (double transaction : transaction_history) {
            calculated_balance += transaction;
        }
        
        bool balance_correct = (std::abs(balance - calculated_balance) < 0.01);
        
        // Invariant 2: Transaction count should match history size
        bool count_correct = (transaction_count == static_cast<int>(transaction_history.size()));
        
        // Invariant 3: Balance should not be negative
        bool balance_positive = (balance >= 0.0);
        
        std::cout << "Invariant check for " << account_id << ":" << std::endl;
        std::cout << "  Balance correct: " << (balance_correct ? "YES" : "NO") 
                  << " (expected: $" << calculated_balance << ", actual: $" << balance << ")" << std::endl;
        std::cout << "  Count correct: " << (count_correct ? "YES" : "NO")
                  << " (expected: " << transaction_history.size() << ", actual: " << transaction_count << ")" << std::endl;
        std::cout << "  Balance positive: " << (balance_positive ? "YES" : "NO") << std::endl;
        
        return balance_correct && count_correct && balance_positive;
    }
    
    // Debugging getters for GDB inspection
    const std::string& get_id() const { return account_id; }
    double get_balance() const { return balance; }
    int get_transaction_count() const { return transaction_count; }
    size_t get_history_size() const { return transaction_history.size(); }
    bool is_account_frozen() const { return is_frozen; }
    const std::vector<double>& get_transaction_history() const { return transaction_history; }
};

class Bank {
private:
    std::map<std::string, BankAccount*> accounts;
    double total_deposits;
    int total_accounts;
    
public:
    Bank() : total_deposits(0.0), total_accounts(0) {
        std::cout << "Bank system initialized." << std::endl;
    }
    
    ~Bank() {
        // Clean up accounts
        for (auto& pair : accounts) {
            delete pair.second;
        }
    }
    
    bool create_account(const std::string& id, double initial_balance) {
        if (accounts.find(id) != accounts.end()) {
            std::cout << "Account " << id << " already exists!" << std::endl;
            return false;
        }
        
        BankAccount* account = new BankAccount(id, initial_balance);
        accounts[id] = account;
        
        // Bug: Not updating total_deposits correctly
        total_deposits += initial_balance * 1.1; // Incorrect multiplier
        total_accounts++;
        
        return true;
    }
    
    BankAccount* get_account(const std::string& id) {
        auto it = accounts.find(id);
        if (it != accounts.end()) {
            return it->second;
        }
        return nullptr;
    }
    
    void perform_transactions() {
        std::cout << "\n--- Performing Various Transactions ---" << std::endl;
        
        // Create some accounts
        create_account("ACC001", 1000.0);
        create_account("ACC002", 500.0);
        create_account("ACC003", 250.0);
        
        // Perform transactions that will corrupt state
        auto* acc1 = get_account("ACC001");
        auto* acc2 = get_account("ACC002");
        auto* acc3 = get_account("ACC003");
        
        if (acc1) {
            acc1->deposit(200.0);   // Missing transaction_count increment
            acc1->withdraw(150.0);  // Works correctly
            acc1->deposit(75.0);    // Missing transaction_count increment
            acc1->withdraw(2000.0); // Should fail but allows negative balance
        }
        
        if (acc2) {
            acc2->deposit(100.0);
            acc2->freeze_account();
            acc2->deposit(50.0);    // Should fail due to frozen account
            acc2->withdraw(25.0);   // Should fail due to frozen account
        }
        
        if (acc3) {
            acc3->withdraw(300.0);  // Creates negative balance
            acc3->deposit(25.0);
        }
    }
    
    void audit_accounts() {
        std::cout << "\n--- Account Audit ---" << std::endl;
        std::cout << "Total accounts: " << total_accounts << std::endl;
        std::cout << "Recorded total deposits: $" << total_deposits << std::endl;
        
        double actual_total = 0.0;
        bool all_valid = true;
        
        for (const auto& pair : accounts) {
            BankAccount* account = pair.second;
            std::cout << "\nAuditing account: " << pair.first << std::endl;
            
            bool valid = account->check_invariants();
            all_valid = all_valid && valid;
            actual_total += account->get_balance();
        }
        
        std::cout << "\nActual total balance: $" << actual_total << std::endl;
        std::cout << "All accounts valid: " << (all_valid ? "YES" : "NO") << std::endl;
    }
    
    // Debugging helpers
    size_t get_account_count() const { return accounts.size(); }
    double get_recorded_total() const { return total_deposits; }
};

int main() {
    std::cout << "Starting Bank State Corruption Simulation..." << std::endl;
    std::cout << "This program simulates a banking system with state corruption bugs." << std::endl;
    std::cout << "Use GDB to inspect object states and verify invariants." << std::endl;
    
    Bank bank;
    
    // Perform transactions that will corrupt object states
    bank.perform_transactions();
    
    // Audit will reveal the corruption
    bank.audit_accounts();
    
    std::cout << "\nSimulation complete. Use GDB to inspect object states:" << std::endl;
    std::cout << "Suggested GDB breakpoints:" << std::endl;
    std::cout << "  - BankAccount::deposit (line ~37)" << std::endl;
    std::cout << "  - BankAccount::withdraw (line ~54)" << std::endl;
    std::cout << "  - BankAccount::check_invariants (line ~84)" << std::endl;
    std::cout << "  - Bank::audit_accounts (line ~173)" << std::endl;
    
    return 0;
}