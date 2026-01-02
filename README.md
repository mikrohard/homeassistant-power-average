# Power Average Calculator for Home Assistant

A Home Assistant custom integration that calculates average power consumption over 15-minute windows for three-phase electrical systems. This is particularly useful for monitoring EV charging or other high-power consumption scenarios where you need to track average power usage for billing or load management purposes.

## Features

- **Real-time Power Monitoring**: Calculates total power consumption from three-phase current and voltage sensors
- **15-Minute Window Averaging**: Automatically calculates average power consumption over 15-minute windows
- **Per-Phase Tracking**: Monitors power consumption for each phase (L1, L2, L3) individually
- **Two Sensor Entities**:
  - **Current Window Sensor**: Shows the running average for the current 15-minute window
  - **Completed Window Sensor**: Shows the final average from the last completed 15-minute window
- **Estimated Window Sensors**: Optional sensors that predict the final window average when adding a specific power load
- **Export Protection**: Negative current values (power export) are automatically treated as 0
- **Configurable via UI**: Easy setup through Home Assistant's integration page

## Installation

### HACS (Recommended)

1. Add this repository to HACS as a custom repository:
   - Open HACS in Home Assistant
   - Click on the three dots menu and select "Custom repositories"
   - Add the repository URL: `https://github.com/mikrohard/homeassistant-power-average`
   - Select "Integration" as the category
   - Click "Add"

2. Install the integration through HACS:
   - Search for "Power Average Calculator"
   - Click "Download"
   - Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/power_average` folder to your Home Assistant's `custom_components` directory
2. Restart Home Assistant

## Configuration

### Prerequisites

You need to have the following sensors available in Home Assistant:
- Three current sensors (one for each phase L1, L2, L3) with device class `current`
- Three voltage sensors (one for each phase L1, L2, L3) with device class `voltage`

These sensors are typically provided by smart meters, energy monitors, or power measurement devices.

### Setup

1. Navigate to **Settings** → **Devices & Services** in Home Assistant
2. Click **Add Integration**
3. Search for "Power Average Calculator"
4. Click to add the integration
5. Configure the integration by providing:
   - **Name**: A friendly name for your power average calculator
   - **Phase L1 Current Sensor**: Select your L1 current sensor
   - **Phase L2 Current Sensor**: Select your L2 current sensor
   - **Phase L3 Current Sensor**: Select your L3 current sensor
   - **Phase L1 Voltage Sensor**: Select your L1 voltage sensor
   - **Phase L2 Voltage Sensor**: Select your L2 voltage sensor
   - **Phase L3 Voltage Sensor**: Select your L3 voltage sensor
6. Click **Submit** to proceed to power targets configuration
7. (Optional) Add power targets in Watts to create estimated window sensors
8. Click **Submit** to complete setup

## Usage

Once configured, the integration creates two sensor entities (plus optional estimated window sensors):

### 1. Power Average Sensor
- **Entity ID**: `sensor.[your_name]_power_average`
- **Description**: Shows the running average power consumption for the current 15-minute window
- **Attributes**:
  - `window_start`: Start time of the current window
  - `measurement_count`: Number of measurements taken in the current window
  - `window_duration_seconds`: Duration since window started
  - `l1_average_power`: Average power on phase L1
  - `l2_average_power`: Average power on phase L2
  - `l3_average_power`: Average power on phase L3
  - `last_measurement`: Timestamp of the last measurement

### 2. Completed Window Sensor
- **Entity ID**: `sensor.[your_name]_completed_window`
- **Description**: Shows the final average power consumption from the last completed 15-minute window
- **Attributes**:
  - `window_start`: Start time of the completed window
  - `window_end`: End time of the completed window
  - `measurement_count`: Total measurements in the completed window
  - `l1_average_power`: Average power on phase L1 for the completed window
  - `l2_average_power`: Average power on phase L2 for the completed window
  - `l3_average_power`: Average power on phase L3 for the completed window

### 3. Estimated Window Sensors (Optional)
For each configured power target, an estimated window sensor is created:

- **Entity ID**: `sensor.[your_name]_estimated_[target]w` (e.g., `sensor.power_average_estimated_3000w`)
- **Description**: Estimates what the final 15-minute window average would be if the specified power target is added for the remainder of the current window
- **Attributes**:
  - `power_target`: The configured power target in Watts
  - `current_window_average`: The current running average power
  - `window_start`: Start time of the current window
  - `elapsed_seconds`: Time elapsed since window started
  - `remaining_seconds`: Time remaining in the current window
  - `target_power_for_remainder`: The power value used for the remaining time (current average + power target)

#### How Estimated Window Sensors Work

The estimated window sensor calculates what the final completed window average would be by:

1. Taking the current window average for the elapsed portion of the window
2. Adding the power target to the current average for the remainder of the window
3. Calculating the weighted average across the full 15-minute window

**Formula:**
```
estimated_avg = (current_avg × elapsed_seconds + (current_avg + power_target) × remaining_seconds) / 900
```

**Example:** If 5 minutes have passed with a 2000W average, and you have a 3000W power target configured:
- Elapsed: 300 seconds at 2000W average
- Remaining: 600 seconds at 5000W (2000W + 3000W)
- Estimated final average: (2000 × 300 + 5000 × 600) / 900 = **4000W**

This is useful for EV charging scenarios where you want to know if starting/increasing charging now would push the window average above a certain threshold.

## How It Works

1. The integration continuously monitors the specified current and voltage sensors
2. Power is calculated using the formula: `Power = Current × Voltage` for each phase
3. Total power is the sum of all three phases: `Total = P(L1) + P(L2) + P(L3)`
4. Measurements are taken whenever sensor values change and every 10 seconds
5. The average is calculated over 15-minute windows (00-15, 15-30, 30-45, 45-00 minutes)
6. When a window completes, the final average is stored in the completed window sensor
7. Negative current values (power export) are automatically set to 0

## Use Cases

- **EV Charging Monitoring**: Track average power consumption during vehicle charging sessions
- **Load Management**: Monitor average power usage for peak demand management
- **Energy Billing**: Calculate average power for time-of-use billing periods
- **Industrial Equipment Monitoring**: Track power consumption patterns of three-phase equipment
- **Solar Export Prevention**: Monitor consumption while ignoring export values
- **Smart EV Charging**: Use estimated window sensors to determine optimal charging power levels without exceeding grid limits

## Example Automations

### Notification When Average Power Exceeds Threshold
```yaml
automation:
  - alias: "High Power Consumption Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.power_average
        above: 10000  # 10 kW
        for:
          minutes: 5
    action:
      - service: notify.mobile_app
        data:
          title: "High Power Consumption"
          message: "Average power consumption is {{ states('sensor.power_average') }} W"
```

### Log Completed Window Averages
```yaml
automation:
  - alias: "Log Power Window Averages"
    trigger:
      - platform: state
        entity_id: sensor.power_average_completed_window
    condition:
      - condition: template
        value_template: "{{ trigger.from_state.state != trigger.to_state.state }}"
    action:
      - service: logbook.log
        data:
          name: "Power Average"
          message: >
            15-minute average: {{ states('sensor.power_average_completed_window') }} W
            ({{ state_attr('sensor.power_average_completed_window', 'window_start') }} -
            {{ state_attr('sensor.power_average_completed_window', 'window_end') }})
```

### Smart EV Charging - Limit Based on Estimated Window Average
```yaml
automation:
  - alias: "Reduce EV Charging When Approaching Limit"
    trigger:
      - platform: numeric_state
        entity_id: sensor.power_average_estimated_7000w
        above: 10000  # Grid limit of 10 kW
    action:
      - service: number.set_value
        target:
          entity_id: number.ev_charger_current_limit
        data:
          value: 10  # Reduce charging current
      - service: notify.mobile_app
        data:
          title: "EV Charging Reduced"
          message: >
            Estimated window average would exceed 10kW.
            Current estimate: {{ states('sensor.power_average_estimated_7000w') }} W
```

## Troubleshooting

### Sensors Show "Unavailable"
- Ensure all six required sensors (3 current + 3 voltage) are available and providing numeric values
- Check that sensors have the correct device classes (`current` and `voltage`)

### No Measurements Being Taken
- Check Home Assistant logs for error messages
- Verify that the source sensors are updating regularly
- Ensure sensors are not in "unknown" or "unavailable" states

### Incorrect Power Values
- Verify that current sensors report values in Amperes (A)
- Verify that voltage sensors report values in Volts (V)
- Check if your current sensors already account for power factor

## Support

For issues, feature requests, or questions:
- Open an issue on [GitHub](https://github.com/mikrohard/homeassistant-power-average/issues)
- Check the [Home Assistant Community Forum](https://community.home-assistant.io/)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.