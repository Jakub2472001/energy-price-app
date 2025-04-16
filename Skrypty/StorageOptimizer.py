from pyomo.environ import *
import numpy as np
import matplotlib.pyplot as plt

# Create a model
model = ConcreteModel()

# Time periods
T = range(24)  # Assuming hourly demand for 24 hours

# Generate dummy demand data (e.g., sinusoidal demand pattern)
np.random.seed(0)  # For reproducibility
base_demand = 50  # Base demand
demand_variation = 30  # Variation in demand
model.demand = Param(T, initialize={t: base_demand + demand_variation * np.sin(t * np.pi / 12) + np.random.uniform(-5, 5) for t in T})

# Parameters
model.max_input = 100  # Maximum hourly input
model.max_output = 100  # Maximum hourly output
model.capacity = 200  # Total storage capacity

# Efficiency levels based on storage percentage
efficiency_levels = {
    0: 0.7,   # 0% storage
    1: 0.7,   # 10% storage
    2: 0.3,   # 20% storage
    3: 0.7,   # 30% storage
    4:0.7,   # 40% storage
    5: 0.7,   # 50% storage
    6: 0.1,   # 60% storage
    7: 0.1,   # 70% storage
    8: 0.1,   # 80% storage
    9: 0.9,   # 90% storage
    10: 1.0   # 100% storage
}

# Decision Variables
model.output = Var(T, within=NonNegativeReals)
model.input = Var(T, within=NonNegativeReals)
model.storage = Var(T, within=NonNegativeReals)
model.storage_level = Var(T, within=NonNegativeIntegers, bounds=(0, 10))  # 0 to 10 levels
model.efficiency = Var(T, within=NonNegativeReals)

# Binary variables for each storage level
model.is_level_active = Var(T, range(11), within=Binary)

# Binary variables for loading and unloading
model.is_loading = Var(T, within=Binary)
model.is_unloading = Var(T, within=Binary)

# Big M constant
M = 1e6

# Objective Function: Minimize non-delivered gas
model.obj = Objective(expr=sum(model.demand[t] - model.output[t] for t in T), sense=minimize)

# Constraints
def storage_balance_rule(model, t):
    if t == 0:
        return model.storage[t] == model.input[t] - model.output[t]
    else:
        return model.storage[t] == model.storage[t-1] + model.input[t] - model.output[t]
model.storage_balance = Constraint(T, rule=storage_balance_rule)

def input_limit_rule(model, t):
    return model.input[t] <= model.max_input
model.input_limit = Constraint(T, rule=input_limit_rule)

def output_limit_rule(model, t):
    return model.output[t] <= model.max_output
model.output_limit = Constraint(T, rule=output_limit_rule)

def storage_capacity_rule(model, t):
    return model.storage[t] <= model.capacity
model.storage_capacity = Constraint(T, rule=storage_capacity_rule)

# # Link storage level to storage variable using floor to avoid conversion error
# def storage_level_rule(model, t):
#     return model.storage_level[t] == floor((model.storage[t] / model.capacity) * 10)  # 10 levels
# model.storage_level_link = Constraint(T, rule=storage_level_rule)

# Set efficiency based on storage level using Big M
def efficiency_rule(model, t):
    return model.efficiency[t] == sum(efficiency_levels[i] * model.is_level_active[t, i] for i in range(11))
model.efficiency_link = Constraint(T, rule=efficiency_rule)

# Ensure only one storage level is active
def only_one_level_active_rule(model, t):
    return sum(model.is_level_active[t, i] for i in range(11)) == 1
model.only_one_level_active = Constraint(T, rule=only_one_level_active_rule)

# Link storage level to active level
def storage_level_active_rule(model, t, i):
    return model.storage[t] <= (i / 10) * model.capacity + M * (1 - model.is_level_active[t, i])
model.storage_level_active = Constraint(T, range(11), rule=storage_level_active_rule)

def storage_level_inactive_rule(model, t, i):
    return model.storage[t] >= (i / 10) * model.capacity - M * (1 - model.is_level_active[t, i])
model.storage_level_inactive = Constraint(T, range(11), rule=storage_level_inactive_rule)

# Efficiency constraint based on storage level
def efficiency_input_rule(model, t):
    return model.input[t] <= model.efficiency[t] * model.max_input
model.efficiency_input_constraint = Constraint(T, rule=efficiency_input_rule)

# Constraint to prevent loading and unloading at the same time
def loading_input_constraint(model, t):
    return model.input[t] <= model.max_input * model.is_loading[t]  # Input can only occur if loading is active
model.loading_input_constraint = Constraint(T, rule=loading_input_constraint)

def unloading_output_constraint(model, t):
    return model.output[t] <= model.max_output * model.is_unloading[t]  # Output can only occur if unloading is active
model.unloading_output_constraint = Constraint(T, rule=unloading_output_constraint)

# Ensure only one of loading or unloading is active
def loading_unloading_exclusive(model, t):
    return model.is_loading[t] + model.is_unloading[t] <= 1  # Cannot load and unload at the same time
model.loading_unloading_exclusive_constraint = Constraint(T, rule=loading_unloading_exclusive)

# Solve the model
solver = SolverFactory('scip')  # or any other solver
solver.solve(model)

# Collect results for plotting
input_values = [model.input[t].value for t in T]
output_values = [model.output[t].value for t in T]
storage_values = [model.storage[t].value for t in T]
efficiency_values = [model.efficiency[t].value for t in T]

# Plotting function
def plot_results():
    plt.figure(figsize=(12, 8))

    # Demand Plot
    plt.subplot(3, 1, 1)
    plt.plot(T, [model.demand[t] for t in T], label='Demand', color='blue')
    plt.title('Gas Demand')
    plt.xlabel('Hour')
    plt.ylabel('Demand')
    plt.grid()
    plt.legend()

    # Storage and Input/Output Plot
    plt.subplot(3, 1, 2)
    plt.plot(T, storage_values, label='Gas Storage', color='green')
    plt.plot(T, input_values, label='Gas Input', color='orange')
    plt.plot(T, output_values, label='Gas Output', color='red')
    plt.title('Gas Storage, Input, and Output')
    plt.xlabel('Hour')
    plt.ylabel('Gas Volume')
    plt.grid()
    plt.legend()

    # Efficiency Plot
    plt.subplot(3, 1, 3)
    plt.plot(T, efficiency_values, label='Loading Efficiency', color='purple')
    plt.title('Loading Efficiency')
    plt.xlabel('Hour')
    plt.ylabel('Efficiency')
    plt.grid()
    plt.legend()

    plt.tight_layout()
    plt.show()

# Call the plotting function
plot_results()
