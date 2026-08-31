// content-en.jsx — chapter "Automatic Preheating (Warm-up)" — English edition

// ═══════════════════ COVER ═══════════════════
coverImage = "may-rang-auto-bia.png";   // ảnh máy Auto
COVER("OTL Roaster",
      "User Manual",
      "Automatic Preheating\n(Preheat / Warm-up)",
      "OTL Auto coffee roaster \u2013 HMI control panel",
      "Version 1.0 \u2013 08/2026          Copyright (c) O Tesla Industry CO., Ltd");

// ═══════════════════ MANUFACTURER INFORMATION ═══════════════════
chapterHeader = "Manufacturer information";
addPage();
COMPANY("O TESLA INDUSTRY CO., LTD",
        "Manufacturer of OTL industrial coffee roasters",
[["Office", "44 N5 Street, Tan Phuoc Quarter, Tan Dong Hiep Ward, Ho Chi Minh City, Vietnam"],
 ["Factory", "398/33 DT743B, Dong Thanh Quarter, Tan Dong Hiep Ward, Ho Chi Minh City, Vietnam"],
 ["Telephone", "+84 936 198 938"],
 ["Email", "otesla.vn@gmail.com"],
 ["Tax code", "0314844413"],
 ["Document", "User Manual – Automatic Preheating (Preheat / Warm-up)"],
 ["Version", "1.0 – 08/2026"],
 ["Applies to", "OTL Auto coffee roasters with the automatic preheating function"]],
"IMPORTANT NOTICE",
"This document is intended to help the operator run the machine in a systematic, orderly and safe manner. The operator must be in good health, comply with all local fire and explosion safety regulations and follow the instructions given in this document.\n• Read the whole document carefully before operating the machine.\n• Keep this document close to the machine so it can be consulted immediately in any situation.\n• The content may change with the version of the control software. Contact O Tesla for the latest revision.");

// ═══════════════════ TABLE OF CONTENTS (reserved, drawn at the end) ═══════════════════
chapterHeader = "Table of contents";
TOCRESERVE();


// ═══════════════════ INTRODUCTION ═══════════════════
chapterHeader = "Automatic Preheating";
addPage();

H1("Automatic Preheating (Warm-up)");

P("Before each roasting day, the drum body and the entire cast-iron mass of the machine must be brought up to the correct working temperature. Starting a batch while the machine is still cold always leaves the first batch short of heat: the beans receive a weak thermal shock on charging, the time to first crack stretches out, and the first batch never matches the ones that follow.");

P("On earlier machines the operator had to light the burner manually, watch the clock for 15 \u2013 30 minutes and adjust the gas by hand so the temperature would rise at a reasonable rate. This method depends entirely on the skill and memory of the individual operator.");

P("The OTL Auto roaster provides an automatic preheating function. The operator only enters the desired temperature and the preheating time in the Preheat window, then presses START. The machine purges the combustion chamber, ignites the burner, adjusts the gas level automatically to bring the bean temperature (BT) up to the set value, and then holds that temperature stable within \u00b12 \u00b0C until the set time has elapsed.");

IMGC("main.bmp", 400, "Figure 1 \u2013 Main screen of the OTL Auto roaster.",
[[0.004, 0.850, 0.090, 0.147, "1"],
 [0.812, 0.238, 0.180, 0.175, "2"],
 [0.812, 0.660, 0.180, 0.105, "3"],
 [0.812, 0.765, 0.180, 0.100, "4"]],
["1  Setup button \u2013 opens the auxiliary function page, from which the Preheat window is reached.",
 "2  Bean temperature (BT) and exhaust temperature (ET) \u2013 the two values to watch while preheating.",
 "3  Burner \u2013 gas level of the burner.",
 "4  Airflow \u2013 speed of the exhaust fan."]);

H3("Contents of this chapter");
BUL([
"Safety warnings that must be read before operating the function.",
"Operating principle and the six stages of the preheating cycle.",
"Conditions to be checked before starting.",
"Step-by-step operating instructions on the HMI.",
"The self-tuning function during the first run.",
"Troubleshooting table.",
"Appendices with technical parameters."
]);

// ═══════════════════ SAFETY ═══════════════════
chapterHeader = "Automatic Preheating \u2013 Safety";
addPage();
H1("1  Safety");

P("The automatic preheating function directly controls the gas valve and the burner flame. The operator must read and understand all of the warnings below before using it.");

SAFETY("nguyhiem", "DANGER \u2013 Risk of gas explosion",
"Leaking gas accumulating inside the combustion chamber can explode, causing death or serious injury.\n\u2022 Before pressing START, inspect the complete gas line and gas valve and make sure there is no smell of gas in the area.\n\u2022 Never disable, remove or obstruct the flame sensor. The machine relies on this sensor to confirm that the flame is present.\n\u2022 If the machine reports a failed ignition, CLOSE THE MANUAL GAS VALVE and find the cause before trying again. Never restart the ignition repeatedly.");

SAFETY("canhbao", "WARNING \u2013 Hot surfaces",
"During and after preheating, the drum body, the sampler, the exhaust duct and the burner assembly exceed 200 \u00b0C. Contact will cause severe burns.\n\u2022 Always wear heat-resistant gloves when working near these parts.\n\u2022 Keep flammable material (packaging, cloths, plastic containers) at least 1 m away from the machine.");

SAFETY("canhbao", "WARNING \u2013 The machine starts equipment by itself",
"While preheating is running, the machine opens the gas valve, adjusts the gas level and adjusts the exhaust fan without any operator action.\n\u2022 Never reach into the drum, the feed hopper or the cooling tray while the preheating cycle is running.\n\u2022 To stop immediately: switch the preheating function off in the Preheat window, or press the EMERGENCY STOP button.");

SAFETY("thantrong", "CAUTION \u2013 The exhaust fan must be running",
"The exhaust fan must run throughout the preheating cycle to remove combustion gases. If the fan fails or the exhaust duct is blocked, combustion gases will enter the workshop.");

SAFETY("luuy", "NOTICE \u2013 Do not load coffee while preheating",
"The drum must remain empty for the whole preheating cycle. Coffee left in the drum during this stage will scorch on the surface and the batch is lost.");

// ═══════════════════ PRINCIPLE ═══════════════════
chapterHeader = "Automatic Preheating \u2013 Operating principle";
addPage();
H1("2  Operating principle");

P("The preheating cycle consists of six consecutive stages. The machine moves from one stage to the next according to the measured temperature and the flame sensor signal; no operator action is required.");

STATEFLOW([
["Idle", "The machine takes over gas and airflow control and closes the gas valve to 0 %.", "a few seconds"],
["Cooling down", "Runs only if the machine is hotter than the set value. Airflow 60 %, gas off, waiting for the temperature to drop.", "variable"],
["Chamber purge", "Airflow 60 % clears residual gas from the combustion chamber before any spark.", "8 seconds"],
["Ignition", "Gas valve opens, gas 30 % and airflow 30 %, waiting for the flame signal. Up to three attempts.", "3 \u00d7 60 seconds"],
["Heating up", "The PID controller raises and lowers the gas to bring the bean temperature to the set value without overshoot.", "10 \u2013 20 minutes"],
["Holding", "The set temperature is reached. The machine holds it within \u00b12 \u00b0C until the time expires.", "until time is up"]
]);

P("Two protective layers are active in parallel during every stage:");
BUL([
"If the bean temperature exceeds the set value by 15 \u00b0C, the machine cuts the gas to 0 % and opens the airflow fully until the temperature falls. The preheating cycle continues.",
"If the difference between exhaust temperature (ET) and bean temperature (BT) exceeds 160 \u00b0C, the machine assumes one of the two sensors has failed, aborts the cycle immediately, closes the gas valve and reports a fault."
]);

// ═══════════════════ BEFORE STARTING ═══════════════════
chapterHeader = "Automatic Preheating \u2013 Preparation";
addPage();
H1("3  Checks before starting");

P("Complete every item below before each preheating cycle. Skipping an item may spoil the cycle or create a hazard.");

TABLE(["", "Item to check", "Requirement"],
[
["\u25A1", "Roasting drum", "Completely empty, no beans left from the previous batch."],
["\u25A1", "Discharge and charge doors", "Closed. Cylinders in the closed position."],
["\u25A1", "Manual gas valve", "Fully open. Gas pressure within the range specified for the burner."],
["\u25A1", "Smell of gas", "No smell of gas anywhere around the machine."],
["\u25A1", "Exhaust fan and duct", "Fan running smoothly, duct clear, cyclone cleaned."],
["\u25A1", "BT and ET sensors", "Both showing plausible values on screen, differing by no more than 160 \u00b0C."],
["\u25A1", "Emergency stop button", "Released, safety circuit reset (green lamp lit)."],
["\u25A1", "Area around the machine", "No flammable material within 1 m."]
], [24, 176, 235.28]);

SAFETY("thantrong", "CAUTION \u2013 Sensors reading far apart",
"If BT and ET already differ considerably while the machine is cold, one of the two probes or its signal wiring is almost certainly faulty. Do not run preheating until the fault has been repaired.");

// ═══════════════════ OPERATING STEPS ═══════════════════
chapterHeader = "Automatic Preheating \u2013 Operation";
addPage();
H1("4  Step-by-step operation");

H2(1, "Switch on power and reset the safety circuit");
STEPIMG(1, "Turn the main power switch to ON.", "cong-tac-nguon.png", "", 66);
STEPIMG(2, "Turn the emergency stop button clockwise to release it.", "nut-dung-khan.png", "", 58);
STEPIMG(3, "Press the Reset Circuit button to energise the control circuit. The green lamp on the button lights up.", "nut-reset-circuit.png", "", 46);

H2(2, "Open the Preheat window");
STEPIMG(4, "On the main screen, press the Setup button in the lower left corner.", "nut-setup.png", "", 40);
STEPIMG(5, "On the auxiliary function page, press the Preheat button.", "nut-preheat-menu.png", "", 110);

IMGC("config page.bmp", 330, "Figure 2 \u2013 Auxiliary function page. The Preheat button is in the upper row.",
[[0.494, 0.238, 0.250, 0.140, "1"]],
[]);

// ═══════════════════ PREHEAT WINDOW ═══════════════════
H2(3, "Set the temperature and the time");

IMGC("preheat.bmp", 300, "Figure 3 \u2013 The Preheat window.",
[[0.015, 0.020, 0.330, 0.190, "1"],
 [0.660, 0.020, 0.325, 0.190, "2"],
 [0.025, 0.280, 0.465, 0.235, "3"],
 [0.505, 0.280, 0.470, 0.235, "4"],
 [0.025, 0.525, 0.950, 0.170, "5"],
 [0.025, 0.735, 0.950, 0.225, "6"]],
["1  Bean temp \u2013 the current bean temperature of the machine.",
 "2  Target \u2013 the temperature the machine is working towards.",
 "3  Set temp \u2013 preheating temperature, adjusted with the \u2013 and + keys.",
 "4  Set time \u2013 preheating time in minutes.",
 "5  Process \u2013 progress bar of the preheating cycle.",
 "6  START \u2013 starts and ends the preheating cycle."]);

STEP(6, "Set Set temp with the \u2013 and + keys to the required bean temperature. Typical values: 180 \u2013 200 \u00b0C for green coffee, 150 \u2013 170 \u00b0C for cocoa.");
STEP(7, "Set Set time to the total preheating time in minutes. Typical values: 20 \u2013 30 minutes. When this time has elapsed the machine shuts the flame off and ends the cycle automatically.");

PI("Note: the preheating time is counted from successful ignition; the chamber purge is not included.");

H2(4, "Start preheating");
STEPIMG(8, "Press START. The machine begins the cycle: chamber purge followed by ignition.", "nut-start-preheat.png", "", 220);
STEP(9, "Stay and watch until ignition succeeds and the bean temperature starts to rise. From this point the machine runs fully automatically; the operator may carry out other work in the workshop but must not leave the machine area.");

SAFETY("canhbao", "WARNING \u2013 Do not leave the machine during ignition",
"Remain at the machine throughout the chamber purge and the ignition stage. Leave the position only after the bean temperature is rising steadily, confirming a stable flame.");

// ═══════════════════ MONITORING ═══════════════════
chapterHeader = "Automatic Preheating \u2013 Monitoring";
addPage();
H1("5  Monitoring during preheating");

P("The table below shows what the machine is doing at each stage, what appears on the screen and what the operator has to watch.");

TABLE(["Stage", "What the machine does", "On the screen", "Operator"],
[
["Cooling down", "Gas 0 %, airflow 60 %, waiting for the temperature to fall to the set value.", "Bean temp falling, Burner at 0.", "Wait. Do not switch off the exhaust fan."],
["Purge", "Airflow 60 % for 8 seconds, gas valve still closed.", "Airflow rising, Burner at 0.", "Stay and watch."],
["Ignition", "Gas valve opens, gas 30 %, airflow 30 %, waiting for the flame signal.", "Burner shows 30 %, Bean temp starts to rise.", "Watch. Switch off at once if gas is smelled."],
["Self-tuning", "First run at each temperature level only. The machine oscillates the temperature around a lower level to measure the behaviour of the roaster.", "The Process bar advances with each measured cycle.", "Wait, do not adjust anything by hand."],
["Heating up", "The PID controller raises and lowers the gas according to progress.", "Bean temp rising steadily, Burner changing continuously.", "May carry out other work near the machine."],
["Holding", "Holds the temperature within \u00b12 \u00b0C of the set value.", "Bean temp tracking Target, Burner low and steady.", "Prepare the coffee for the first batch."]
], [70, 150, 118, 97.28]);

PI("While preheating is running, the gas and airflow levels shown on the main screen are set by the machine. Turning the potentiometers or adjusting by hand has no effect until the cycle ends.");

// ═══════════════════ SELF-TUNING ═══════════════════
chapterHeader = "Automatic Preheating \u2013 Self-tuning";
addPage();
H1("6  Self-tuning during the first run");

P("Every roaster has its own thermal behaviour: mass of cast iron, burner output, length of the exhaust duct, quality of the gas. For this reason the machine does not use a fixed set of control parameters but measures the behaviour of its own roaster and calculates the matching parameters.");

H3("When the machine tunes itself");
BUL([
"The first time preheating is run at a new temperature level.",
"After the holding result of the previous run was rated unsatisfactory (deviation greater than \u00b12 \u00b0C).",
"The machine must be cold enough. If it is still hot, the tuning step is skipped and fallback parameters are used."
]);

H3("What happens during tuning");
P("The machine switches the gas alternately on and off around a temperature level below the set value, making the bean temperature oscillate. From the amplitude and the period of that oscillation the machine calculates three control coefficients and stores them on the memory card. This takes about 5 \u2013 10 minutes and runs only once for each temperature level.");

PI("Note: if tuning has not finished within 10 minutes, the machine skips it and continues heating with the fallback parameters. This is not a fault.");

H3("After tuning is complete");
BUL([
"The machine stores up to 8 different temperature levels. Two levels within 15 \u00b0C of each other count as the same level.",
"From the second run onwards the machine reuses the stored parameters and goes straight to the heating stage.",
"At the end of every preheating cycle the machine rates its own stability. If the result is unsatisfactory it deletes the parameters for that level and tunes again on the next run. No operator action is required."
]);

// ═══════════════════ ENDING ═══════════════════
chapterHeader = "Automatic Preheating \u2013 Ending the cycle";
addPage();
H1("7  Ending the cycle and starting to roast");

H3("Automatic end");
P("When the time entered in Set time has elapsed, the machine shuts off the flame, closes the gas valve, returns gas and airflow control to the operator and switches the preheating function off by itself. The drum keeps turning and the exhaust fan keeps running.");

H3("Stopping early by hand");
STEP(1, "Open the Preheat window again and switch the preheating function off. The machine closes the gas valve immediately and aborts the cycle.");
STEP(2, "Wait for the temperature to settle before carrying out any other operation.");

SAFETY("luuy", "NOTICE \u2013 Charge the first batch promptly",
"Charge the first batch within 5 minutes after preheating ends. If left longer, the cast-iron mass cools down and the first batch will still be short of heat, exactly as if no preheating had been performed.");

H3("Moving on to roasting");
BUL([
"Check that Bean temp on the main screen matches the intended charge temperature.",
"Load the coffee into the hopper and continue as described in the chapter Roaster operation.",
"If switching to automatic roasting, confirm that the correct roasting profile is selected."
]);

// ═══════════════════ TROUBLESHOOTING ═══════════════════
chapterHeader = "Automatic Preheating \u2013 Troubleshooting";
addPage();
H1("8  Troubleshooting");

TABLE(["Symptom", "Possible cause", "Remedy"],
[
["The machine reports failed ignition after three attempts.",
 "Gas supply empty or manual gas valve still closed. Ignition electrode dirty, worn or with the wrong gap. Flame sensor dirty or wire broken. Ignition airflow too strong and blowing the flame out.",
 "Close the manual gas valve. Check the gas pressure, clean the ignition electrode and the flame sensor, reset the gap according to the burner documentation. Only then try again."],
["The machine reports a temperature deviation fault and closes the gas.",
 "The difference between exhaust and bean temperature exceeded 160 \u00b0C. Usually a probe has slipped out of position, a wire is broken or a transmitter has failed.",
 "Check both probes and their signal wiring. Compare the two values with the machine cold: a large difference indicates a fault."],
["The temperature overshoots the set value, then the machine cuts the gas and opens the airflow fully.",
 "This is the anti-overshoot protection, not a fault. It typically occurs when residual heat remains from a previous batch or the parameters have not yet been re-tuned.",
 "Let the machine handle it. If it repeats often, run preheating with the machine fully cold so that it can tune itself again."],
["The temperature rises very slowly or never reaches the set value.",
 "Low gas pressure, dirty burner, exhaust fan opened too far and drawing all the heat away, or charge and discharge doors not sealing.",
 "Check the gas pressure and clean the burner. Check the door seals. Check the exhaust duct and cyclone for blockages."],
["The temperature swings widely around the set value.",
 "The parameters for this temperature level are not yet suitable.",
 "The machine detects this and will tune itself again on the next preheating run. If the problem persists, contact O Tesla service."],
["Tuning takes a long time and is then skipped.",
 "The machine is still hot, so the temperature cannot fall far enough for the oscillation to be measured.",
 "Not a fault. For correct tuning, run preheating with the machine fully cold at the start of the shift."],
["START is pressed but nothing happens.",
 "The safety circuit has not been reset, the emergency stop is still pressed, or the machine is busy with another cycle.",
 "Reset the safety circuit, check the emergency stop button and make sure no roasting batch is running."],
["Ignition takes longer than usual on machines with a premix burner.",
 "Premix burners ignite slowly, taking roughly 40 seconds to catch.",
 "Normal behaviour. Check that the Premix burner switch on the Config page matches the burner actually fitted."]
], [110, 165, 160.28]);

// ═══════════════════ APPENDIX A ═══════════════════
chapterHeader = "Automatic Preheating \u2013 Appendix";
addPage();
H1("Appendix A  Technical parameters");

P("The values below are preset in the control software. Only technicians authorised by O Tesla may change them.");

TABLE(["Parameter", "Value", "Meaning"],
[
["Chamber purge time", "8 seconds", "Clears residual gas before any spark."],
["Airflow during purge and cooling", "60 %", "Exhaust fan level during the preparation stages."],
["Gas level for ignition", "30 %", "Gas level used to light the burner."],
["Airflow during ignition", "30 %", "Keeps the ignition flame from being blown out."],
["Flame signal timeout", "60 seconds", "Premix burner: 65 seconds."],
["Ignition attempts", "3", "After three attempts a fault is reported and the gas closed."],
["Band counted as temperature reached", "\u00b13 \u00b0C", "Within this band the machine switches to holding."],
["Stability target while holding", "\u00b12 \u00b0C", "Outside this band the machine will tune itself again."],
["Anti-overshoot gas cut-off", "set value + 15 \u00b0C", "Gas cut, airflow opened fully."],
["Sensor deviation abort limit", "160 \u00b0C", "Difference between ET and BT."],
["Stored temperature levels", "8", "Two levels within 15 \u00b0C count as one."],
["Maximum tuning time", "10 minutes", "After this the fallback parameters are used."]
], [175, 100, 160.28]);

// ═══════════════════ APPENDIX B ═══════════════════
chapterHeader = "Automatic Preheating \u2013 Appendix";
addPage();
H1("Appendix B  Selecting the burner type");

P("The machine uses different ignition parameters for the two burner types. Selecting the wrong type causes failed ignition reports even though the burner itself is in good order.");

IMGC("config.bmp", 330, "Figure 4 \u2013 Config page. The Premix burner switch is in the lower left row.",
[[0.340, 0.735, 0.155, 0.215, "1"]],
["1  Premix burner \u2013 switch on for premix burners (gas and air mixed in advance), off for conventional burners."]);

TABLE(["Burner type", "Premix burner switch", "Flame signal timeout"],
[
["Conventional (diffusion) burner", "OFF", "60 seconds"],
["Premix burner", "ON", "65 seconds"]
], [175, 130, 130.28]);

SAFETY("thantrong", "CAUTION \u2013 Change only when the burner is replaced",
"This switch must match the burner actually fitted to the machine. Operators must not change it; only a technician changes it when the burner is replaced.");

RULE();
PI("This document applies to OTL Auto coffee roasters equipped with the automatic preheating function. For technical enquiries please contact O Tesla Industry Co., Ltd.");

TOCDRAW("Table of contents", "PH-");
// ═══════════════════ EXPORT ═══════════════════
var base = "F:/Project/112_Quanly/122_Manual_AI/preheat-vi/build/";
var ai = new File(base + "Preheat-Warm-up-Manual-EN.ai");
var saveOpt = new IllustratorSaveOptions();
doc.saveAs(ai, saveOpt);

var pdf = new File(base + "Preheat-Warm-up-Manual-EN.pdf");
var po = new PDFSaveOptions();
po.preserveEditability = false;
doc.saveAs(pdf, po);

var msg = "OK pages=" + doc.artboards.length;
if (missing.length > 0) msg += " | thieu anh: " + missing.join(", ");
msg;
