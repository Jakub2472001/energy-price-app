import pandas as pd
from pyomo.environ import *
import numpy as np
import matplotlib.pyplot as plt

class GasStorageModel:
    def __init__(self, residual):
        self.model = ConcreteModel()
        self.T = range(len(residual))
        self.demand, self.surplus = self.calc_demand_surplus(residual)
        # Assuming hourly demand for 24 hours
        self.base_demand = 50  # Base demand
        self.demand_variation = 30  # Variation in demand
        self.max_input = 100  # Maximum hourly input
        self.max_output = 100  # Maximum hourly output
        self.capacity = 200  # Total storage capacity
        self.efficiency_levels = {
            0: 0.7, 1: 0.7, 2: 0.3, 3: 0.7, 4: 0.7,
            5: 0.7, 6: 0.1, 7: 0.1, 8: 0.1, 9: 0.9, 10: 1.0
        }
        self._initialize_model(self.demand)

    def _initialize_model(self, demand):
        # Generate dummy demand data
        np.random.seed(0)  # For reproducibility
        self.model.demand = demand

        # Decision Variables
        self.model.output = Var(self.T, within=NonNegativeReals)
        self.model.input = Var(self.T, within=NonNegativeReals)
        self.model.storage = Var(self.T, within=NonNegativeReals)
        self.model.storage_level = Var(self.T, within=NonNegativeIntegers, bounds=(0, 10))  # 0 to 10 levels
        self.model.efficiency = Var(self.T, within=NonNegativeReals)
        self.model.is_level_active = Var(self.T, range(11), within=Binary)
        self.model.is_loading = Var(self.T, within=Binary)
        self.model.is_unloading = Var(self.T, within=Binary)

        # Objective Function
        self.model.obj = Objective(expr=sum(self.model.demand[t] - self.model.output[t] for t in self.T), sense=minimize)

        # Constraints
        self._add_constraints()

    def _add_constraints(self):
        # Storage balance
        self.model.storage_balance = Constraint(self.T, rule=self.storage_balance_rule)
        # Input limit
        self.model.input_limit = Constraint(self.T, rule=self.input_limit_rule)
        # Output limit
        self.model.output_limit = Constraint(self.T, rule=self.output_limit_rule)
        # Storage capacity
        self.model.storage_capacity = Constraint(self.T, rule=self.storage_capacity_rule)
        # Efficiency
        self.model.efficiency_link = Constraint(self.T, rule=self.efficiency_rule)
        # Only one storage level active
        self.model.only_one_level_active = Constraint(self.T, rule=self.only_one_level_active_rule)
        # Storage level active/inactive
        self.model.storage_level_active = Constraint(self.T, range(11), rule=self.storage_level_active_rule)
        self.model.storage_level_inactive = Constraint(self.T, range(11), rule=self.storage_level_inactive_rule)
        # Efficiency input constraint
        self.model.efficiency_input_constraint = Constraint(self.T, rule=self.efficiency_input_rule)
        # Loading and unloading constraints
        self.model.loading_input_constraint = Constraint(self.T, rule=self.loading_input_constraint)
        self.model.unloading_output_constraint = Constraint(self.T, rule=self.unloading_output_constraint)
        self.model.loading_unloading_exclusive_constraint = Constraint(self.T, rule=self.loading_unloading_exclusive)

    def storage_balance_rule(self, model, t):
        if t == 0:
            return model.storage[t] == model.input[t] - model.output[t]
        else:
            return model.storage[t] == model.storage[t - 1] + model.input[t] - model.output[t]

    def input_limit_rule(self, model, t):
        return model.input[t] <= self.max_input

    def output_limit_rule(self, model, t):
        return model.output[t] <= self.max_output

    def storage_capacity_rule(self, model, t):
        return model.storage[t] <= self.capacity

    def efficiency_rule(self, model, t):
        return model.efficiency[t] == sum(self.efficiency_levels[i] * model.is_level_active[t, i] for i in range(11))

    def only_one_level_active_rule(self, model, t):
        return sum(model.is_level_active[t, i] for i in range(11)) == 1

    def storage_level_active_rule(self, model, t, i):
        M = 1e6
        return model.storage[t] <= (i / 10) * self.capacity + M * (1 - model.is_level_active[t, i])

    def storage_level_inactive_rule(self, model, t, i):
        M = 1e6
        return model.storage[t] >= (i / 10) * self.capacity - M * (1 - model.is_level_active[t, i])

    def efficiency_input_rule(self, model, t):
        return model.input[t] <= model.efficiency[t] * self.max_input

    def loading_input_constraint(self, model, t):
        return model.input[t] <= self.max_input * model.is_loading[t]

    def unloading_output_constraint(self, model, t):
        return model.output[t] <= self.max_output * model.is_unloading[t]

    def loading_unloading_exclusive(self, model, t):
        return model.is_loading[t] + model.is_unloading[t] <= 1

    def solve(self):
        print('solving')

        solver = SolverFactory('scip')  # or any other solver
        solver.solve(self.model)
        print('done')

    def plot_results(self):
        print('plotting')

        input_values = [self.model.input[t].value for t in self.T]
        output_values = [self.model.output[t].value for t in self.T]
        storage_values = [self.model.storage[t].value for t in self.T]
        efficiency_values = [self.model.efficiency[t].value for t in self.T]

        plt.figure(figsize=(12, 8))
        # Demand Plot
        plt.subplot(3, 1, 1)
        plt.plot(self.T, [self.model.demand[t] for t in self.T], label='Demand', color='blue')
        plt.title('Gas Demand')
        plt.xlabel('Hour')
        plt.ylabel('Demand')
        plt.grid()
        plt.legend()
        # Storage and Input/Output Plot
        plt.subplot(3, 1, 2)
        plt.plot(self.T, storage_values, label='Gas Storage', color='green')
        plt.plot(self.T, input_values, label='Gas Input', color='orange')
        plt.plot(self.T, output_values, label='Gas Output', color='red')
        plt.title('Gas Storage, Input, and Output')
        plt.xlabel('Hour')
        plt.ylabel('Gas Volume')
        plt.grid()
        plt.legend()
        # Efficiency Plot
        plt.subplot(3, 1, 3)
        plt.plot(self.T, efficiency_values, label='Loading Efficiency', color='purple')
        plt.title('Loading Efficiency')
        plt.xlabel('Hour')
        plt.ylabel('Efficiency')
        plt.grid()
        plt.legend()
        plt.tight_layout()
        plt.show()

    def calc_demand_surplus(self, residual):
        positive_demand_mask = residual >=0
        demand = pd.Series(0, index = residual.index)
        surplus = pd.Series(0, index = residual.index)
        demand.loc[positive_demand_mask] = residual[positive_demand_mask]
        surplus.loc[~positive_demand_mask] = residual[~positive_demand_mask]

        return demand, surplus

# # Usage
# if __name__ == "__main__":
#     gas_model = GasStorageModel()
#     gas_model.solve()
#     gas_model.plot_results()
