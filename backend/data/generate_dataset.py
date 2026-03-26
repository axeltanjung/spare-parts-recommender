"""
Industrial Spare Parts Recommendation System - Synthetic Dataset Generator

Generates realistic industrial maintenance data with:
- Correlated sensor readings based on machine type and age
- Realistic failure distributions (Weibull-based)
- Missing values and noise injection
- Seasonal maintenance patterns
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import warnings
warnings.filterwarnings("ignore")

np.random.seed(42)

MACHINE_TYPES = ["crusher", "conveyor", "pump", "compressor", "motor", "turbine"]
LOCATIONS = ["Plant-A", "Plant-B", "Plant-C", "Mine-North", "Mine-South", "Refinery-1"]
FAILURE_TYPES = [
    "bearing_failure", "seal_leak", "overheating", "vibration_excess",
    "electrical_fault", "corrosion", "fatigue_crack", "lubrication_failure",
    "belt_wear", "impeller_damage"
]
PART_CATEGORIES = [
    "bearing", "seal", "filter", "belt", "impeller", "motor_coil",
    "gasket", "valve", "coupling", "gear", "shaft", "housing",
    "sensor_probe", "lubricant_cartridge", "cooling_fan"
]

MACHINE_TYPE_PROFILES = {
    "crusher":    {"temp_base": 75, "vib_base": 8.0, "press_base": 150, "failure_rate": 0.08},
    "conveyor":   {"temp_base": 45, "vib_base": 4.5, "press_base": 50,  "failure_rate": 0.05},
    "pump":       {"temp_base": 55, "vib_base": 5.0, "press_base": 200, "failure_rate": 0.06},
    "compressor": {"temp_base": 85, "vib_base": 6.5, "press_base": 300, "failure_rate": 0.07},
    "motor":      {"temp_base": 65, "vib_base": 5.5, "press_base": 80,  "failure_rate": 0.04},
    "turbine":    {"temp_base": 95, "vib_base": 7.0, "press_base": 250, "failure_rate": 0.09},
}

COMPATIBLE_PARTS = {
    "crusher":    ["bearing", "gear", "shaft", "housing", "lubricant_cartridge", "belt"],
    "conveyor":   ["belt", "bearing", "coupling", "motor_coil", "gear", "sensor_probe"],
    "pump":       ["impeller", "seal", "gasket", "valve", "bearing", "coupling"],
    "compressor": ["valve", "filter", "seal", "gasket", "cooling_fan", "lubricant_cartridge"],
    "motor":      ["motor_coil", "bearing", "coupling", "cooling_fan", "sensor_probe", "shaft"],
    "turbine":    ["impeller", "bearing", "seal", "shaft", "sensor_probe", "cooling_fan"],
}

FAILURE_PART_MAP = {
    "bearing_failure":     ["bearing", "lubricant_cartridge", "housing"],
    "seal_leak":           ["seal", "gasket", "valve"],
    "overheating":         ["cooling_fan", "filter", "lubricant_cartridge"],
    "vibration_excess":    ["bearing", "coupling", "shaft", "gear"],
    "electrical_fault":    ["motor_coil", "sensor_probe"],
    "corrosion":           ["gasket", "valve", "housing", "seal"],
    "fatigue_crack":       ["shaft", "housing", "impeller", "gear"],
    "lubrication_failure": ["lubricant_cartridge", "bearing", "filter"],
    "belt_wear":           ["belt", "coupling"],
    "impeller_damage":     ["impeller", "seal", "shaft"],
}


def generate_machines(n=200):
    machines = []
    for i in range(n):
        mtype = np.random.choice(MACHINE_TYPES, p=[0.2, 0.25, 0.2, 0.15, 0.12, 0.08])
        age = max(0.5, np.random.weibull(2.5) * 8)
        usage = np.clip(np.random.normal(16, 4), 4, 24)
        if age > 10:
            usage = np.clip(usage - 2, 4, 24)

        machines.append({
            "machine_id": f"M{i+1:04d}",
            "machine_type": mtype,
            "age_years": round(age, 1),
            "location": np.random.choice(LOCATIONS, p=[0.25, 0.2, 0.15, 0.15, 0.15, 0.1]),
            "usage_hours_per_day": round(usage, 1),
        })

    df = pd.DataFrame(machines)
    mask = np.random.random(len(df)) < 0.02
    df.loc[mask, "age_years"] = np.nan
    return df


def generate_spare_parts(n=150):
    parts = []
    for i in range(n):
        category = np.random.choice(PART_CATEGORIES, p=[
            0.12, 0.10, 0.08, 0.08, 0.07, 0.06, 0.07, 0.07,
            0.06, 0.06, 0.05, 0.05, 0.04, 0.05, 0.04
        ])

        compatible_types = [mt for mt, cp in COMPATIBLE_PARTS.items() if category in cp]
        if not compatible_types:
            compatible_types = [np.random.choice(MACHINE_TYPES)]

        cost_base = {
            "bearing": 250, "seal": 80, "filter": 45, "belt": 120,
            "impeller": 800, "motor_coil": 1500, "gasket": 35, "valve": 300,
            "coupling": 180, "gear": 600, "shaft": 900, "housing": 1200,
            "sensor_probe": 350, "lubricant_cartridge": 60, "cooling_fan": 200,
        }

        cost = max(10, np.random.lognormal(np.log(cost_base.get(category, 200)), 0.3))
        failure_rate = np.clip(np.random.beta(2, 8), 0.01, 0.5)

        parts.append({
            "part_id": f"P{i+1:04d}",
            "part_name": f"{category}_{i+1:03d}",
            "category": category,
            "compatible_machine_types": ",".join(compatible_types),
            "failure_rate": round(failure_rate, 4),
            "cost_usd": round(cost, 2),
            "lead_time_days": int(np.random.choice([1, 3, 5, 7, 14, 21], p=[0.1, 0.25, 0.25, 0.2, 0.15, 0.05])),
            "criticality": np.random.choice(["high", "medium", "low"], p=[0.2, 0.5, 0.3]),
        })

    df = pd.DataFrame(parts)
    mask = np.random.random(len(df)) < 0.03
    df.loc[mask, "cost_usd"] = np.nan
    return df


def generate_maintenance_logs(machines_df, parts_df, n=8000):
    logs = []
    start_date = datetime(2021, 1, 1)
    end_date = datetime(2024, 12, 31)
    date_range_days = (end_date - start_date).days

    for i in range(n):
        machine = machines_df.sample(1, weights=_machine_weights(machines_df)).iloc[0]
        mtype = machine["machine_type"]

        compatible = parts_df[
            parts_df["compatible_machine_types"].str.contains(mtype, na=False)
        ]
        if compatible.empty:
            compatible = parts_df.sample(1)

        failure_type = np.random.choice(FAILURE_TYPES, p=_failure_probs(mtype))
        relevant_categories = FAILURE_PART_MAP.get(failure_type, [])

        relevant_parts = compatible[compatible["category"].isin(relevant_categories)]
        if relevant_parts.empty:
            relevant_parts = compatible

        part = relevant_parts.sample(1).iloc[0]

        day_offset = int(np.random.beta(3, 2) * date_range_days)
        ts = start_date + timedelta(days=day_offset)
        month = ts.month
        seasonal_factor = 1.0 + 0.15 * np.sin(2 * np.pi * (month - 6) / 12)

        age = machine["age_years"] if pd.notna(machine["age_years"]) else 5.0
        usage = machine["usage_hours_per_day"]
        base_downtime = np.random.lognormal(1.5, 0.8)
        downtime = base_downtime * (1 + 0.05 * age) * (usage / 16) * seasonal_factor

        logs.append({
            "log_id": f"L{i+1:06d}",
            "machine_id": machine["machine_id"],
            "part_id": part["part_id"],
            "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "failure_type": failure_type,
            "downtime_hours": round(np.clip(downtime, 0.5, 120), 2),
            "maintenance_type": np.random.choice(
                ["corrective", "preventive", "predictive"],
                p=[0.5, 0.3, 0.2]
            ),
            "technician_id": f"T{np.random.randint(1, 31):03d}",
        })

    df = pd.DataFrame(logs)
    mask = np.random.random(len(df)) < 0.015
    df.loc[mask, "downtime_hours"] = np.nan
    mask2 = np.random.random(len(df)) < 0.01
    df.loc[mask2, "failure_type"] = np.nan
    return df


def generate_sensor_data(machines_df, n_readings_per_machine=15):
    sensors = []
    for _, machine in machines_df.iterrows():
        mtype = machine["machine_type"]
        profile = MACHINE_TYPE_PROFILES[mtype]
        age = machine["age_years"] if pd.notna(machine["age_years"]) else 5.0
        usage = machine["usage_hours_per_day"]

        age_factor = 1 + 0.03 * age
        usage_factor = usage / 16

        for j in range(n_readings_per_machine):
            temp = np.random.normal(
                profile["temp_base"] * age_factor * usage_factor,
                profile["temp_base"] * 0.1
            )
            vib = np.random.gamma(
                shape=3,
                scale=profile["vib_base"] * age_factor * usage_factor / 3
            )
            press = np.random.normal(
                profile["press_base"] * usage_factor,
                profile["press_base"] * 0.08
            )

            anomaly_components = [
                0.3 * (temp - profile["temp_base"]) / profile["temp_base"],
                0.4 * (vib - profile["vib_base"]) / profile["vib_base"],
                0.2 * abs(press - profile["press_base"]) / profile["press_base"],
                0.1 * age / 15,
            ]
            anomaly = np.clip(sum(anomaly_components) + np.random.normal(0, 0.05), 0, 1)

            sensors.append({
                "machine_id": machine["machine_id"],
                "reading_date": (
                    datetime(2024, 1, 1) + timedelta(days=j * 24)
                ).strftime("%Y-%m-%d"),
                "avg_temperature": round(np.clip(temp, 20, 200), 2),
                "vibration_level": round(np.clip(vib, 0.5, 25), 2),
                "pressure_psi": round(np.clip(press, 10, 500), 2),
                "anomaly_score": round(anomaly, 4),
            })

    df = pd.DataFrame(sensors)
    mask = np.random.random(len(df)) < 0.03
    df.loc[mask, "avg_temperature"] = np.nan
    mask2 = np.random.random(len(df)) < 0.02
    df.loc[mask2, "vibration_level"] = np.nan
    return df


def _machine_weights(machines_df):
    ages = machines_df["age_years"].fillna(5.0)
    usage = machines_df["usage_hours_per_day"]
    weights = ages * usage
    return weights / weights.sum()


def _failure_probs(machine_type):
    base = np.ones(len(FAILURE_TYPES))
    type_boost = {
        "crusher":    {"vibration_excess": 3, "fatigue_crack": 2, "bearing_failure": 2},
        "conveyor":   {"belt_wear": 4, "bearing_failure": 2, "lubrication_failure": 2},
        "pump":       {"seal_leak": 3, "impeller_damage": 3, "corrosion": 2},
        "compressor": {"overheating": 3, "seal_leak": 2, "vibration_excess": 2},
        "motor":      {"electrical_fault": 4, "overheating": 2, "bearing_failure": 2},
        "turbine":    {"vibration_excess": 3, "fatigue_crack": 3, "overheating": 2},
    }
    for ft, boost in type_boost.get(machine_type, {}).items():
        idx = FAILURE_TYPES.index(ft)
        base[idx] *= boost

    return base / base.sum()


def generate_all(output_dir="./generated"):
    os.makedirs(output_dir, exist_ok=True)

    print("Generating machines...")
    machines = generate_machines(200)
    machines.to_csv(os.path.join(output_dir, "machines.csv"), index=False)
    print(f"  -> {len(machines)} machines")

    print("Generating spare parts...")
    parts = generate_spare_parts(150)
    parts.to_csv(os.path.join(output_dir, "spare_parts.csv"), index=False)
    print(f"  -> {len(parts)} spare parts")

    print("Generating maintenance logs...")
    logs = generate_maintenance_logs(machines, parts, 8000)
    logs.to_csv(os.path.join(output_dir, "maintenance_logs.csv"), index=False)
    print(f"  -> {len(logs)} maintenance logs")

    print("Generating sensor data...")
    sensors = generate_sensor_data(machines, 15)
    sensors.to_csv(os.path.join(output_dir, "sensor_data.csv"), index=False)
    print(f"  -> {len(sensors)} sensor readings")

    total = len(machines) + len(parts) + len(logs) + len(sensors)
    print(f"\nTotal rows: {total}")
    print(f"Output directory: {os.path.abspath(output_dir)}")

    return machines, parts, logs, sensors


if __name__ == "__main__":
    generate_all()
