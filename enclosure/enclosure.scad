// =====================================================================
// SLIC2PORT-FXS enclosure - 2-piece 3D-printable case (base + lid + button plungers)
// Board: SLIC2PORT-FXS v3.4 / v3.4.1, 120 x 90 mm, M3 mounting holes at 4 mm inset.
// (v3.4.1 verified 2026-10-31: all positions identical to v3.4 except SW2,
//  moved +1.8 mm in X for Issue #9 pad clearance - reflected in sw_pos below.)
//
// Coordinate system = KiCad board coordinates:
//   X: 0..120 east,  Y: 0..90 SOUTH (same direction as KiCad file Y),
//   Z: 0 at case bottom outer face, up.
// Board outline occupies x 0..120, y 0..90 in this frame.
// All dimensions in mm. Render with -D part="base" | "lid" | "plungers" | "assembly".
// =====================================================================

part = "assembly";          // [base, lid, plungers, assembly]

// ---- Board / stack parameters (measured from SLIC2PORT-FXS-v3.4.kicad_pcb) ----
pcb_w = 120;  pcb_d = 90;  pcb_t = 1.6;
hole_pos = [[4,4],[116,4],[4,86],[116,86]];   // H1..H4, drill 3.2 (M3)

// ---- Case parameters ----
wall      = 2.0;            // side wall thickness
floor_t   = 2.0;            // base floor thickness
lid_t     = 2.4;            // lid plate thickness
gap_side  = 2.0;            // board edge -> cavity wall clearance
gap_b     = 3.5;            // PCB underside clearance (C10 0805 + TH pin protrusion)
inner_h   = 18.0;           // PCB top -> lid underside (tallest part: KS0835F module ~15.5)
corner_r  = 5.0;            // outer corner radius

boss_hole_d = 2.9;          // M3 self-tap pilot (use 4.3 for M3 heat-set inserts)
screw_len_note = 26;        // M3x26 pan head (25 also OK)

pcb_bot = floor_t + gap_b;          // 5.5
pcb_top = pcb_bot + pcb_t;          // 7.1
lid_bot = pcb_top + inner_h;        // 25.1
lid_top = lid_bot + lid_t;          // 27.5

cav_w = pcb_w + 2*gap_side;         // 124
cav_d = pcb_d + 2*gap_side;         // 94
out_w = cav_w + 2*wall;             // 128
out_d = cav_d + 2*wall;             // 98
cx = pcb_w/2;  cy = pcb_d/2;        // board centre (60,45)

// ---- Connector / control positions (KiCad coords, from the PCB file) ----
// =====================================================================
// BOARD INTERFACE - every board-dependent value lives in this section.
// The case structure (walls, bosses, screw scheme) and print design do
// NOT depend on the PCB revision. For a new board revision (v4.0):
// re-extract the values below from the new .kicad_pcb, regenerate the
// STLs, and re-check inner_h against the new tallest part.
// v4.0 status: outline 120x90 and H1..H4 are expected to be kept, but
// connector edge positions and the height map may change - the values
// below are still v3.4/v3.4.1 and MUST be refreshed before printing
// a fit-critical case for v4.0.
// =====================================================================
rj11_x   = [18, 102];               // J_3 port A / J_4 port B, body centre X (front face y=0.45)
usb_x    = 16;                      // J1 USB-C centre X, shell front y=88.6, shell centre z = pcb_top+1.6
tb_cx    = 32.5;                    // J2 terminal block centre X (pins at x=30,35, y=85)
sw_pos   = [[70.78, 76.78],         // SW1 (EN)  actuator centre = pad centroid
            [81.08, 76.78]];        // SW2 (IO0) - v3.4.1 position (v3.4 was 79.28)
led_pos  = [[45.51,8.18],[54.10,8.18],[50.70,11.97],     // D4 HOOK_A, D5 RING_A, D6 LINK_A
            [71.50,8.18],[80.11,8.18],[76.70,11.97],     // D7 HOOK_B, D8 RING_B, D9 LINK_B
            [67.70,83.47],[78.20,83.47]];                // D2 PWR, D3 STAT
button_h = 5.0;                     // SW_PUSH_6mm total height above PCB (verify variant!)
plunger_gap = 1.2;                  // plunger tip -> button top clearance at rest

// Component zones / height map (drives lid vents + assembly mock; fit-relevant
// via inner_h check against tallest_part_h)
mod_zones   = [[24.5, 30.8], [45.3, 43.8]];   // KS0835F plates [x0, y0] (MOD_A / MOD_B)
mod_size    = [50.2, 6.3, 13.0];              // plate L x T x H, stands 2.4 above PCB
relay_zones = [[30.4, 52.9], [98.4, 30.4]];   // G5V-2 bodies [x0, y0] (K1 / K2)
relay_size  = [20.5, 10.1, 11.5];
cap_pos     = [[22.52, 65.28], [54.12, 56.98], [4.53, 61.77]];  // D8 electrolytics C13/C22/C1
cap_d = 8;  cap_h = 12;
stamp_xy = [41, 65];  stamp_size = [18, 24];  stamp_socket_h = 4.3;  stamp_t = 3;
tallest_part_h = 15.5;              // KS0835F top above PCB; inner_h (18.0) must exceed this
// Lid ventilation grille: decorative staggered slot pattern that also covers
// the hot parts (SLIC modules underneath rows 29-44, relays at row edges).
// [ row Y, [slot centre Xs], slot length ] - re-check coverage per board rev.
vent_grille = [ [29,   [33, 51, 69, 87, 105], 14],
                [36.5, [24, 42, 60, 78, 96],  14],
                [44,   [33, 51, 69, 87, 105], 14],
                [51.5, [69, 87, 105],         14],
                [51.5, [36, 48],              12] ];

$fn = 48;

// ---------- helpers ----------
module rrect(w, d, r) {             // rounded rect centred at origin (2D)
  hull() for (sx=[-1,1], sy=[-1,1])
    translate([sx*(w/2-r), sy*(d/2-r)]) circle(r=r);
}
module slot2d(len, w) {             // horizontal rounded slot centred at origin (2D)
  hull() { translate([-len/2+w/2,0]) circle(d=w); translate([len/2-w/2,0]) circle(d=w); }
}
font_latin = "Liberation Sans:style=Bold";
font_cjk   = "Noto Sans CJK JP:style=Bold";   // HV-warning kanji; needs fonts-noto-cjk on the rendering machine
bolt_pts   = [[3.4,11],[6,11],[4.3,6.6],[6.2,6.6],[2,0],[3,5],[0.8,5]];   // lightning bolt silhouette (6.2 x 11)

// Logo B (HANDSET RING) polygons, generated from design/logo/logo-b.svg
// local frame: origin = mark centre, +y = mark up, overall width 16 mm
logo_b_polys = [
[[3.47,3.09],[3.40,3.00],[3.37,2.90],[3.36,2.78],[3.38,2.67],[3.43,2.57],[3.50,2.49],[3.59,2.42],[3.70,2.39],[3.81,2.38],[3.92,2.40],[3.97,2.42],[4.03,2.43],[4.09,2.45],[4.15,2.46],[4.20,2.48],[4.26,2.49],[4.32,2.50],[4.38,2.51],[4.44,2.51],[4.50,2.52],[4.56,2.53],[4.62,2.53],[4.68,2.53],[4.74,2.54],[4.79,2.54],[4.85,2.53],[4.91,2.53],[4.97,2.53],[5.03,2.52],[5.09,2.52],[5.15,2.51],[5.21,2.50],[5.27,2.49],[5.33,2.48],[5.38,2.47],[5.44,2.46],[5.50,2.44],[5.56,2.43],[5.61,2.41],[5.67,2.39],[5.73,2.37],[5.78,2.35],[5.84,2.33],[5.89,2.31],[5.95,2.28],[6.00,2.26],[6.05,2.23],[6.10,2.20],[6.16,2.17],[6.21,2.14],[6.26,2.11],[6.31,2.08],[6.36,2.05],[6.41,2.01],[6.45,1.98],[6.50,1.94],[6.55,1.90],[6.59,1.87],[6.64,1.83],[6.68,1.79],[6.73,1.75],[6.77,1.70],[6.81,1.66],[6.85,1.62],[6.89,1.57],[6.93,1.53],[6.96,1.48],[7.00,1.44],[7.04,1.39],[7.07,1.34],[7.10,1.29],[7.14,1.24],[7.17,1.19],[7.20,1.14],[7.27,1.05],[7.36,0.98],[7.46,0.94],[7.57,0.92],[7.68,0.94],[7.79,0.98],[7.87,1.05],[7.94,1.14],[7.99,1.24],[8.00,1.35],[7.99,1.47],[7.94,1.57],[7.90,1.64],[7.86,1.70],[7.82,1.77],[7.78,1.83],[7.73,1.89],[7.68,1.96],[7.64,2.02],[7.59,2.08],[7.54,2.14],[7.49,2.20],[7.43,2.25],[7.38,2.31],[7.32,2.36],[7.27,2.42],[7.21,2.47],[7.15,2.52],[7.09,2.57],[7.03,2.62],[6.97,2.67],[6.91,2.71],[6.84,2.76],[6.78,2.80],[6.71,2.84],[6.65,2.88],[6.58,2.92],[6.51,2.96],[6.44,2.99],[6.37,3.03],[6.30,3.06],[6.23,3.09],[6.16,3.12],[6.09,3.15],[6.02,3.18],[5.94,3.20],[5.87,3.23],[5.79,3.25],[5.72,3.27],[5.64,3.29],[5.57,3.31],[5.49,3.32],[5.42,3.34],[5.34,3.35],[5.26,3.36],[5.19,3.37],[5.11,3.38],[5.03,3.39],[4.95,3.39],[4.88,3.39],[4.80,3.39],[4.72,3.39],[4.64,3.39],[4.57,3.39],[4.49,3.38],[4.41,3.38],[4.33,3.37],[4.26,3.36],[4.18,3.34],[4.10,3.33],[4.03,3.32],[3.95,3.30],[3.88,3.28],[3.80,3.26],[3.73,3.24],[3.65,3.22],[3.55,3.17]],
[[3.93,1.67],[3.87,1.57],[3.83,1.47],[3.83,1.42],[3.81,1.44],[3.73,1.52],[3.65,1.60],[3.57,1.67],[3.49,1.75],[3.41,1.82],[3.32,1.89],[3.24,1.96],[3.15,2.03],[3.07,2.10],[2.98,2.17],[2.89,2.23],[2.80,2.30],[2.71,2.36],[2.61,2.42],[2.52,2.48],[2.43,2.54],[2.33,2.59],[2.23,2.65],[2.14,2.70],[2.04,2.75],[1.94,2.80],[1.84,2.85],[1.74,2.89],[1.64,2.94],[1.54,2.98],[1.43,3.02],[1.33,3.06],[1.23,3.10],[1.12,3.13],[1.02,3.17],[0.91,3.20],[0.80,3.23],[0.70,3.26],[0.59,3.28],[0.48,3.31],[0.37,3.33],[0.26,3.35],[0.16,3.37],[0.05,3.39],[-0.06,3.41],[-0.17,3.42],[-0.28,3.43],[-0.39,3.44],[-0.50,3.45],[-0.61,3.46],[-0.72,3.46],[-0.84,3.47],[-0.95,3.47],[-1.06,3.47],[-1.17,3.46],[-1.28,3.46],[-1.39,3.45],[-1.50,3.44],[-1.61,3.43],[-1.72,3.42],[-1.83,3.41],[-1.94,3.39],[-2.05,3.37],[-2.16,3.35],[-2.26,3.33],[-2.37,3.31],[-2.48,3.28],[-2.59,3.26],[-2.70,3.23],[-2.80,3.20],[-2.91,3.17],[-3.01,3.13],[-3.12,3.10],[-3.22,3.06],[-3.33,3.02],[-3.43,2.98],[-3.53,2.94],[-3.63,2.89],[-3.73,2.85],[-3.83,2.80],[-3.93,2.75],[-4.03,2.70],[-4.13,2.65],[-4.22,2.59],[-4.32,2.54],[-4.41,2.48],[-4.51,2.42],[-4.60,2.36],[-4.69,2.30],[-4.78,2.23],[-4.87,2.17],[-4.96,2.10],[-5.05,2.03],[-5.13,1.96],[-5.22,1.89],[-5.30,1.82],[-5.38,1.75],[-5.46,1.67],[-5.54,1.60],[-5.62,1.52],[-5.70,1.44],[-5.78,1.36],[-5.85,1.28],[-5.92,1.19],[-5.99,1.11],[-6.07,1.02],[-6.13,0.94],[-6.20,0.85],[-6.27,0.76],[-6.33,0.67],[-6.39,0.58],[-6.46,0.49],[-6.52,0.39],[-6.57,0.30],[-6.63,0.21],[-6.69,0.11],[-6.74,0.01],[-6.79,-0.09],[-6.84,-0.18],[-6.89,-0.28],[-6.93,-0.36],[-6.98,-0.36],[-7.19,-0.39],[-7.37,-0.48],[-7.53,-0.61],[-7.65,-0.77],[-7.72,-0.97],[-7.98,-2.08],[-8.00,-2.29],[-7.97,-2.49],[-7.88,-2.68],[-7.75,-2.84],[-7.58,-2.96],[-7.39,-3.03],[-5.58,-3.45],[-5.37,-3.47],[-5.17,-3.43],[-4.98,-3.35],[-4.82,-3.22],[-4.70,-3.05],[-4.63,-2.86],[-4.37,-1.74],[-4.35,-1.54],[-4.39,-1.33],[-4.47,-1.15],[-4.55,-1.06],[-4.53,-1.02],[-4.49,-0.96],[-4.46,-0.90],[-4.42,-0.85],[-4.38,-0.79],[-4.34,-0.73],[-4.30,-0.67],[-4.26,-0.62],[-4.22,-0.56],[-4.17,-0.51],[-4.13,-0.45],[-4.08,-0.40],[-4.04,-0.35],[-3.99,-0.30],[-3.94,-0.25],[-3.89,-0.20],[-3.84,-0.15],[-3.79,-0.10],[-3.74,-0.05],[-3.69,-0.00],[-3.64,0.04],[-3.59,0.09],[-3.53,0.13],[-3.48,0.17],[-3.42,0.21],[-3.36,0.26],[-3.31,0.30],[-3.25,0.34],[-3.19,0.37],[-3.13,0.41],[-3.07,0.45],[-3.01,0.48],[-2.95,0.52],[-2.89,0.55],[-2.83,0.58],[-2.77,0.61],[-2.70,0.64],[-2.64,0.67],[-2.58,0.70],[-2.51,0.73],[-2.45,0.75],[-2.38,0.78],[-2.31,0.80],[-2.25,0.82],[-2.18,0.84],[-2.12,0.86],[-2.05,0.88],[-1.98,0.90],[-1.91,0.92],[-1.85,0.93],[-1.78,0.95],[-1.71,0.96],[-1.64,0.97],[-1.57,0.98],[-1.50,0.99],[-1.43,1.00],[-1.36,1.01],[-1.29,1.02],[-1.22,1.02],[-1.16,1.03],[-1.09,1.03],[-1.02,1.03],[-0.95,1.03],[-0.88,1.03],[-0.81,1.03],[-0.74,1.03],[-0.67,1.02],[-0.60,1.02],[-0.53,1.01],[-0.46,1.00],[-0.39,0.99],[-0.32,0.98],[-0.25,0.97],[-0.18,0.96],[-0.11,0.95],[-0.05,0.93],[0.02,0.92],[0.09,0.90],[0.16,0.88],[0.22,0.86],[0.29,0.84],[0.36,0.82],[0.42,0.80],[0.49,0.78],[0.55,0.75],[0.62,0.73],[0.68,0.70],[0.75,0.67],[0.81,0.64],[0.87,0.61],[0.94,0.58],[1.00,0.55],[1.06,0.52],[1.12,0.48],[1.18,0.45],[1.24,0.41],[1.30,0.37],[1.36,0.34],[1.41,0.30],[1.47,0.26],[1.53,0.21],[1.58,0.17],[1.64,0.13],[1.69,0.09],[1.75,0.04],[1.80,-0.00],[1.85,-0.05],[1.90,-0.10],[1.95,-0.15],[2.00,-0.20],[2.05,-0.25],[2.10,-0.30],[2.15,-0.35],[2.19,-0.40],[2.24,-0.45],[2.28,-0.51],[2.32,-0.56],[2.37,-0.62],[2.41,-0.67],[2.45,-0.73],[2.49,-0.79],[2.53,-0.85],[2.57,-0.90],[2.60,-0.96],[2.64,-1.02],[2.66,-1.06],[2.58,-1.15],[2.50,-1.33],[2.46,-1.54],[2.48,-1.74],[2.74,-2.86],[2.81,-3.05],[2.93,-3.22],[3.09,-3.35],[3.28,-3.43],[3.48,-3.47],[3.68,-3.45],[5.50,-3.03],[5.69,-2.96],[5.86,-2.84],[5.99,-2.68],[6.07,-2.49],[6.11,-2.29],[6.09,-2.08],[5.83,-0.97],[5.76,-0.77],[5.64,-0.61],[5.48,-0.48],[5.29,-0.39],[5.09,-0.36],[5.03,-0.36],[5.00,-0.28],[4.95,-0.18],[4.90,-0.09],[4.85,0.01],[4.79,0.11],[4.74,0.21],[4.68,0.30],[4.62,0.39],[4.56,0.49],[4.50,0.58],[4.44,0.67],[4.38,0.76],[4.31,0.85],[4.24,0.94],[4.23,0.95],[4.27,0.95],[4.38,0.97],[4.41,0.98],[4.44,0.99],[4.46,0.99],[4.49,1.00],[4.51,1.00],[4.54,1.01],[4.57,1.01],[4.60,1.02],[4.62,1.02],[4.65,1.03],[4.68,1.03],[4.70,1.03],[4.73,1.03],[4.76,1.03],[4.79,1.03],[4.81,1.03],[4.84,1.03],[4.87,1.03],[4.90,1.03],[4.92,1.02],[4.95,1.02],[4.98,1.02],[5.01,1.01],[5.03,1.01],[5.06,1.00],[5.09,1.00],[5.11,0.99],[5.14,0.98],[5.16,0.97],[5.19,0.97],[5.22,0.96],[5.24,0.95],[5.27,0.94],[5.29,0.93],[5.32,0.91],[5.34,0.90],[5.37,0.89],[5.39,0.88],[5.42,0.86],[5.44,0.85],[5.46,0.84],[5.49,0.82],[5.51,0.81],[5.53,0.79],[5.55,0.77],[5.58,0.76],[5.60,0.74],[5.62,0.72],[5.64,0.71],[5.66,0.69],[5.68,0.67],[5.70,0.65],[5.72,0.63],[5.74,0.61],[5.75,0.59],[5.77,0.57],[5.79,0.55],[5.81,0.52],[5.82,0.50],[5.84,0.48],[5.85,0.46],[5.87,0.43],[5.88,0.41],[5.90,0.39],[5.96,0.30],[6.05,0.23],[6.16,0.19],[6.27,0.17],[6.38,0.19],[6.48,0.23],[6.57,0.30],[6.64,0.39],[6.68,0.49],[6.70,0.60],[6.68,0.71],[6.64,0.82],[6.62,0.86],[6.59,0.90],[6.57,0.93],[6.54,0.97],[6.52,1.01],[6.49,1.05],[6.46,1.08],[6.43,1.12],[6.40,1.15],[6.37,1.19],[6.34,1.22],[6.31,1.25],[6.28,1.28],[6.24,1.32],[6.21,1.35],[6.18,1.38],[6.14,1.41],[6.10,1.43],[6.07,1.46],[6.03,1.49],[5.99,1.52],[5.96,1.54],[5.92,1.57],[5.88,1.59],[5.84,1.61],[5.80,1.63],[5.76,1.66],[5.72,1.68],[5.68,1.70],[5.63,1.71],[5.59,1.73],[5.55,1.75],[5.51,1.76],[5.46,1.78],[5.42,1.79],[5.38,1.81],[5.33,1.82],[5.29,1.83],[5.24,1.84],[5.20,1.85],[5.15,1.86],[5.11,1.87],[5.06,1.87],[5.02,1.88],[4.97,1.88],[4.93,1.89],[4.88,1.89],[4.84,1.89],[4.79,1.89],[4.75,1.89],[4.70,1.89],[4.65,1.89],[4.61,1.88],[4.56,1.88],[4.52,1.88],[4.47,1.87],[4.43,1.86],[4.38,1.85],[4.34,1.85],[4.29,1.84],[4.25,1.82],[4.20,1.81],[4.16,1.80],[4.12,1.79],[4.02,1.74]]
];


module lid_text(str, size, x, y) {  // raised text on lid top, readable from the south side
  translate([x, y, lid_top + 0.6]) rotate([180,0,0])
    linear_extrude(0.6) text(str, size=size, font=font_latin,
                             halign="center", valign="center");
}
module lid_text_eng(str, size, x, y, font="Liberation Sans:style=Bold") {  // engraved text (0.6 deep) on lid top
  translate([x, y, lid_top + 0.05]) rotate([180,0,0])
    linear_extrude(0.65) text(str, size=size, font=font,
                              halign="center", valign="center");
}
module lid_logo(x, y) {  // selected logo (plan B), raised 0.6 on lid top, mark-up points north
  translate([x, y, lid_top + 0.6]) rotate([180, 0, 0])
    linear_extrude(0.6) for (p = logo_b_polys) polygon(p);
}

module wall_slot() {                // capsule slot through a side wall (X = through), 14 x 3
  hull() for (dy = [-5.5, 5.5]) translate([0, dy, 0]) rotate([0, 90, 0]) cylinder(d=3, h=wall+1.2);
}

// ---------- base ----------
module base() {
  difference() {
    union() {
      // shell: plinth band (bottom 1.2 mm tapers in slightly) + main block
      translate([cx, cy, 0]) linear_extrude(1.2, scale=1/0.97) rrect(out_w*0.97, out_d*0.97, corner_r);
      translate([cx, cy, 1.2]) linear_extrude(lid_bot-1.2) rrect(out_w, out_d, corner_r);
      // PCB support bosses at H1..H4 (column over the floor, PCB rests on top)
      for (p = hole_pos) translate([p[0], p[1], floor_t]) {
        cylinder(d=9, h=gap_b);
        translate([0,0,-0.01]) cylinder(d1=12.5, d2=9, h=1.2);   // base flare
      }
    }
    // cavity
    translate([cx, cy, floor_t]) linear_extrude(lid_bot) rrect(cav_w, cav_d, 2.5);
    // decorative groove line around the walls (design seam, 0.8 deep x 1.0 tall)
    translate([cx, cy, 20.5]) linear_extrude(1.0)
      difference() { rrect(out_w+0.4, out_d+0.4, corner_r+0.2); rrect(out_w-1.6, out_d-1.6, corner_r-0.8); }
    // boss pilot holes (blind, 0.9 mm floor remains)
    for (p = hole_pos) translate([p[0], p[1], 0.9]) cylinder(d=boss_hole_d, h=gap_b+floor_t);
    // floor ventilation holes (chimney intake)
    for (p = [[35,25],[60,25],[85,25],[35,60],[60,60],[85,60]])
      translate([p[0], p[1], -0.1]) cylinder(d=6, h=floor_t+0.2);
    // RJ11 cutouts in north wall (y<0 side): plug + latch pass, jack face is 4.45 mm behind case surface
    for (x = rj11_x)
      translate([x, -wall-gap_side]) translate([-6.75, -0.6, 6.8])
        cube([13.5, wall+1.2, 17.4-6.8]);
    // USB-C cutout in south wall: oversized so common plug overmoulds can enter and fully mate
    translate([usb_x, pcb_d+gap_side]) translate([-7.5, -0.6, 5.4])
      cube([15, wall+1.2, 12.6-5.4]);
    // Terminal block (J2) wire slot in south wall (wire with lid removed; cables exit with lid closed)
    translate([tb_cx, pcb_d+gap_side]) translate([-6.5, -0.6, 6.2])
      cube([13, wall+1.2, 19.0-6.2]);
    // side wall ventilation slots (east / west), 14 (along Y) x 3 (Z)
    for (yy = [22, 34, 46]) {
      translate([pcb_w+gap_side-0.6, yy, 13]) wall_slot();
      translate([-gap_side-0.6, yy, 13]) wall_slot();
    }
  }
}

// ---------- lid ----------
module lid() {
  difference() {
    union() {
      // lid plate with a bevelled top rim (machined-enclosure look)
      translate([cx, cy, lid_bot]) linear_extrude(1.2) rrect(out_w, out_d, corner_r);
      translate([cx, cy, lid_bot+1.2]) linear_extrude(lid_t-1.2, scale=0.96) rrect(out_w, out_d, corner_r);
    }
    // corner screw holes + counterbore (M3 pan head)
    for (p = hole_pos) {
      translate([p[0], p[1], lid_bot-0.1]) cylinder(d=3.4, h=lid_t+0.2);
      translate([p[0], p[1], lid_top-1.6]) cylinder(d=7, h=1.7);
    }
    // LED windows: straight 3.2 mm holes (0805 top LEDs shine through; no extra parts)
    for (p = led_pos) translate([p[0], p[1], lid_bot-0.1]) cylinder(d=3.2, h=lid_t+0.2);
    // button plunger holes
    for (p = sw_pos) translate([p[0], p[1], lid_bot-0.1]) cylinder(d=7.0, h=lid_t+0.2);
    // decorative ventilation grille (staggered slots; also vents the SLIC modules / relays)
    for (v = vent_grille) for (xx = v[1])
      translate([xx, v[0], lid_bot-0.1]) linear_extrude(lid_t+0.2) slot2d(v[2], 3);
    // engraved caution lines (west block, below the grille)
    lid_text_eng("CAUTION: RING VOLTAGE", 2.8, 33, 57.5);
    lid_text_eng("UP TO 135Vp-p - NO PSTN", 2.8, 33, 61.5);
    // high-voltage badge, engraved (north-east): border ring + lightning bolt + warning texts
    translate([99, 16.5, lid_top-0.6]) linear_extrude(0.65)
      difference() { rrect(34, 15, 2.5); rrect(31.6, 12.6, 1.6); }
    translate([85.5, 11, lid_top-0.6]) linear_extrude(0.65) polygon(bolt_pts);
    lid_text_eng("高圧注意", 4.2, 104.5, 13.3, font_cjk);
    lid_text_eng("HIGH VOLTAGE", 2.6, 104.5, 19.6);
  }
  // raised lettering (identification + credits), readable from the south side
  lid_logo(79, 63);   // plan B logo, east of the product name (clears vent grille / EN-IO0 labels / plunger bar)
  lid_text("SLIC2PORT-FXS", 6.5, 33, 66);
  lid_text("2-PORT FXS PSEUDO EXCHANGE", 2.8, 33, 71.5);
  lid_text("@GOROman  2026-10-31  Rev 4.0", 2.8, 33, 76);
  lid_text("PORT A", 3.4, 50, 20);
  lid_text("PORT B", 3.4, 74, 20);
  lid_text("EN", 3, sw_pos[0][0], 70.5);
  lid_text("IO0", 3, sw_pos[1][0], 70.5);
}

// ---------- button plungers (one twin-bar part, print 1; shafts land on SW1/SW2) ----------
// Modelled in installed orientation; origin at (button centre midpoint, lid_top plane).
module plungers() {
  shaft_len = lid_top - (pcb_top + button_h + plunger_gap);   // 14.2
  // bar (rests on lid top, bridges both buttons - centres are only 10.3 mm apart,
  // less than a single plunger's flange diameter, so one shared bar is used)
  linear_extrude(2.2, scale=0.9) rrect(23, 10, 2);
  // shafts hang below the bar (toward the buttons)
  for (sx = [-5.15, 5.15]) translate([sx, 0, 0]) rotate([180, 0, 0]) {
    cylinder(d=6.4, h=shaft_len - 1.0);
    translate([0, 0, shaft_len - 1.0]) cylinder(d1=6.4, d2=4.6, h=1.0);  // tip chamfer
  }
}

// ---------- assembly mock (renders only; simplified component blocks) ----------
module board_mock() {
  color("green") translate([0, 0, pcb_bot]) cube([pcb_w, pcb_d, pcb_t]);
  color("white") for (x = rj11_x) translate([x-6.75, 0.45, pcb_top]) cube([13.5, 13.5, 13.5]);       // RJ11 jacks
  color("silver") translate([usb_x-4.5, 81.2, pcb_top]) cube([9, 7.4, 3.3]);                          // USB-C
  color("green") translate([tb_cx-5.1, 80.2, pcb_top]) cube([10.2, 9.8, 10]);                         // terminal block J2
  color("gray") for (z = mod_zones)                                                                   // SLIC modules (vertical plates)
    translate([z[0], z[1], pcb_top+2.4]) cube(mod_size);
  color("black") for (z = relay_zones)                                                                // relays G5V-2
    translate([z[0], z[1], pcb_top]) cube(relay_size);
  color("blue") for (p = cap_pos)                                                                     // electrolytics D8
    translate([p[0], p[1], pcb_top]) cylinder(d=cap_d, h=cap_h);
  color("darkgray") translate([stamp_xy[0], stamp_xy[1], pcb_top+stamp_socket_h])                     // Stamp S3 on socket
    cube([stamp_size[0], stamp_size[1], stamp_t]);
  color("black") for (p = sw_pos) translate([p[0]-3, p[1]-3, pcb_top]) cube([6, 6, button_h]);        // switches
  color("red") for (p = led_pos) translate([p[0]-1, p[1]-0.5, pcb_top]) cube([2, 1, 0.8]);            // LEDs
}

plunger_mid = [sw_pos[0][0] + (sw_pos[1][0]-sw_pos[0][0])/2, sw_pos[0][1]];  // (75.93, 76.78)

if (part == "base") base();
else if (part == "lid") lid();
else if (part == "open") { board_mock(); color("lightgray", 1.0) base(); }
else if (part == "plungers")
  // standalone print orientation: bar on the build plate, shafts pointing up
  translate([0, 0, 2.2]) rotate([180, 0, 0]) plungers();
else { board_mock(); color("lightgray", 1.0) base(); color("dimgray", 1.0) lid();
       translate([plunger_mid[0], plunger_mid[1], lid_top]) plungers(); }
