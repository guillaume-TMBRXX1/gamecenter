# GRIDIRON SIM — PLAYBOOK EXPANSION DATABASE V0.1

> Supplementary football knowledge base for Claude.
>
> **Purpose:** enrich GridironSim with structured NFL football knowledge without modifying the existing V0.1 architecture, franchises, Playbook V0.1 data, or QB Reads 1-2-3 system.
>
> **Status:** reference / expansion database. Claude decides later what becomes active data and what remains reserve.

---

## 00 — NON-NEGOTIABLE RULES

1. Do **not** modify the existing GridironSim architecture unless explicitly requested.
2. Do **not** assign these formations/concepts to current franchises automatically.
3. Do **not** replace existing Playbook V0.1 data.
4. Do **not** redesign the existing QB Reads 1-2-3 system.
5. Do **not** collapse concepts into simplistic names or probabilities.
6. Treat this document as a supplementary football knowledge base.
7. A football concept is not the same thing as a play instance.
8. A formation is a structural container; a concept is the football action.
9. Compatibility is not play frequency.
10. A valid play can fail; a successful play can result from a bad call.
11. All outcomes must emerge from interaction and execution rather than hard-coded guarantees.

---

# 01 — MASTER FOOTBALL MODEL

A complete play can be represented as:

```text
GAME CONTEXT
→ PERSONNEL
→ FORMATION
→ ALIGNMENT
→ MOTION / SHIFT
→ CONCEPT
→ VARIANT
→ PLAYER ASSIGNMENTS
→ ROUTES / BLOCKING / PROTECTION
→ DEFENSIVE FRONT
→ COVERAGE
→ PRESSURE
→ MATCHUPS
→ PLAYER ARCHETYPES
→ EXECUTION
→ OUTCOME
```

Core separation:

```text
PLAY CALL ≠ PLAY EXECUTION ≠ PLAY OUTCOME
```

---

# 02 — PERSONNEL

## 02.1 Core personnel

| Personnel | RB | TE | WR | Typical identity |
|---|---:|---:|---:|---|
| 10 | 1 | 0 | 4 | Spread / pass |
| 11 | 1 | 1 | 3 | Most versatile |
| 12 | 1 | 2 | 2 | Balanced / run + PA |
| 21 | 2 | 1 | 2 | Pro / I / split |
| 22 | 2 | 2 | 1 | Heavy / short yardage |

Personnel is a structural constraint, not a play-call frequency.

---

# 03 — FORMATION DATABASE

## 03.1 Existing GridironSim V0.1 formations — DO NOT ALTER

Offense:

```text
SHOTGUN
SINGLEBACK
I_FORM
PISTOL
EMPTY
```

Defense:

```text
4_3
3_4
NICKEL
DIME
GOAL_LINE
```

These remain the existing architecture. The expansion database adds football knowledge around them.

## 03.2 Formation families

```text
GUN / SHOTGUN
PISTOL
SINGLEBACK
I_FORM
STRONG
WEAK
HEAVY
FULL_HOUSE
WILDCAT
EMPTY
```

Common structural variants:

```text
DOUBLES
TRIPS
TRIPS_OPEN
TRIPS_TIGHT
BUNCH
STACK
TIGHT
Y_OFF
WING
WING_PAIR
DEUCE
SPLIT
SPLIT_BACK
FLEX
NIFTY / NASTY
OFFSET
HIP
CLOSE
QUADS
```

Examples:

```text
GUN_DOUBLES
GUN_TRIPS
GUN_BUNCH
GUN_TIGHT
GUN_Y_OFF
GUN_EMPTY
GUN_SPLIT
GUN_WING
GUN_STACK
PISTOL_STRONG
PISTOL_WING
PISTOL_FULL_HOUSE
SINGLEBACK_ACE
SINGLEBACK_BUNCH
SINGLEBACK_WING
SINGLEBACK_TIGHT
I_FORM_SLOT
I_FORM_WING
```

### Formation normalization

Do not create hundreds of independent formation IDs unnecessarily.

Prefer:

```text
BASE FORMATION
+
PERSONNEL
+
STRUCTURAL MODIFIERS
+
DIRECTION
```

Example:

```text
SHOTGUN
+ 11
+ TRIPS
+ Y_OFF
+ RIGHT
```

---

# 04 — ALIGNMENT DATABASE

Functional roles:

```text
X
Z
F
Y
H
R
Q
```

Alignment modifiers:

```text
SPLIT
SLOT
STACK
BUNCH
TRIPS
QUADS
TIGHT
Y_OFF
WING
DEUCE
FLEX
OFFSET
NARROW / NASTY
ON_LINE
OFF_LINE
```

The same concept can change materially when alignment changes.

---

# 05 — MOTION / SHIFT

## 05.1 Motion families

```text
JET
ORBIT
ACROSS
RETURN
TRADE
```

Motion is a modifier:

```text
FORMATION + PERSONNEL + CONCEPT + MOTION = PLAY INSTANCE
```

Motion can:

- identify possible man/zone behavior;
- change leverage;
- move an edge defender;
- alter run fits;
- create a blocking angle;
- create a constraint;
- disguise the final intent.

Motion response is information, not certainty.

```text
DEFENDER FOLLOWS → MAN LIKELY
DEFENSE PASSES OFF → ZONE / MATCH LIKELY
```

## 05.2 Shift

A shift repositions the structure before the snap.

```text
INITIAL FORMATION
→ SHIFT
→ DEFENSIVE RESPONSE
→ FINAL FORMATION
→ PLAY
```

Motion = player moves.

Shift = structure changes.

---

# 06 — RUN CONCEPT DATABASE

## 06.1 Core concepts

```text
INSIDE_ZONE
OUTSIDE_ZONE
WIDE_ZONE
STRETCH
SPLIT_ZONE
DUO
POWER
COUNTER
```

## 06.2 Gap / downhill

```text
ISO
LEAD
BLAST
TRAP
WHAM
POWER
POWER_TOSS
QB_POWER
QB_SNEAK
GOAL_LINE_ISO
GOAL_LINE_POWER
```

## 06.3 Perimeter / misdirection

```text
PIN_PULL
TOSS
TOSS_LEAD
TOSS_CRACK
SWEEP
BUCK_SWEEP
JET_SWEEP
JET_ACTION
END_AROUND
REVERSE
DOUBLE_REVERSE
COUNTER_SWEEP
COUNTER_GT
COUNTER_GH
```

## 06.4 Draw / QB run

```text
QB_DRAW
HB_DRAW
SET_DRAW
DIVE
HB_SLAM
HB_OFF_TACKLE
```

## 06.5 Option / constraint runs

```text
POWER_READ
INVERTED_VEER
READ_OPTION
QB_SWEEP
```

### Run execution model

```text
RUN_CONCEPT = {
  id,
  family,
  blocking_scheme,
  primary_gap,
  secondary_gap,
  ball_carrier,
  backfield_action,
  qb_action,
  motion_dependency,
  pullers,
  lead_blockers,
  edge_blockers,
  read_structure,
  rb_path,
  cut_rules,
  formation_compatibility,
  personnel_compatibility,
  variants
}
```

### RB cut rules

```text
BANG     = take immediate designed lane
BEND     = cut behind flow
BOUNCE   = get outside
CUTBACK  = reverse pursuit angle
```

### Run read

```text
RUN_READ = {
  defender,
  trigger,
  expected_behavior,
  response,
  priority
}
```

---

# 07 — PASS CONCEPT DATABASE

## 07.1 Quick pass

```text
SLANT
HITCH
STICK
SPACING
CHOICE
```

## 07.2 Screens

```text
BUBBLE_SCREEN
FL_SE_SCREEN
HB_SLIP_SCREEN
WR_TUNNEL_SCREEN
MESH_WHEEL
```

## 07.3 Medium

```text
LEVELS
SHALLOW_CROSS
MESH
SMASH
SALEM
DRIVE
CURL_FLAT
PIVOT
SPOT_SNAG
SAIL
Y_CROSS
DART_QUICK_DIG
DOUBLE_DIG
DEEP_CROSS
COMEBACK
```

## 07.4 Deep

```text
DAGGER
FLOOD
MILLS
DOUBLE_POST
VERTICALS
DIVIDE
FOUR_VERTICALS
SWITCH_VERTICALS
DEEP_CROSS
```

## 07.5 Play Action

```text
PA_BOOT
PA_SLIDE
PA_FLOOD
PA_BOOT_FLOOD
```

Play Action is a modifier/family, not necessarily a single immutable route tree.

---

# 08 — ROUTE PRIMITIVES

```text
GO
FADE
SEAM
DIG
POST
OUT
COMEBACK
SLANT
DRAG
SHALLOW_CROSS
HITCH
CURL
CORNER
SAIL
FLAT
ARROW
WHEEL
TEXAS / ANGLE
CHOICE
```

Important:

```text
ROUTE ≠ CONCEPT
```

Example:

```text
TEXAS = route
```

while:

```text
HB TEXAS + OUTSIDE GO + SLOT DIG
```

is a concept structure.

---

# 09 — OPTION / RPO

## 09.1 Option concepts

```text
READ_OPTION
SPEED_OPTION
MIDLINE_OPTION
TRIPLE_OPTION
INVERTED_VEER
POWER_READ
SHOVEL_OPTION
```

## 09.2 RPO concepts

```text
RPO_ALERT
RPO_PEEK
RPO_READ
RPO_INSIDE_ZONE
RPO_POWER
RPO_OUTSIDE_ZONE
```

Core model:

```text
PLAY START
→ INITIAL ACTION
→ READ DEFENDER
→ QB DECISION
→ FINAL OUTCOME
```

Do not redesign QB Reads 1-2-3.

---

# 10 — BLOCKING DATABASE

Blocking primitives:

```text
ZONE_STEP
REACH
CUT_OFF
COMBO
CLIMB
DOWN_BLOCK
PULL
KICK_OUT
WRAP
LEAD
ARC
SEAL
TRAP
CRACK
CHIP
MOTION_BLOCK
```

```text
BLOCK_ASSIGNMENT = {
  player,
  block_type,
  target,
  initial_alignment,
  direction,
  timing,
  release_condition,
  secondary_target,
  objective
}
```

Target types:

```text
DL
EDGE
LB
NICKEL
CB
SAFETY
FORCE
SPILL
SECOND_LEVEL
ZONE
```

---

# 11 — PASS PROTECTION

## 11.1 Families

```text
FIVE_MAN
SIX_MAN
SEVEN_MAN_MAX
FULL_SLIDE
HALF_SLIDE
MAN_PROTECTION
CHIP
SCAT / SCAN_RELEASE
```

### Five-man

OL handles five; RB/TE can release. More exposed to pressure.

### Six-man

RB/TE/H-back can protect the sixth threat.

### Seven-man / max

Maximum protection, fewer routes.

### Full slide

Entire OL slides in one direction.

### Half slide

One side zone/slide, other side man protection.

### Man protection

Specific defender assignments.

### Chip

Brief edge contact followed by release.

### Scat / scan-release

OL handles base rush; RB scans an additional threat before release.

Protection states:

```text
SCAN
IDENTIFY
ENGAGE
PASS_OFF
ANCHOR
SLIDE
HELP
RELEASE
RECOVER
```

---

# 12 — DEFENSIVE FRONT DATABASE

## 12.1 Techniques

```text
0  = head-up C
1  = inside G
2  = head-up G
2i = inside G
3  = outside G
4  = head-up T
4i = inside T
5  = outside T
6  = head-up / near TE
7  = inside TE
9  = wide edge
```

## 12.2 Gaps

```text
A
B
C
D / OUTSIDE_EDGE
```

## 12.3 Front families

```text
EVEN
4_3_OVER
4_3_UNDER
4_3_EVEN
4_2_5
ODD
3_4_ODD
OKIE
STACK
BEAR
TITE
MINT
HYBRID
GOAL_LINE
SHORT_YARDAGE
NASCAR / PASS_RUSH
EMPTY_SPECIFIC
```

Front movement:

```text
STEM
SHIFT
SLANT
ANGLE
SPIN
EXCHANGE
STUNT
LOOP
CRASH
```

Front ≠ coverage.

---

# 13 — RUN FITS

Roles:

```text
A_GAP
B_GAP
C_GAP
D_GAP
FORCE
SPILL
CONTAIN
ALLEY
SCRAPE
SCRAPE_EXCHANGE
PURSUE
READ
```

```text
RUN_FIT = {
  defender,
  primary_gap,
  secondary_gap,
  force_or_fit_role,
  trigger,
  leverage,
  spill_box_rule,
  pursuit_path,
  adjustment
}
```

Block recognition:

```text
DOWN
BASE
REACH
DOUBLE_TEAM
PULL
TRAP
WHAM
ARC
CRACK
PASS_SET
RELEASE
```

---

# 14 — COVERAGE DATABASE

## 14.1 Families

```text
MAN
ZONE
MATCH
HYBRID
BRACKET / DOUBLE
```

## 14.2 Coverages

```text
COVER_0
COVER_0_BLITZ
COVER_1
COVER_1_ROBBER
COVER_2
COVER_2_CORNER
COVER_2_BUZZ
TAMPA_2
COVER_2_MAN
COVER_3
COVER_3_SKY
COVER_3_BUZZ
COVER_3_MATCH
QUARTERS / COVER_4
MATCH_QUARTERS
PALMS / 2_READ
COVER_6
COVER_8
SPLIT_FIELD
BRACKET
DOUBLE
ROBBER
BANJO
PRESS_MAN
OFF_MAN
MATCH_MAN
WALL
COLLISION
```

Match mechanics:

```text
MEG
MOD
WALL
CARRY
PASS_OFF
BANJO
TRAP
SQUAT
ROB
```

```text
MATCH_RULE = {
  defender,
  read_key,
  trigger_route,
  trigger_depth,
  action,
  match_target,
  fallback_zone,
  leverage
}
```

Defender states:

```text
PRE_SNAP_ALIGN
READ
MATCH
CARRY
TRAIL
PASS_OFF
WALL
ROB
TRAP
SQUAT
DROP
FIT_RUN
PRESS
RECOVER
PURSUE
```

Route coverage states:

```text
OPEN
WINDOW
CONTESTED
TIGHT
DOUBLE_COVERED
UNCOVERED
```

Coverage is time-dependent.

---

# 15 — PRESSURE / BLITZ DATABASE

Pressure families:

```text
FOUR_MAN_RUSH
BLITZ
ZONE_BLITZ
SIMULATED_PRESSURE
CREEPER
MUG_PRESSURE
GREEN_DOG
OVERLOAD
CROSS_BLITZ
EDGE_PRESSURE
INTERIOR_PRESSURE
```

Concepts:

```text
FOUR_MAN_RUSH
FOUR_MAN_STUNT
ET_STUNT
TEX_STUNT
INTERIOR_STUNT
LONG_STUNT
FIVE_MAN_PRESSURE
SIX_MAN_PRESSURE
SEVEN_MAN_PRESSURE
COVER_0_PRESSURE
COVER_1_PRESSURE
FIRE_ZONE
FIRE_3
COVER_2_FIRE
SIMULATED_PRESSURE
CREEPER
MUG_DROP
DOUBLE_A_GAP_MUG
MUG_BLITZ
GREEN_DOG
TE_GREEN_DOG
RB_GREEN_DOG
OVERLOAD_BLITZ
FIELD_OVERLOAD
BOUNDARY_PRESSURE
INTERIOR_BLITZ
A_GAP_BLITZ
B_GAP_BLITZ
EDGE_BLITZ
CORNER_BLITZ
SAFETY_BLITZ
NICKEL_BLITZ
CROSS_BLITZ
CROSS_DOG
EXCHANGE_PRESSURE
SPILL_PROTECTION
CONTAIN_RUSH
INTERIOR_COLLAPSE
EDGE_RUSH
```

Key distinctions:

```text
MUG = presentation
BLITZ = actual pressure
SIMULATED_PRESSURE = pressure presentation with only four actual rushers, often dropping a traditional rusher
CREEPER = replacement pressure concept
FIRE_ZONE = usually five rushers with zone coverage behind
GREEN_DOG = coverage defender rushes when assigned RB/TE stays in protection
```

Always separate:

```text
PRESENTED_PRESSURE
ACTUAL_PRESSURE
```

---

# 16 — PRESSURE EXECUTION

```text
PRESSURE_PACKAGE = {
  id,
  family,
  front,
  presentation,
  actual_rushers,
  coverage,
  drop_replacements,
  rush_lanes,
  stunts,
  blitzers,
  green_dog_rules,
  pressure_timing,
  protection_conflicts,
  disguise_level,
  complexity,
  formation_adjustments
}
```

```text
RUSH_ASSIGNMENT = {
  player,
  initial_alignment,
  rush_type,
  rush_lane,
  target,
  contain,
  stunt_partner,
  trigger,
  timing,
  counter
}
```

```text
DROP_REPLACEMENT = {
  rusher_leaving_zone,
  dropper,
  replacement_zone,
  trigger,
  timing
}
```

Rusher states:

```text
ALIGN
SHOW
TRIGGER
RUSH
STUNT
REDIRECT
CONTAIN
COLLAPSE
PRESSURE
SACK
PURSUIT
```

Pressure outcomes:

```text
CLEAN
PRESSURE
HURRY
HIT
SCRAMBLE
SACK
THROWAWAY
BAT
INTERCEPTION
```

Pressure ≠ sack.

---

# 17 — POCKET MODEL

```text
POCKET = {
  depth,
  width,
  left_edge,
  right_edge,
  interior_integrity,
  collapse_direction,
  escape_lane
}
```

States:

```text
CLEAN
NARROW
COLLAPSED_LEFT
COLLAPSED_RIGHT
COLLAPSED_INTERIOR
FULL_COLLAPSE
```

Protection result depends on:

```text
RUSHER ABILITY
BLOCKER ABILITY
RUSH MOVE
PROTECTION
ALIGNMENT
STUNT
COMMUNICATION
TIMING
FATIGUE
```

---

# 18 — SITUATIONAL FOOTBALL

Game context:

```text
GAME_CONTEXT = {
  quarter,
  clock,
  down,
  distance,
  field_position,
  score_diff,
  timeouts_offense,
  timeouts_defense,
  drive_state,
  tempo,
  personnel,
  substitutions_available,
  previous_play,
  recent_sequence
}
```

Distance tags:

```text
SHORT = 1-3
MEDIUM = 4-6
LONG = 7-10
VERY_LONG = 11+
```

Field tags:

```text
BACKED_UP
OWN_RED_ZONE
MIDFIELD
PLUS_TERRITORY
RED_ZONE
GOAL_TO_GO
GOAL_LINE
```

Score tags:

```text
WINNING_BIG
WINNING
TIED
TRAILING
TRAILING_BIG
```

Clock tags:

```text
NORMAL
LATE_QUARTER
TWO_MINUTE
UNDER_ONE_MINUTE
FINAL_DRIVE
FOUR_MINUTE
```

Special situations:

```text
THIRD_DOWN
FOURTH_DOWN
SHORT_YARDAGE
RED_ZONE
TWO_POINT
END_OF_HALF
END_OF_GAME
VICTORY_FORMATION
FIELD_GOAL
```

---

# 19 — SITUATIONAL PRINCIPLES

Situation filters relevance; it does not dictate a play.

Correct:

```text
GAME STATE
→ SITUATIONAL FILTER
→ VALID PLAY SET
→ DEFENSIVE LOOK
→ AI DECISION
→ PLAY INSTANCE
```

Incorrect:

```text
3RD & 10 → ALWAYS DAGGER
```

Third down:

```text
3RD & SHORT → QB SNEAK / POWER / DUO / IZ / RPO / QUICK PASS
3RD & MEDIUM → STICK / MESH / LEVELS / SLANT / DIG / FLOOD
3RD & LONG → DAGGER / FLOOD / MESH / VERTICALS / SCREEN / DRAW
```

Four-minute offense emphasizes:

```text
RUN
FIRST DOWN
CLOCK
TURNOVER AVOIDANCE
```

Two-minute offense emphasizes:

```text
CLOCK
SIDELINE
FIRST DOWN
TIMEOUTS
EXPLOSIVE POTENTIAL
```

Red zone emphasizes:

```text
CONDENSED SPACE
LEVERAGE
BUNCH / STACK
SLANT
CORNER
SMASH
MESH / RUB
RUN
QB RUN
PLAY ACTION
```

---

# 20 — RISK / VALUE PROFILE

```text
RISK_PROFILE = {
  turnover_risk,
  sack_risk,
  explosive_gain_potential,
  clock_cost,
  variance
}
```

```text
VALUE_PROFILE = {
  expected_yards,
  first_down_probability,
  explosive_probability,
  turnover_probability,
  sack_probability,
  clock_effect
}
```

These are descriptive/derived properties, not hard-coded guarantees.

---

# 21 — SPECIAL TEAMS

Families:

```text
KICKOFF
KICK_RETURN
PUNT
PUNT_RETURN
FIELD_GOAL
PAT
TWO_POINT
ONSIDE_KICK
FAKE_KICK
BLOCKED_KICK
```

Roles:

```text
KICKER
PUNTER
LONG_SNAPPER
HOLDER
RETURNER
GUNNER
JAMMER
KICK_COVERAGE
KICK_RETURN_BLOCKER
PUNT_COVERAGE
PUNT_RETURN_BLOCKER
PROTECTOR
PERSONAL_PROTECTOR
EDGE_BLOCKER
INTERIOR_BLOCKER
```

Kick types:

```text
DEEP
DIRECTIONAL
POOCH
SQUIB
SHORT
ONSIDE
HIGH_HANG
DRIVE
```

Punt types / targets:

```text
COFFIN_CORNER
LEFT_SIDELINE
RIGHT_SIDELINE
CENTER
OPEN_FIELD
```

Field goal outcomes:

```text
MADE
MISSED_LEFT
MISSED_RIGHT
MISSED_SHORT
BLOCKED
ABORTED
```

Special teams mistakes:

```text
BAD_SNAP
MUFF
FUMBLE
MISSED_BLOCK
MISSED_TACKLE
PENALTY
BAD_HOLD
BAD_KICK
BLOCKED_KICK
MISCOMMUNICATION
```

Special teams should be simulated as sequences:

```text
SNAP
→ PROTECTION
→ KICK
→ COVERAGE
→ RETURN / CATCH
→ BLOCKING
→ TACKLE / RECOVERY
→ FIELD POSITION
```

---

# 22 — PLAYER ARCHETYPES

Archetypes describe **behavior**, not ratings.

## QB

```text
POCKET_PASSER
MOBILE_QB
DUAL_THREAT
SCRAMBLER
FIELD_GENERAL
AGGRESSIVE_THROWER
QUICK_GAME_QB
```

## RB

```text
ONE_CUT
ELUSIVE
POWER_BACK
SPEED_BACK
PASS_CATCHING_BACK
THIRD_DOWN_BACK
ALL_PURPOSE
```

## WR

```text
X_RECEIVER
Z_RECEIVER
SLOT_RECEIVER
DEEP_THREAT
POSSESSION
SEPARATOR
YAC
CONTESTED_CATCH
ROUTE_TECHNICIAN
```

## TE

```text
INLINE_TE
RECEIVING_TE
BLOCKING_TE
MOVE_TE
Y_OFF_TE
SPLIT_TE
```

## OL

```text
POWER_BLOCKER
ZONE_BLOCKER
PULLING_GUARD
ATHLETIC_LINEMAN
ANCHOR_PASS_BLOCKER
AGILE_CENTER
```

## DL / EDGE

```text
RUN_STUFFER
PASS_RUSH_DT
NOSE_TACKLE
POWER_EDGE
SPEED_EDGE
HYBRID_EDGE
```

## LB

```text
MIKE
WILL
SAM
COVERAGE_LB
BLITZ_LB
HYBRID_LB
```

## DB

```text
PRESS_MAN
OFF_MAN
ZONE_CORNER
MATCH_CORNER
BALL_HAWK
PHYSICAL_CORNER
SLOT_CORNER
FREE_SAFETY
STRONG_SAFETY
BOX_SAFETY
CENTER_FIELDER
MATCH_SAFETY
HYBRID_SAFETY
```

## Special Teams

```text
RETURN_SPECIALIST
GUNNER
COVERAGE_SPECIALIST
POWER_PUNTER
DIRECTIONAL_PUNTER
PIN_PUNTER
HANGTIME_PUNTER
POWER_KICKER
ACCURACY_KICKER
LONG_RANGE_KICKER
```

---

# 23 — PLAYER BEHAVIOR MODELS

Archetype does not replace assignment.

Correct:

```text
ASSIGNMENT = GO ROUTE
ARCHETYPE = DEEP THREAT
EXECUTION = HOW THE GO IS RUN
```

Incorrect:

```text
DEEP THREAT → AUTOMATIC GO ROUTE
```

## Route execution

```text
ROUTE_EXECUTION = {
  release,
  stem,
  depth,
  break,
  separation,
  catch_point,
  adjustment,
  yac_action
}
```

## Run execution

```text
RUN_EXECUTION = {
  aiming_point,
  read,
  cut,
  acceleration,
  contact,
  ball_security,
  secondary_action
}
```

## Blocking execution

```text
BLOCK_EXECUTION = {
  target,
  technique,
  leverage,
  engagement,
  sustain,
  shed_response,
  release
}
```

## Coverage execution

```text
COVERAGE_EXECUTION = {
  alignment,
  leverage,
  pedal,
  trigger,
  match,
  carry,
  break,
  contest,
  recovery
}
```

## Pass rush execution

```text
PASS_RUSH_EXECUTION = {
  alignment,
  getoff,
  first_move,
  rush_lane,
  counter,
  contain,
  pressure,
  finish
}
```

---

# 24 — PLAYER MATCHUPS

```text
MATCHUP = {
  offensive_player,
  defensive_player,
  assignment,
  technique,
  leverage,
  advantage,
  disadvantage,
  execution
}
```

States:

```text
ADVANTAGE
EVEN
DISADVANTAGE
```

Advantage does not guarantee success.

---

# 25 — CONCEPT RELATIONSHIPS

Relationship types:

```text
BASE
COMPLEMENT
COUNTER
CONSTRAINT
ANSWER
SETUP
PAYOFF
SEQUENCE
MIRROR
CHANGEUP
TENDENCY_BREAKER
```

Examples:

```text
INSIDE_ZONE ↔ BOOT
POWER ↔ COUNTER
POWER ↔ POWER_READ
POWER ↔ POWER_RPO
ZONE ↔ PLAY_ACTION
JET ↔ INSIDE_ZONE
JET ↔ SWEEP
JET ↔ BOOT
```

Core relationship:

```text
BASE PLAY
→ DEFENSIVE RESPONSE
→ COUNTER / CONSTRAINT
→ DEFENSIVE ADJUSTMENT
→ NEXT RESPONSE
```

A relationship means:

```text
A MAY CREATE RESPONSE X
B IS ONE POSSIBLE ANSWER
```

not:

```text
A ALWAYS → B
```

---

# 26 — PLAY SEQUENCING

Possible sequence lengths:

```text
TWO_PLAY
THREE_PLAY
MULTI_PLAY
```

Examples:

```text
RUN → PLAY ACTION
RUN → RPO → COUNTER
JET → INSIDE_ZONE → BOOT
POWER → COUNTER → POWER
```

Recent memory can use:

```text
LAST_5_PLAYS
LAST_10_PLAYS
CURRENT_DRIVE
CURRENT_GAME
```

But limited memory must not make the AI omniscient.

Tendency confidence:

```text
LOW
MEDIUM
HIGH
```

Five snaps are not enough to make a definitive long-term tendency.

---

# 27 — TENDENCIES AND TELLS

Potential information:

```text
FORMATION
PERSONNEL
ALIGNMENT
MOTION_RESPONSE
SAFETY_DEPTH
FRONT
PRESSURE_PRESENTATION
RECENT_PLAY_SEQUENCE
```

Separate:

```text
BASE_TENDENCY
RECENT_TENDENCY
```

and:

```text
PRESENTED_SHELL
ACTUAL_COVERAGE
```

A defense may show 2-high and rotate to 1-high after the snap.

An offense may show a run look and pass.

A tendency is information, not certainty.

---

# 28 — COMPATIBILITY MATRIX

Every combination should be classified:

```text
PRIMARY
SUPPORTED
POSSIBLE
UNNATURAL
INVALID
```

Compatibility is a football-integrity filter, not a frequency model.

## 28.1 Typical personnel compatibility

```text
10:
  GUN / EMPTY / SPREAD / QUICK PASS / SCREEN / RPO

11:
  GUN / SINGLEBACK / PISTOL / BUNCH / TRIPS / TIGHT
  Broadest compatibility

12:
  SINGLEBACK / PISTOL / GUN Y_OFF / TIGHT / WING / HEAVY
  Run + PA + TE concepts

21:
  I_FORM / PISTOL / SINGLEBACK / SPLIT / STRONG / WEAK
  Power / Iso / Lead / Counter / PA

22:
  I_FORM / HEAVY / FULL_HOUSE / GOAL_LINE
  Power / Iso / Lead / Duo / Counter / PA
```

## 28.2 Typical concept compatibility

```text
ZONE:
  GUN / PISTOL / SINGLEBACK

GAP:
  I_FORM / SINGLEBACK / GUN / PISTOL / HEAVY

PERIMETER:
  GUN / PISTOL / SINGLEBACK / WING

OPTION:
  GUN / PISTOL / WILDCAT

RPO:
  GUN / PISTOL

QUICK_PASS:
  GUN / EMPTY / SINGLEBACK

MEDIUM_PASS:
  GUN / SINGLEBACK / PISTOL

DEEP_PASS:
  GUN / EMPTY / SINGLEBACK

PLAY_ACTION:
  PISTOL / SINGLEBACK / GUN Y_OFF / I_FORM / HEAVY
```

## 28.3 Situation compatibility

```text
SHORT_YARDAGE:
  HEAVY / I_FORM / TIGHT / PISTOL

LONG_YARDAGE:
  GUN / EMPTY / TRIPS / BUNCH

RED_ZONE:
  BUNCH / STACK / TIGHT / HEAVY / EMPTY

THIRD_AND_LONG:
  DIME / NICKEL / QUARTERS / COVER_3 / COVER_6 / SIM_PRESSURE

THIRD_AND_SHORT:
  HEAVY / BEAR / TITE / RUN_BLITZ / COVER_0
```

These are compatibility tendencies, not hard-coded play calls.

---

# 29 — COMPATIBILITY DATA MODEL

```text
COMPATIBILITY = {
  personnel,
  formation,
  concept,
  variant,
  protection,
  motion,
  situation,
  defensive_compatibility,
  level,
  reason
}
```

An INVALID result must have a structural reason.

Examples:

```text
INVALID:
required player role is absent

INVALID:
variant requires a QB run threat that the structure does not provide

INVALID:
required route/block assignment cannot be represented by the formation
```

A combination can be:

```text
FORMATION = PRIMARY
CONCEPT = PRIMARY
VARIANT = SUPPORTED
PROTECTION = SUPPORTED
OVERALL = SUPPORTED
```

The overall level is not an average. A single structural INVALID can invalidate the entire play.

---

# 30 — COMPLETE PLAY INSTANCE SCHEMA

```text
PLAY_INSTANCE = {
  game_context,
  personnel,
  formation,
  alignment,
  motion,
  concept,
  variant,
  player_assignments,
  routes,
  blocking,
  protection,
  defensive_front,
  coverage,
  pressure,
  matchups,
  player_profiles,
  compatibility,
  execution,
  outcome
}
```

---

# 31 — PLAY CALL VS EXECUTION

```text
PLAY_CALL = {
  game_context,
  situational_context,
  personnel,
  formation,
  motion,
  concept,
  variant,
  protection,
  expected_defensive_response
}
```

```text
PLAY_EXECUTION = {
  assignments,
  player_behavior,
  defensive_response,
  matchup_results,
  execution_variance,
  outcome
}
```

A good call can fail.

A mediocre call can succeed.

---

# 32 — EXECUTION VARIANCE

Players should not execute identically every snap.

Conceptually:

```text
EXPECTED_BEHAVIOR
+
PLAYER_ABILITY
+
ARCHETYPE
+
MATCHUP
+
CONTEXT
+
CONTROLLED_VARIANCE
→ EXECUTION
```

Variance must remain controlled enough to preserve football plausibility.

---

# 33 — DEFENSIVE INTERACTION MODEL

A pass concept can encounter:

```text
FRONT
+
COVERAGE
+
PRESSURE
+
MATCHUP
```

A run concept can encounter:

```text
FRONT
+
TECHNIQUES
+
RUN FITS
+
BLOCK DESTRUCTION
+
PURSUIT
```

A special teams play can encounter:

```text
PROTECTION
+
RUSH
+
COVERAGE
+
RETURN
+
BLOCKING
```

---

# 34 — INTEGRATED EXAMPLE

```text
GAME:
3RD & 8
MIDFIELD
TIED
NORMAL CLOCK

PERSONNEL:
11

FORMATION:
GUN TRIPS Y_OFF RIGHT

MOTION:
JET

CONCEPT:
RPO / INSIDE ZONE VARIANT

PROTECTION:
HALF_SLIDE

DEFENSE:
NICKEL
+
2-HIGH PRESENTATION
+
SIMULATED PRESSURE

PLAYER ASSIGNMENTS:
QB → READ
RB → INSIDE ZONE
Y → BLOCK / RELEASE
X → VERTICAL
Z → OUTSIDE ROUTE
F → QUICK / ACCESS ROUTE

DEFENSIVE RESPONSE:
EDGE EXPANDS
+
LB HOLDS
+
ONE DL DROPS

QB DECISION:
KEEP RUN / THROW ACCORDING TO READ STRUCTURE

EXECUTION:
MATCHUP + BLOCKING + PRESSURE + PLAYER PROFILE

OUTCOME:
GAIN / STOP / TURNOVER / ETC.
```

The important point is that the concept, assignments, defense and outcome remain separate layers.

---

# 35 — DATABASE INTEGRITY RULES

Before a play becomes a valid Play Instance:

```text
1. PERSONNEL VALID?
2. FORMATION VALID?
3. ALIGNMENTS VALID?
4. MOTION VALID?
5. CONCEPT VALID?
6. VARIANT VALID?
7. PLAYER ASSIGNMENTS VALID?
8. PROTECTION VALID?
9. SITUATION VALID?
10. DEFENSIVE INTERACTION VALID?
```

Only then:

```text
→ EXECUTION
→ OUTCOME
```

---

# 36 — NORMALIZATION RULES

Avoid duplicates caused by naming.

Examples:

```text
OUTSIDE_ZONE
≈ WIDE_ZONE
≈ STRETCH
```

depending on assignment terminology.

```text
POWER
→ POWER
→ POWER_TOSS
→ QB_POWER
```

Keep related variants separate when their execution changes.

Do not merge genuinely different blocking or read structures merely because they share a family name.

---

# 37 — FOOTBALL SEMANTIC RULES

### Formation

Defines where players line up.

### Concept

Defines the coordinated offensive/defensive idea.

### Route

Defines an individual receiver path.

### Assignment

Defines what one player is responsible for.

### Variant

Defines a meaningful structural modification.

### Personnel

Defines who is on the field.

### Situation

Defines why the context matters.

### Coverage

Defines defensive pass responsibilities.

### Front

Defines defensive box structure / alignments.

### Pressure

Defines rush behavior.

### Execution

Defines what actually happens.

### Outcome

Defines the final result.

---

# 38 — WHAT THIS DATABASE MUST NOT DO

Do not use it to:

```text
AUTO-ASSIGN CONCEPTS TO FRANCHISES
REPLACE EXISTING PLAYBOOK V0.1
REPLACE CURRENT FORMATIONS
REWRITE QB READS 1-2-3
CREATE ARBITRARY PLAY PROBABILITIES
GUARANTEE OUTCOMES
TURN TENDENCIES INTO CERTAINTIES
CREATE ONE-TO-ONE FORMATION → PLAY RULES
```

---

# 39 — CLAUDE INTEGRATION DIRECTIVE

When using this database to extend GridironSim:

1. Preserve all existing V0.1 structures unless explicitly instructed otherwise.
2. Treat this document as a supplementary knowledge layer.
3. Normalize new data before adding it.
4. Validate football compatibility before generating a play instance.
5. Keep formation, concept, assignment, execution and outcome separate.
6. Use player archetypes to influence execution, not to replace ratings.
7. Use situational data to filter and contextualize, not to hard-code calls.
8. Use concept relationships to model sequencing and counters, not deterministic play chains.
9. Keep defensive front, coverage and pressure as separate dimensions.
10. Keep presented pressure/shell separate from actual pressure/coverage.
11. Do not assume a concept succeeds because it is a good matchup.
12. Do not assume a concept fails because the matchup is theoretically unfavorable.
13. Preserve controlled execution variance.
14. Keep reserve concepts available for future franchises.
15. Do not retrofit every item in this database into current teams automatically.

---

# 40 — FINAL ARCHITECTURE

The complete supplementary football knowledge hierarchy is:

```text
PERSONNEL
    ↓
FORMATION
    ↓
ALIGNMENT
    ↓
MOTION / SHIFT
    ↓
CONCEPT
    ↓
VARIANT
    ↓
PLAYER ASSIGNMENTS
    ↓
PLAYER ARCHETYPE / ROLE BEHAVIOR
    ↓
ROUTES / BLOCKING / PROTECTION
    ↓
DEFENSIVE FRONT
    ↓
RUN FIT
    ↓
COVERAGE
    ↓
PRESSURE
    ↓
MATCHUP
    ↓
SITUATIONAL CONTEXT
    ↓
COMPATIBILITY FILTER
    ↓
SEQUENCING / CONCEPT RELATIONSHIP
    ↓
PLAY INSTANCE
    ↓
EXECUTION
    ↓
OUTCOME
```

---

# 41 — FINAL STATUS

This database is intended to function as the football-knowledge reference layer for future GridironSim expansion.

It covers:

- Personnel
- Formations
- Alignments
- Motion
- Run concepts
- Pass concepts
- Routes
- Screens
- Play Action
- Option
- RPO
- Blocking
- Pass protection
- Defensive fronts
- Techniques
- Gaps
- Run fits
- Coverages
- Match rules
- Pressure
- Blitz
- Simulated pressure
- Creepers
- Mug fronts
- Green Dog
- Special Teams
- Situational Football
- Player Archetypes
- Player Role Behavior
- Matchups
- Concept Relationships
- Play Sequencing
- Tendencies
- Compatibility
- Play validation

The final principle is:

```text
DO NOT SIMULATE A PLAY NAME.

SIMULATE:
WHO IS ON THE FIELD
+
WHERE THEY ALIGN
+
WHAT THEY ARE ASKED TO DO
+
HOW THE OPPOSITION RESPONDS
+
HOW EACH PLAYER EXECUTES
+
WHAT THE INTERACTION PRODUCES
```

This document is a **football knowledge and expansion layer**, not a replacement for the existing GridironSim engine.
