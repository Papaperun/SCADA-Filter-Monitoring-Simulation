import pandas as pd 
import random
from datetime import datetime

# this is to generate a 3 - year log with random spikes , nulls sensore failures/outliers and human error

# Generate NTU values as a SCADA with a chances for nulls ( to indcate a filter being off) , and spikes to repsent real world 
# also makes turbitity increase as run hours like in the real world
def generate_ntu(hours_since_backwash, force_violation=False):
    if not force_violation and hours_since_backwash >= 50 and random.random() < 0.1:
        return None, 0 # Backwash
    if random.random() < 0.05 or force_violation:
        return round(random.uniform(0.30, 0.99), 2), hours_since_backwash # spike
    if random.random() < 0.01 : # outlier
        return round(random.uniform(1.0, 5.0), 2), hours_since_backwash # extream outliers ( sensor error)
    base_value = random.uniform(0.05, 0.29)
    increment = max(0, (hours_since_backwash- 50 )* 0.01 ) # calulates how much NTU value should increase
    return round(base_value + increment, 2), hours_since_backwash

# generate bench test ntu with natural veriablity and outliers
def generate_bench_value(scada_value, variablity=0.2):
    if scada_value is None:
        return None # # match SCADA backwash ( no reading)
    if random.random() < 0.02: # 2% chance of an outlier
        return round(random.uniform(0.0, 5.0), 2)
    offset = random.uniform(-variablity, variablity) * scada_value
    return round(scada_value + offset, 2)

date_range = pd.date_range(start="2022-01-01", end="2025-01-01", freq='15min') # change this after test for the full 3 years
filters = ["Filter one", "filter Two", "Filter Three", "Filter Four", "Filter Five"]
hours_since_backwash = {filter_name: random.randint(0,50) for filter_name in filters}
scada_data = []
bench_data = []

current_day = None # Track the current day for day break lines 
delayed_backwash_filter = random.choice(filters) # randomly selects a filter for the delay
delay_triggered = False # track if the delay has been triggered
delay_duration = 16 # number of 15_ minuted intervales ( 4 hours) to delay the backwash
delay_end_time = None

for timestamp in date_range:
    day = timestamp.date() # extract the date (YYYY-MM-DD)
    if current_day is None:
        current_day = day # Initialize the current day
    elif day != current_day:
        # Add a day break line when the day changes
        scada_data.append([f"{current_day} End of day"] + [None]* len(filters))  # <<< Added day break line >>>
        current_day = day # Update the current day 

    scada_row = [timestamp]  # <<< Start scada_row with timestamp >>>
    for filter_name in filters:
        # Handle delayed backwash logic 
        if filter_name == delayed_backwash_filter and not delay_triggered:
            if hours_since_backwash[filter_name] >= 50:
                delay_triggered = True  # <<< Fixed typo: delay_triggerd -> delay_triggered >>>
                delay_end_time = timestamp + pd.Timedelta(minutes=delay_duration * 15) # Calculate delay
        
        if filter_name == delayed_backwash_filter and delay_triggered:
            if delay_end_time is not None and timestamp < delay_end_time: # Ensure delay_end_time is not None
                # During the delay, force NTU to spike 
                ntu_value, _ = generate_ntu(hours_since_backwash[filter_name], force_violation=True)
            else:
                # End the delay and reset hours_since_backwash
                ntu_value, hours_since_backwash[filter_name] = generate_ntu(hours_since_backwash[filter_name])
                delay_triggered = False # Reset the delay trigger
        else:
            # Normal NTU generation for other filters
            ntu_value, hours_since_backwash[filter_name] = generate_ntu(hours_since_backwash[filter_name])

        if ntu_value is None:
            hours_since_backwash[filter_name] = 0
        else:
            hours_since_backwash[filter_name] += 1
        scada_row.append(ntu_value)  # <<< Append NTU value for each filter >>>
    
    scada_data.append(scada_row)  # <<< Append completed scada_row to scada_data >>>

    # Generate bench test data every 4 hours 
    if timestamp.minute == 0 and timestamp.hour % 4 == 0:
        bench_row = [timestamp]  # <<< Start bench_row with timestamp >>>
        for filter_name in filters:
            scada_value = scada_row[filters.index(filter_name) + 1]  # Get SCADA value for the filter
            bench_value = generate_bench_value(scada_value)
            bench_row.append(bench_value)  # <<< Append bench test value for each filter >>>
        bench_data.append(bench_row)  # <<< Append completed bench_row to bench_data >>>

# Create DataFrames for SCADA and Bench Test data
scada_columns = ["Timestamp"] + filters  # <<< Define SCADA columns >>>
bench_columns = ["Timestamp"] + filters  # <<< Define Bench Test columns >>>
scada_df = pd.DataFrame(scada_data, columns=scada_columns)
bench_df = pd.DataFrame(bench_data, columns=bench_columns)

# Save the DataFrame to separate CSV files 
scada_df.to_csv("scada_data.csv", index=False)
bench_df.to_csv("Bench_test_data.csv", index=False)

print("SCADA data saved to scada_data.csv")
print("Bench test data saved to bench_test_data.csv")