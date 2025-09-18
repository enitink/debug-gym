# State Corruption Debugging Scenario

## Description
This program simulates a banking system with subtle state corruption bugs that violate class invariants. The program doesn't crash but produces incorrect results that can only be detected through careful state inspection.

## State Corruption Issues
1. **Invariant Violations**: Object state becomes inconsistent with expected invariants
2. **Transaction Count Mismatch**: `transaction_count` doesn't match `transaction_history.size()`
3. **Balance Calculation Errors**: Balance doesn't equal sum of all transactions
4. **Business Logic Bugs**: Allows negative balances and transactions on frozen accounts
5. **Aggregate State Issues**: Bank's total deposits calculation is incorrect

## Class Invariants to Verify
### BankAccount Class
- `balance` should equal sum of all transactions in `transaction_history`
- `transaction_count` should equal `transaction_history.size()`
- Balance should never be negative for savings accounts
- Frozen accounts shouldn't allow new transactions

### Bank Class  
- `total_deposits` should reflect actual sum of account balances
- `total_accounts` should match number of accounts in the map

## Debugging Strategy
This scenario teaches debug agents to:
- Set breakpoints in class methods to inspect object states
- Verify invariants using GDB expressions
- Examine private member variables and their relationships
- Understand how state corruption propagates through method calls
- Use GDB to call methods and inspect return values

## Suggested GDB Commands
```bash
# Set breakpoints at key methods
gdb(command="break BankAccount::deposit")
gdb(command="break BankAccount::check_invariants")
gdb(command="break Bank::audit_accounts")

# Run with breakpoints to examine corruption
gdb(command="run_with_break state_corruption.cpp:37")  # Inside deposit method
gdb(command="run_with_break state_corruption.cpp:84")  # Inside invariant check

# Inspect object states at breakpoints
gdb(command="print *this")                    # Examine current object
gdb(command="print transaction_count")        # Check counter
gdb(command="print transaction_history.size()") # Check vector size
gdb(command="print balance")                  # Check balance
gdb(command="call check_invariants()")        # Call invariant method

# Examine bank state
gdb(command="print total_deposits")           # Bank's recorded total
gdb(command="print accounts.size()")          # Number of accounts
```

## Expected Debugging Flow
1. **Initial Execution**: Run program and observe audit failures
2. **Set Method Breakpoints**: Break in deposit/withdraw methods
3. **Inspect Object State**: Examine member variables during execution
4. **Verify Invariants**: Use GDB to check invariant conditions
5. **Trace Corruption**: Follow how state becomes inconsistent
6. **Fix State Management**: Implement proper state updates

## Key Learning Points
- How to use GDB to verify C++ class invariants
- Inspecting complex object relationships and dependencies
- Understanding subtle state corruption that doesn't cause crashes
- Using GDB to call methods and examine object behavior
- Debugging business logic errors in object-oriented code