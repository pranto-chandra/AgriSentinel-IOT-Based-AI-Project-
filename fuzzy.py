import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# Define variables
# Inputs
soil = ctrl.Antecedent(np.arange(0, 101, 1), 'soil')
temp = ctrl.Antecedent(np.arange(0, 51, 1), 'temp')
hum = ctrl.Antecedent(np.arange(0, 101, 1), 'hum')

# Output
irrigation = ctrl.Consequent(np.arange(0, 101, 1), 'irrigation')

# Membership functions
# Soil (0-100%): lower is drier in this context (or higher depending on sensor, let's assume 0 is bone dry)
# Based on main.py: dry < 55, wet > 85
soil['dry'] = fuzz.trimf(soil.universe, [0, 0, 60])
soil['medium'] = fuzz.trimf(soil.universe, [50, 70, 90])
soil['wet'] = fuzz.trimf(soil.universe, [80, 100, 100])

# Temperature (0-50°C)
temp['cold'] = fuzz.trimf(temp.universe, [0, 0, 20])
temp['normal'] = fuzz.trimf(temp.universe, [15, 25, 35])
temp['hot'] = fuzz.trimf(temp.universe, [30, 50, 50])

# Humidity (0-100%)
hum['dry'] = fuzz.trimf(hum.universe, [0, 0, 40])
hum['normal'] = fuzz.trimf(hum.universe, [30, 60, 90])
hum['humid'] = fuzz.trimf(hum.universe, [80, 100, 100])

# Irrigation (0-100%)
irrigation['low'] = fuzz.trimf(irrigation.universe, [0, 0, 40])
irrigation['medium'] = fuzz.trimf(irrigation.universe, [30, 50, 70])
irrigation['high'] = fuzz.trimf(irrigation.universe, [60, 100, 100])

# Rules
rule1 = ctrl.Rule(soil['dry'] & temp['hot'], irrigation['high'])
rule2 = ctrl.Rule(soil['dry'] & temp['cold'], irrigation['medium'])
rule3 = ctrl.Rule(soil['wet'], irrigation['low'])
rule4 = ctrl.Rule(soil['medium'] & temp['hot'], irrigation['medium'])
rule5 = ctrl.Rule(hum['humid'], irrigation['low'])
rule6 = ctrl.Rule(soil['dry'] & hum['dry'], irrigation['high'])

system = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6])
sim = ctrl.ControlSystemSimulation(system)

def fuzzy_refine(s, t, h):
    try:
        sim.input['soil'] = s
        sim.input['temp'] = t
        sim.input['hum'] = h
        sim.compute()
        return round(sim.output['irrigation'], 2)
    except:
        # Fallback if fuzzy logic fails (e.g., out of bounds)
        if s < 55: return 80.0
        return 20.0