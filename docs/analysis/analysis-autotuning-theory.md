# Auto-Tuning in PID Temperature Controllers
## A Professor-Level Technical Explanation Without Skipping the Details

---

## 1. What Is Auto-Tuning?

**Auto-Tuning**, usually abbreviated as **AT**, is a function that allows a temperature controller to automatically measure the dynamic behavior of a controlled system and calculate suitable PID parameters.

In a temperature control system, the controller needs to understand how the process reacts when energy is applied. For example, it needs to know:

- how fast the temperature rises when output is increased;
- how much delay exists between output change and temperature response;
- how much thermal inertia the system has;
- whether the system overshoots easily;
- whether the system is slow and heavy;
- whether the output has enough authority to affect the process;
- whether the sensor response is fast or delayed.

Auto-Tuning is the controller's way of experimentally learning these characteristics.

In simple words:

> Auto-Tuning allows the controller to test the personality of the machine, then calculate suitable P, I, and D values based on the actual response.

It is not magic. It is a controlled experiment performed by the controller.

---

## 2. Basic Control Terms

Before understanding Auto-Tuning, the key terms must be clearly defined.

### 2.1 SV — Set Value

**SV** means **Set Value**.

It is the target value that the controller tries to reach.

Example:

```text
SV = 200°C
```

This means the controller will try to make the process temperature stabilize at 200°C.

In a coffee roaster, SV may refer to:

- environmental temperature target;
- inlet air temperature target;
- exhaust temperature target;
- drum temperature target;
- a temperature target used by an external profile controller.

### 2.2 PV — Process Value

**PV** means **Process Value**.

It is the actual measured value from the sensor.

Example:

```text
PV = 185°C
```

This means the sensor is currently reading 185°C.

The controller constantly compares SV and PV. The basic control error is:

```text
Error = SV - PV
```

If:

```text
SV > PV
```

the measured temperature is lower than the target, so the controller increases heating output.

If:

```text
SV < PV
```

the measured temperature is higher than the target, so the controller reduces heating output, or increases cooling output if cooling control is configured.

### 2.3 Output / MV — Manipulated Variable

The controller output is also called **MV**, meaning **Manipulated Variable**.

It is the signal that the controller sends to the final control element.

Examples of final control elements include:

- SSR;
- relay;
- electric heater;
- gas valve;
- burner actuator;
- inverter / VFD;
- damper actuator;
- steam valve;
- cooling fan;
- water valve.

The output is usually expressed as a percentage:

```text
0%   = minimum output
50%  = half output
100% = maximum output
```

For a linear analog output of **0–10V**:

```text
0%   = 0V
10%  = 1V
20%  = 2V
50%  = 5V
100% = 10V
```

The conversion formula is:

```text
Vout = Output% × 10 / 100
```

Example:

```text
Output = 73%

Vout = 73 × 10 / 100
Vout = 7.3V
```

---

## 3. What Does PID Mean?

PID consists of three control actions:

```text
P = Proportional
I = Integral
D = Derivative
```

In the manual, PID is described as:

```text
P = Proportional Band
I = Integral Time
D = Derivative Time
```

This detail is extremely important.

Many industrial controllers do not use `Kp` directly. Instead, they use **Proportional Band**.

These two concepts behave in opposite ways.

With proportional gain:

```text
Higher Kp = stronger control action
```

With proportional band:

```text
Smaller proportional band = stronger control action
Larger proportional band  = softer control action
```

Therefore, if the controller defines P as **Proportional Band**, then:

```text
Smaller P → more aggressive control
Larger P  → gentler control
```

This is one of the most common misunderstandings when technicians adjust industrial PID controllers.

---

## 4. What Auto-Tuning Actually Does

When Auto-Tuning starts, the controller temporarily stops using normal PID control.

Instead, it changes the control output temporarily to **ON/OFF control**.

This means the controller intentionally causes the process temperature to rise and fall around a target region.

The manual explains that when Auto-Tuning starts:

```text
The control output is temporarily changed to ON/OFF control.
The optimum PID constants are computed from the response data.
```

So Auto-Tuning does not calculate PID from theory alone.

It performs a real test:

```text
Apply output → observe PV response → create controlled oscillation → calculate PID
```

During Auto-Tuning, the temperature may:

- rise;
- overshoot slightly;
- fall;
- oscillate;
- repeat for one or more cycles;
- settle after PID values are calculated.

This is normal behavior during Auto-Tuning.

---

## 5. Why Is This Method Called Limit Cycle?

The manual says:

```text
This method is called limit cycle.
```

In control theory, a **limit cycle** is a sustained oscillation caused by the system and controller interacting in a repeated pattern.

During Auto-Tuning, the controller intentionally creates such an oscillation.

A simplified sequence looks like this:

```text
PV is below target → output turns ON
PV rises
PV exceeds target → output turns OFF
PV falls
PV becomes low again → output turns ON again
```

This creates a repeated oscillation around the tuning point.

From this oscillation, the controller can estimate:

- process gain;
- oscillation period;
- thermal delay;
- heating rate;
- cooling rate;
- overshoot tendency;
- response speed;
- thermal inertia.

In engineering language:

> Auto-Tuning identifies the dynamic characteristics of the controlled process by forcing a controlled oscillation and analyzing the resulting PV response.

In simple language:

> The controller shakes the system a little, watches how it reacts, and learns how to control it.

---

## 6. Auto-Tuning Is Not a Universal Solution

A common mistake is thinking:

> If I turn Auto-Tuning ON, the controller will automatically become perfect.

This is not true.

Auto-Tuning only produces PID values based on the condition in which the tuning was performed.

If the real operating condition is different, the PID values may not be optimal.

For example, in a coffee roaster:

- tuning with an empty drum is different from roasting with beans;
- tuning at low airflow is different from operating at high airflow;
- tuning at 160°C is different from operating at 220°C;
- tuning before the drum is thermally saturated gives different results;
- tuning with unstable gas pressure gives unreliable PID;
- tuning with a slow sensor gives different behavior;
- tuning with wrong output limits gives poor PID;
- tuning with a dirty burner or weak flame gives incorrect data.

The conclusion is:

> Auto-Tuning is only as good as the condition under which it is performed.

For best results, Auto-Tuning should be performed under conditions close to real operation.

---

## 7. AT.MD — Auto-Tuning Mode

The parameter **AT.MD** means:

```text
Auto-Tuning Mode
```

According to the manual, there are two types:

```text
1. Standard type Auto-Tuning
2. Low PV type Auto-Tuning
```

These two modes determine where the Auto-Tuning operation is performed.

---

## 8. Standard Type Auto-Tuning

In **Standard type Auto-Tuning**, the controller performs Auto-Tuning based on the actual SV.

Example:

```text
SV = 200°C
AT.MD = STD
```

The controller tunes around 200°C.

### 8.1 Advantage of Standard Type

The main advantage is accuracy at the actual operating point.

If the machine will normally operate around 200°C, tuning at 200°C gives PID values that are more representative of that condition.

This is useful when:

- the machine is already proven safe;
- the process can tolerate some oscillation;
- overshoot is acceptable;
- the technician wants better control near the real operating temperature.

### 8.2 Disadvantage of Standard Type

During Auto-Tuning, the controller intentionally creates oscillation.

Therefore, PV may rise above SV.

For sensitive systems, this may be risky.

Examples:

- coffee roasters;
- dryers with heat-sensitive material;
- furnaces with strict temperature limits;
- gas-fired systems with high thermal inertia;
- systems where overheating may damage parts or product.

Therefore, Standard Auto-Tuning should be used carefully.

---

## 9. Low PV Type Auto-Tuning

In **Low PV type Auto-Tuning**, the controller performs Auto-Tuning below the SV.

The manual says:

```text
Low PV type Auto-Tuning:
Auto-Tuning based on a value 10% lower than set value SV.
```

However, this sentence can be misunderstood.

Many people assume:

```text
Low PV tuning point = SV × 90%
```

For example:

```text
SV = 200°C

200 × 90% = 180°C
```

But the manual example shows that with a K-type thermocouple, when SV is 200°C, the actual Low PV tuning point is 160°C, not 180°C.

The reason is that the calculation is based on the sensor range lower limit.

---

## 10. FRL and FRH

The manual uses:

```text
FRL = Full Range Low
FRH = Full Range High
```

For a K-type thermocouple, the example range is:

```text
FRL = -200°C
FRH = 1370°C
```

The Low PV tuning point is calculated from FRL to SV.

The formula is:

```text
Low PV AT target = FRL + (SV - FRL) × 0.9
```

Example:

```text
FRL = -200°C
SV  = 200°C

Low PV AT target = -200 + (200 - (-200)) × 0.9
Low PV AT target = -200 + 400 × 0.9
Low PV AT target = -200 + 360
Low PV AT target = 160°C
```

So although the controller displays:

```text
SV = 200°C
```

the actual Auto-Tuning operation is performed at:

```text
160°C
```

---

## 11. Why Low PV Is Not Always SV × 90%

If FRL is 0°C:

```text
Low PV AT target = 0 + (200 - 0) × 0.9
Low PV AT target = 180°C
```

In this case, the result is 180°C.

But if FRL is -200°C:

```text
Low PV AT target = -200 + (200 - (-200)) × 0.9
Low PV AT target = 160°C
```

Therefore, the actual Low PV tuning point depends on the input range.

This is a critical detail.

A technician who does not understand FRL may believe that Low PV tuning is only 10% below SV, while in reality it may be much lower.

---

## 12. Standard Type vs Low PV Type

| Item | Standard Type | Low PV Type |
|---|---:|---:|
| Tuning point | Around SV | Below SV |
| Accuracy near real SV | Higher | Lower |
| Overshoot risk | Higher | Lower |
| Safety during first tuning | Lower | Higher |
| Best use case | Known and safe process | First tuning or high-risk system |
| Possible weakness | May overheat | PID may be less accurate at actual SV |

---

## 13. When to Use Standard Type

Use Standard Auto-Tuning when:

- the system is already mechanically and electrically verified;
- the sensor is reading correctly;
- the actuator works properly;
- the output direction is correct;
- the process can tolerate temporary oscillation;
- there is no sensitive product inside;
- the tuning temperature is close to normal operation;
- a technician is present;
- over-temperature protection is available.

For a coffee roaster, Standard AT may be used when:

```text
The drum is empty.
The machine is warmed up.
Airflow is stable.
Gas pressure is stable.
Burner response is verified.
The target tuning temperature is close to actual preheat/operation temperature.
```

---

## 14. When to Use Low PV Type

Use Low PV Auto-Tuning when:

- this is the first tuning attempt;
- the process response is unknown;
- overshoot is dangerous;
- burner or heater power is high;
- thermal inertia is large;
- the sensor is slow;
- you want a safer initial PID;
- you want to avoid tuning directly at high temperature.

However, remember:

> Low PV Auto-Tuning is safer, but the PID values may be less accurate at the final operating SV.

---

## 15. Auto-Tuning Start Conditions

According to the manual, Auto-Tuning can start in two ways.

### 15.1 Method 1 — Set AT to ON

In the **G.AT** group:

```text
AT = ON
```

The controller starts Auto-Tuning if the controller is in RUN state.

### 15.2 Method 2 — Press SET + UP

In operating state, press and hold:

```text
SET + UP
```

for more than 3 seconds.

The controller must be in:

```text
RUN state
```

Otherwise, Auto-Tuning will not execute correctly.

---

## 16. Auto-Tuning Sequence

The manual gives the Auto-Tuning sequence.

A proper technical sequence is:

```text
1. Select the SV number for Auto-Tuning.
2. Set the corresponding SV value.
3. Select AT.MD: Standard or Low PV.
4. Confirm the controller is in RUN state.
5. Start Auto-Tuning.
```

### 16.1 Select SV.NO

```text
SV.NO = selected set value number
```

Example:

```text
SV.NO = 1
```

This means the controller will use SV number 1.

### 16.2 Set the SV Value

Example:

```text
SV1 = 200°C
```

The selected SV becomes the basis for Auto-Tuning.

### 16.3 Select AT.MD

Choose:

```text
AT.MD = STD
```

or:

```text
AT.MD = LOW
```

### 16.4 Confirm RUN State

The controller must be in:

```text
RUN
```

If it is in STOP, change it to RUN first.

### 16.5 Execute Auto-Tuning

Either:

```text
Set AT = ON in G.AT group
```

or:

```text
Press and hold SET + UP for more than 3 seconds
```

When Auto-Tuning starts, the AT display indicator turns ON.

---

## 17. How to Stop Auto-Tuning

Auto-Tuning can be stopped in two ways.

### 17.1 Method 1 — Set AT to OFF

In the G.AT group:

```text
AT = OFF
```

### 17.2 Method 2 — Press MODE + UP

Press and hold:

```text
MODE + UP
```

for more than 3 seconds.

When Auto-Tuning terminates, the AT display indicator turns OFF.

---

## 18. What Happens When Auto-Tuning Completes?

If Auto-Tuning completes normally, the controller updates the PID parameters.

The manual states:

```text
If AT is completed normally, P, I, D values are reset to the same PID number as SV.NO.
```

This means:

```text
SV.NO = 1 → Auto-Tuning writes to PID No.1
SV.NO = 2 → Auto-Tuning writes to PID No.2
SV.NO = 3 → Auto-Tuning writes to PID No.3
```

This is very important.

If the wrong SV.NO is selected, the newly calculated PID values may be stored in the wrong PID number.

---

## 19. Special Case: Remote Input REM

The manual states:

```text
P, I, D values are reset to PID No.4 when set as remote input.
```

This means that when the controller uses remote input, the Auto-Tuning result is stored in:

```text
PID No.4
```

This may happen when SV is provided by:

- PLC;
- external HMI;
- analog remote setpoint;
- profile controller;
- supervisory control system;
- computer-based roasting software.

Therefore, when using remote input, always check PID No.4 after Auto-Tuning.

---

## 20. What Happens If Auto-Tuning Is Cancelled?

The manual says:

```text
The P, I, D values are not changed if AT is cancelled or forcibly terminated during AT.
```

This means:

```text
Auto-Tuning completed normally → PID values are updated
Auto-Tuning cancelled           → PID values remain unchanged
Auto-Tuning forcibly stopped    → PID values remain unchanged
```

This is a safety feature.

The controller does not overwrite the existing PID values with incomplete or unreliable tuning data.

---

## 21. Auto-Tuning Maximum Time and AT.E

The manual states that if Auto-Tuning does not finish within 24 hours, it is automatically cancelled.

When this happens:

- Auto-Tuning is terminated;
- emergency output is generated;
- the `[T]` icon keeps blinking;
- `AT.E` is displayed in the PV window.

`AT.E` means Auto-Tuning Error.

---

## 22. Why Auto-Tuning May Fail

Auto-Tuning fails when the controller cannot obtain a valid response from the process.

### 22.1 Output Does Not Affect the Process

The controller sends output, but PV does not respond.

Possible causes:

- relay not switching;
- SSR failure;
- heater disconnected;
- gas valve not opening;
- burner not firing;
- analog 0–10V wiring error;
- interlock blocking output;
- safety chain open;
- actuator not moving;
- wrong output type selected.

### 22.2 Sensor Problem

PV may be incorrect or too unstable.

Possible causes:

- wrong sensor type;
- wrong input configuration;
- broken thermocouple;
- reversed thermocouple polarity;
- loose sensor wiring;
- sensor installed in the wrong position;
- sensor response too slow;
- excessive signal noise;
- over-filtering of PV;
- sensor not exposed to the controlled heat zone.

### 22.3 Heating Power Too Weak

The controller applies output, but the process cannot heat fast enough.

Possible causes:

- burner too small;
- gas pressure too low;
- valve not opening enough;
- heater power insufficient;
- airflow removes too much heat;
- chamber heat loss too high;
- poor insulation;
- drum or process mass too large.

### 22.4 Output Limit Too Low

If output high limit is too low, the controller may not have enough authority.

Example:

```text
OHL = 20%
```

If the machine needs at least 50% output to heat properly, Auto-Tuning may fail or produce poor PID.

### 22.5 Process Too Slow

Some systems have very large thermal inertia.

Examples:

- large ovens;
- heavy drums;
- indirect heating systems;
- thick metal chambers;
- large water tanks;
- slow sensor placement.

If the process responds too slowly, Auto-Tuning may take too long.

### 22.6 External Disturbance During Auto-Tuning

Auto-Tuning needs stable conditions.

Disturbances can corrupt the tuning data.

Examples:

- door opened;
- airflow changed;
- gas pressure changed;
- product loaded during tuning;
- fan speed changed;
- operator manually changed output;
- environmental temperature changed strongly.

---

## 23. Auto-Tuning with Linear 0–10V Output

When using a linear analog output, such as:

```text
0–10V = 0–100%
```

Auto-Tuning does not tune voltage directly.

The correct control chain is:

```text
SV and PV → PID calculation → Output% → Analog voltage
```

The conversion is:

```text
Vout = Output% × 10 / 100
```

Examples:

```text
Output = 0%    → 0V
Output = 25%   → 2.5V
Output = 50%   → 5V
Output = 75%   → 7.5V
Output = 100%  → 10V
```

During Auto-Tuning, the controller may temporarily change the output in a more aggressive way than normal PID operation.

For a 0–10V burner or valve, this means the analog signal may move significantly.

Therefore, output limits are important.

---

## 24. OLL and OHL — Output Limits

The manual mentions:

```text
OLL = Output Low Limit
OHL = Output High Limit
```

These parameters limit the controller output.

For a 0–10V output:

```text
OLL = 0%
OHL = 100%
```

means:

```text
Minimum voltage = 0V
Maximum voltage = 10V
```

If you set:

```text
OLL = 20%
OHL = 80%
```

then:

```text
Minimum voltage = 2V
Maximum voltage = 8V
```

Formula:

```text
Vmin = OLL × 10 / 100
Vmax = OHL × 10 / 100
```

Example:

```text
OLL = 15%
OHL = 70%

Vmin = 1.5V
Vmax = 7.0V
```

For gas burners, output limits are critical.

If the controller is allowed to output 100%, the burner may receive 10V and go to full fire.

This may be unsafe during Auto-Tuning if the machine response is not yet known.

---

## 25. If the Device Uses 2–10V Instead of 0–10V

Some actuators or burners use:

```text
2–10V
```

In such systems:

```text
2V  = minimum command
10V = maximum command
```

Sometimes 0V may indicate signal failure or shutdown.

If the controller only provides 0–10V, one practical method is:

```text
OLL = 20%
OHL = 100%
```

because:

```text
20% of 10V = 2V
```

For a true 2–10V scaled signal, the formula is:

```text
Vout = 2 + Output% × 8 / 100
```

Examples:

```text
0%   → 2V
25%  → 4V
50%  → 6V
75%  → 8V
100% → 10V
```

Always verify how the receiving device interprets 0V, 2V, and 10V.

---

## 26. Proportional Action in Detail

The proportional action responds to the present error.

```text
Error = SV - PV
```

If the error is large, the proportional action produces a larger output change.

If the error is small, the proportional action produces a smaller output change.

With proportional band:

```text
Smaller P band → stronger response
Larger P band  → weaker response
```

### 26.1 If P Is Too Aggressive

Symptoms:

- PV rises quickly;
- PV overshoots SV;
- output changes sharply;
- the process oscillates;
- burner or heater output becomes unstable;
- in a coffee roaster, RoR may become unstable.

### 26.2 If P Is Too Weak

Symptoms:

- PV rises slowly;
- the process feels lazy;
- PV stays below SV for too long;
- the controller cannot correct errors quickly;
- recovery from disturbance is slow.

### 26.3 Correct P Behavior

A good P setting allows:

- reasonably fast approach to SV;
- acceptable overshoot;
- stable output;
- good disturbance response;
- no excessive oscillation.

---

## 27. Integral Action in Detail

Integral action responds to accumulated error over time.

If PV remains below SV for a long time, integral action increases output gradually to remove the remaining error.

Without integral action, a proportional controller may leave a steady-state error.

Example:

```text
SV = 200°C
PV stabilizes at 195°C
Error = 5°C
```

Integral action continues correcting until PV reaches SV.

### 27.1 Integral Time

In many industrial controllers:

```text
Smaller integral time = stronger integral action
Larger integral time  = weaker integral action
```

This is another common source of misunderstanding.

### 27.2 If I Is Too Strong

Symptoms:

- overshoot;
- long oscillation;
- output stays high too long;
- slow recovery after saturation;
- RoR surge in coffee roasting;
- temperature continues rising after output should have reduced.

### 27.3 If I Is Too Weak

Symptoms:

- PV does not fully reach SV;
- steady-state error remains;
- recovery is slow;
- the controller feels passive.

---

## 28. Derivative Action in Detail

Derivative action responds to the rate of change.

It acts like a predictive brake.

If PV is rising quickly toward SV, derivative action reduces output before PV overshoots.

Derivative action is useful in systems with large thermal inertia.

Examples:

- gas-fired ovens;
- coffee roasters;
- heavy metal drums;
- slow heating chambers;
- systems where temperature keeps rising after output is reduced.

### 28.1 If D Is Too Strong

Symptoms:

- output becomes noisy;
- analog 0–10V signal may fluctuate;
- burner command may shake;
- controller reacts to sensor noise;
- system becomes nervous.

Derivative action is sensitive to noise because noise often appears as rapid PV change.

### 28.2 If D Is Too Weak

Symptoms:

- overshoot increases;
- thermal inertia is not controlled well;
- PV reaches SV too fast and passes it;
- stabilization takes longer.

---

## 29. ARW — Anti Reset Wind-Up

The manual says:

```text
When the control output value reaches the limit value (OLH, OLL),
it executes the ARW operation to prevent overintegration.
```

ARW means:

```text
Anti Reset Wind-Up
```

In older control terminology, “reset” often means integral action.

So ARW means:

```text
Anti Integral Wind-Up
```

---

## 30. What Is Integral Wind-Up?

Assume:

```text
SV = 200°C
PV = 80°C
Error = 120°C
```

The controller increases output.

Soon output reaches its limit:

```text
Output = 100%
```

At this point, the controller cannot physically output more than 100%.

However, if the integral term continues accumulating error internally, the controller develops excessive stored integral action.

When PV finally approaches SV, output should decrease.

But because the integral term has accumulated too much, output remains high.

This causes:

- overshoot;
- slow recovery;
- long oscillation;
- output stuck at maximum;
- excessive heating.

This is called **integral wind-up**.

---

## 31. How ARW Helps

ARW prevents the integral term from growing excessively when output is already saturated.

If output reaches:

```text
OHL
```

ARW prevents further excessive positive integration.

If output reaches:

```text
OLL
```

ARW prevents further excessive negative integration.

Benefits:

- less overshoot;
- faster recovery;
- better stability;
- less output saturation;
- safer control during large error conditions.

---

## 32. ARW in Coffee Roasting

ARW is very important in coffee roasting.

When beans are charged into the drum:

- the measured temperature may drop;
- error becomes large;
- PID increases output;
- burner output may approach maximum;
- integral action starts accumulating.

Later, when the drum and beans begin recovering heat:

- PV rises;
- but integral action may still be high;
- burner output remains too high;
- RoR may surge;
- the roast profile becomes unstable.

ARW reduces this problem.

A practical explanation:

> ARW prevents the controller from emotionally overreacting during a long error condition.

---

## 33. ALPHA — Two-Degree-of-Freedom PID

The manual explains that ALPHA is used to adjust response characteristics to SV changes.

This is related to **two-degree-of-freedom PID control**.

A normal closed-loop control system must deal with two major situations:

```text
1. Response to set value change
2. Response to disturbance
```

---

## 34. Response to Set Value Change

Example:

```text
SV changes from 180°C to 200°C
```

The controller must bring PV from the old target to the new target.

If the controller is too aggressive:

- PV rises quickly;
- overshoot may occur;
- output may jump;
- oscillation may happen.

If the controller is too gentle:

- PV rises slowly;
- the process may lag behind;
- it may not follow the desired profile.

---

## 35. Response to Disturbance

A disturbance is an external influence that changes PV without changing SV.

In coffee roasting, disturbances include:

- charging green coffee into the drum;
- changing airflow;
- changing gas pressure;
- opening a sampling trier;
- environmental temperature changes;
- different bean moisture;
- different batch size;
- fan speed changes;
- drum thermal condition changes.

The controller must reject these disturbances and bring PV back toward SV.

---

## 36. Limitation of Normal PID

Normal PID is often called **one-degree-of-freedom PID**.

It uses the same PID behavior for:

```text
1. Following SV changes
2. Rejecting disturbances
```

This creates a compromise.

A very aggressive PID may follow SV quickly, but may overreact to disturbances.

A very gentle PID may handle disturbances smoothly, but may follow SV too slowly.

---

## 37. Purpose of Two-Degree-of-Freedom PID

Two-degree-of-freedom PID allows the controller to adjust the response to SV changes separately from disturbance response.

The manual states that this helps:

```text
Optimize the response to set value change
and obtain an appropriate response to disturbances.
```

ALPHA controls this behavior.

In simple words:

> ALPHA changes how calmly or aggressively the controller reacts when SV changes.

---

## 38. Meaning of ALPHA Values

The manual states:

```text
ALPHA = 0%   → same as normal PID
ALPHA = 100% → may take a long time to reach normal state
```

A practical interpretation:

| ALPHA | Behavior When SV Changes | Speed | Overshoot | Smoothness |
|---:|---|---:|---:|---:|
| 0% | Like normal PID | Fast | Higher | More aggressive |
| 50% | Balanced | Medium | Lower | Smoother |
| 100% | Very gentle | Slow | Low | Very smooth |

From the graph in the manual:

- Alpha 0 rises quickly but overshoots more;
- Alpha 50 gives a balanced response;
- Alpha 100 rises more slowly and gently.

---

## 39. ALPHA in Coffee Roasting

In a coffee roaster, ALPHA affects how the burner output behaves when the target temperature changes.

If ALPHA is too low:

- controller reacts sharply to SV changes;
- 0–10V burner signal may rise quickly;
- ET may overshoot;
- RoR may become unstable;
- beans may receive heat shock.

If ALPHA is too high:

- controller reacts too slowly;
- machine may feel lazy;
- profile following may be poor;
- roast may lack energy;
- the process may become flat or baked.

A good starting point is often a moderate ALPHA value.

For example:

```text
ALPHA = 50%
```

Then observe the response and adjust.

---

## 40. Relationship Between ALPHA and n.I

The manual says that if:

```text
n.I = 0 / OFF
```

in the G.CTL group:

- ALPHA is internally set to 0;
- ALPHA is not visible;
- MR parameter becomes visible.

If:

```text
n.I is not 0 / OFF
```

then:

- ALPHA returns to the previously set ALPHA value;
- MR parameter is not visible;
- ALPHA parameter is visible.

This means the controller changes available parameters depending on the selected control algorithm mode.

To use ALPHA, the controller must be in a mode that supports two-degree-of-freedom PID.

---

## 41. n.PID — PID Number

The manual states:

```text
If n.PID is selected, the PID parameter of the corresponding PID number is displayed.
```

This means the controller can store multiple PID parameter sets.

Example:

```text
PID No.1: P1, I1, D1
PID No.2: P2, I2, D2
PID No.3: P3, I3, D3
PID No.4: P4, I4, D4
```

Each PID number can be used for a different operating condition.

---

## 42. Heating PID and Cooling PID

The manual states:

```text
n.P, n.I, n.D are heating PID parameters.
n.Pc, n.Ic, n.Dc are cooling PID parameters.
```

So:

```text
n.P, n.I, n.D
```

belong to heating control.

And:

```text
n.Pc, n.Ic, n.Dc
```

belong to cooling control.

Cooling parameters are displayed when:

```text
G.OUT > CNT2 is not NONE
```

and the product has the OUT2 option.

---

## 43. Why Multiple PID Numbers Are Useful

A thermal system does not behave the same at all temperatures.

In a coffee roaster:

At low temperature:

- drum is still cold;
- heat loss is high;
- response is slow;
- more burner power is needed.

At medium temperature:

- drum is warmer;
- response becomes more stable;
- heat transfer improves.

At high temperature:

- drum stores significant heat;
- small output changes can cause strong temperature changes;
- overshoot risk is higher.

Therefore, one PID set may not be ideal for all regions.

A practical structure may be:

```text
PID No.1 = low-temperature preheat zone
PID No.2 = medium operating zone
PID No.3 = high-temperature zone
PID No.4 = remote input / external profile control
```

---

## 44. Recommended Auto-Tuning Record Sheet

Before and after Auto-Tuning, record the following:

```text
Date:
Machine:
Sensor type:
Control loop:
SV.NO:
SV value:
AT.MD:
FRL:
FRH:
Calculated Low PV tuning point:
Output type:
OLL:
OHL:
Control action:
Current P:
Current I:
Current D:
New P after AT:
New I after AT:
New D after AT:
ALPHA:
ARW:
Airflow condition:
Gas pressure:
Machine load:
Drum condition:
Operator note:
```

This prevents confusion and allows rollback if the new PID is poor.

---

## 45. Pre-Auto-Tuning Checklist

Before starting Auto-Tuning, verify the following.

### 45.1 Sensor Check

- Correct sensor type selected;
- PV reading is reasonable;
- sensor polarity is correct;
- sensor wiring is tight;
- sensor is placed in the correct control zone;
- PV signal is not noisy;
- PV filter is not excessive;
- sensor response is not too delayed.

### 45.2 Output Check

- Correct output type selected;
- relay, SSR, 0–10V, or 4–20mA is configured correctly;
- output wiring is correct;
- final control element responds;
- burner or heater actually changes heat input;
- interlocks are not blocking output;
- safety circuit is active;
- output limits are reasonable.

### 45.3 Control Direction Check

For heating control:

```text
PV below SV → output should increase
```

For cooling control:

```text
PV above SV → cooling output should increase
```

If the direction is wrong, Auto-Tuning must not be started.

Wrong control direction can make the controller drive the system away from the target.

### 45.4 Safety Check

- Emergency stop works;
- over-temperature protection works;
- flame safeguard works if using gas;
- fan or exhaust system is running;
- gas pressure is stable;
- no sensitive product is inside;
- technician is present;
- output maximum is safe;
- process can tolerate temporary oscillation.

---

## 46. What to Watch During Auto-Tuning

During Auto-Tuning, monitor:

- PV trend;
- output trend;
- burner behavior;
- voltage output if using 0–10V;
- overshoot;
- heating rate;
- alarm status;
- AT indicator;
- gas pressure;
- airflow;
- flame stability;
- abnormal noise or vibration.

Stop Auto-Tuning if:

- PV rises too fast;
- PV exceeds safe limit;
- burner behaves abnormally;
- output jumps dangerously;
- alarm appears;
- sensor reading becomes unstable;
- the machine condition becomes unsafe.

---

## 47. After Auto-Tuning

After Auto-Tuning completes:

1. Check that AT indicator is OFF.
2. Confirm no `AT.E` error exists.
3. Read the new P, I, D values.
4. Confirm which PID number was updated.
5. Save or write down the new values.
6. Run a controlled test.
7. Observe overshoot, settling time, and output smoothness.
8. Adjust manually if needed.

Auto-Tuning gives a starting point, not always a perfect final result.

A skilled technician usually:

```text
Runs AT → observes behavior → manually fine-tunes → tests again → saves final values
```

---

## 48. Practical Interpretation of Auto-Tuning Result

After AT, judge the result by observing the process.

### 48.1 If PV Overshoots Too Much

Possible actions:

- increase proportional band;
- increase integral time;
- reduce derivative time only if D is causing noise;
- increase ALPHA if overshoot happens after SV change;
- reduce OHL;
- use Low PV mode for safer tuning;
- check thermal inertia.

### 48.2 If PV Is Too Slow

Possible actions:

- decrease proportional band;
- decrease integral time carefully;
- check if OHL is too low;
- check if burner/heater is too weak;
- check airflow heat loss;
- check sensor position;
- reduce ALPHA if response to SV change is too slow.

### 48.3 If Output Is Noisy

Possible actions:

- reduce derivative action;
- increase PV filtering slightly;
- check sensor noise;
- check grounding and shielding;
- check analog output wiring;
- check actuator deadband;
- avoid excessive D.

### 48.4 If PV Never Reaches SV

Possible actions:

- check heater capacity;
- check OHL;
- check gas pressure;
- check output wiring;
- check control direction;
- strengthen integral action;
- check if cooling or airflow is too strong.

---

## 49. Special Notes for Coffee Roasters

Coffee roasters are difficult PID systems because they are highly dynamic and nonlinear.

Reasons:

- drum stores heat;
- beans absorb heat;
- airflow changes heat transfer;
- gas pressure affects burner response;
- charge temperature changes the initial condition;
- batch size changes system load;
- bean moisture changes energy demand;
- sensor placement affects PV delay;
- roasting phases require different heat behavior.

Therefore, Auto-Tuning must be used carefully.

Recommended approach:

```text
1. Tune with empty and thermally stable machine first.
2. Use safe output limits.
3. Start with Low PV mode if unsure.
4. Record P/I/D values.
5. Test with real operating conditions.
6. Manually refine PID.
7. Avoid running AT during an important roast batch.
```

---

## 50. Auto-Tuning With SV Ramp and 0–10V Output

If the controller also uses an SV ramp function, the control structure is:

```text
SV ramp → PID calculation → Output% → 0–10V analog signal
```

This means the ramp changes the target temperature gradually. It does not directly ramp the voltage.

Example:

```text
RM.UP = 60°C
UP.TM = 1 minute
```

This means:

```text
SV rises at 60°C/minute
SV rises at 1°C/second
```

The PID then calculates the output percentage required to make PV follow this moving SV.

The analog output is only the physical representation of PID output:

```text
Vout = Output% × 10 / 100
```

Therefore:

> SV Ramp makes the target smoother. PID calculates the required output. The 0–10V signal represents that output. SV Ramp does not guarantee that the voltage itself will increase linearly.

If a truly linear voltage ramp is required, the controller must have an output ramp, MV rate limit, analog slew-rate limit, or an external PLC/analog signal conditioner must be used.

---

## 51. The Most Important Concept

Auto-Tuning is not the final intelligence of the controller.

It is only an identification procedure.

The controller performs an experiment, calculates P/I/D, and stores the result.

The quality of the result depends on:

- correct sensor;
- correct output;
- correct control direction;
- stable process;
- reasonable SV;
- proper AT.MD selection;
- proper output limits;
- similarity between tuning condition and real operating condition.

Final summary:

```text
AT identifies the process.
PID controls the process.
ARW protects the integral term during output saturation.
ALPHA adjusts response to SV changes.
n.PID allows multiple PID sets for different operating regions.
OLL and OHL limit output authority.
0–10V is only the physical output signal corresponding to 0–100% controller output.
```

A professional way to understand it:

> Auto-Tuning teaches the controller how the machine reacts. PID decides how to respond to error. ARW prevents excessive integral accumulation. ALPHA shapes the response when the setpoint changes. Output limits protect the system from excessive command. The technician's job is to choose the right tuning condition, verify the result, and refine it according to real operation.

