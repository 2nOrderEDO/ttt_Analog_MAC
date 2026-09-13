# EMMAC_Block_v3 CLM (gain compression) diagnostic

Method: dc op probe sweep over k=1..8, Iin=-8..7uA at Vout=0.6V
(`probe_sweep.py` -> `probe_v3*.csv`), plus cascode / scaling netlist variants
(`make_variant.py`, `EMMAC_Accuracy_v3_*.spice`).

## 1. Mirror stage ratios (ideal = 1.00)

| ratio | k=1,+1 | k=1,+7 | k=8,+7 | k=8,-8 |
|---|---|---|---|---|
| M24/M23 | 1.140 | 1.036 | 0.974 | 0.953 |
| M29/M28 | 1.186 | 1.091 | 1.003 | 0.997 |
| M20/M28 | 1.145 | 1.078 | 1.018 | - |
| M13/M12 | 1.153 (k1,-1) | - | - | 0.967 |
| M27/(k*M26) | 1.012 | 1.002 | 0.908 | 0.904 |

CLM check: `1 + gds_out*(Vds_out-Vds_ref)/I_out` predicts the measured ratio:
e.g. M29/M28 1.065 pred vs 1.091 meas; M24/M23 0.970 vs 0.974;
M20/M28 1.015 vs 1.018 (k=8,+7) and 1.088 vs ~1.15 (k=1).
=> the errors are channel-length modulation of the non-cascoded mirrors.

## 2. Cascode experiments

| variant | target | result |
|---|---|---|
| C1 | M28/M29/M20 | ratios ->1.00 at low current, but the cascode shifts `net12`, M31's Vds collapses to 72mV and the chain current halves at k=8. Not drop-in. |
| C2 | M23/M24 | works: ratio 1.036->1.000, 1.140->1.04, chain undisturbed. ~0.96 left at k=8. |
| C3 | M12/M13 | lowers M29's Vds (0.995->0.42V) and degrades M29/M28 to 0.48. Not drop-in. |
| C4 | M26/M27 | small gain (mult 0.908->0.916); fixed bias does not equalize Vds. |

Root cause of C1/C3 failure: `net12` is part of the multiplier bias loop
(M30/M31 split), so changing M28's I-V or drain network moves the operating
point.

## 3. W/L matched scaling (constant W/L preserves Vgs and chain bias)

G2: M20,M23,M24,M28,M29 -> 4u/1.12u; M12,M13,M26,M27 -> 2u/2u.
G4: NMOS group -> 4u/4u.

| ratio | base | G2 | G4 |
|---|---|---|---|
| M24/M23 (k1,+1) | 1.140 | 1.045 | 1.046 |
| M24/M23 (k8,+7) | 0.974 | 0.994 | 0.996 |
| M29/M28 (k1,+1) | 1.186 | 1.055 | 1.056 |
| M20/M28 (k1,+1) | 1.145 | 1.045 | 1.045 |
| M27/(k*M26) (k8,+7) | 0.908 | 0.921 | 0.932 |

Nominal accuracy (Vout sweep, half-LSB): base v3 2/128 never-meet,
worst 3.72 LSB; G2 1/128, worst 3.51 LSB, small-signal error 1.84 -> 1.18 LSB.

Limitation: in this PDK `gds` is only weakly reduced by L
(M26 gds 1.55 -> 1.35 -> 1.14 uS for L 1u -> 2u -> 4u), so scaling gives
diminishing returns.

## 4. Conclusions

1. The user hypothesis is confirmed: the residual S-shaped error is CLM of the
   non-cascoded mirrors (M23/M24, M28/M29/M20, M12/M13, M26/M27).
2. C2 (M23/M24 cascode) is safe and should be adopted.
3. Cascoding the M28/M29 reference pair directly shifts the multiplier's
   operating point (net12/M31) - it needs a coordinated redesign
   (wide-swing/regulated cascode + re-bias of M30/M31).
4. The dominant remaining term at high k is the M26/M27 unit mirror CLM
   (~7-9 %), which needs a regulated cascode (Vds-matching feedback) rather
   than L scaling.
