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
corner_r  = 4.0;            // outer corner radius

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

$fn = 48;

// ---------- helpers ----------
module rrect(w, d, r) {             // rounded rect centred at origin (2D)
  hull() for (sx=[-1,1], sy=[-1,1])
    translate([sx*(w/2-r), sy*(d/2-r)]) circle(r=r);
}
module slot2d(len, w) {             // horizontal rounded slot centred at origin (2D)
  hull() { translate([-len/2+w/2,0]) circle(d=w); translate([len/2-w/2,0]) circle(d=w); }
}
module lid_text(str, size, x, y) {  // raised text on lid top, readable from the south side
  translate([x, y, lid_top + 0.6]) rotate([180,0,0])
    linear_extrude(0.6) text(str, size=size, font="Liberation Sans:style=Bold",
                             halign="center", valign="center");
}
module wall_slot() {                // capsule slot through a side wall (X = through), 14 x 3
  hull() for (dy = [-5.5, 5.5]) translate([0, dy, 0]) rotate([0, 90, 0]) cylinder(d=3, h=wall+1.2);
}

// ---------- base ----------
module base() {
  difference() {
    union() {
      // shell: outer block minus cavity is done in difference; start with solid block
      translate([cx, cy, 0]) linear_extrude(lid_bot) rrect(out_w, out_d, corner_r);
      // PCB support bosses at H1..H4 (column over the floor, PCB rests on top)
      for (p = hole_pos) translate([p[0], p[1], floor_t]) {
        cylinder(d=9, h=gap_b);
        translate([0,0,-0.01]) cylinder(d1=12.5, d2=9, h=1.2);   // base flare
      }
    }
    // cavity
    translate([cx, cy, floor_t]) linear_extrude(lid_bot) rrect(cav_w, cav_d, 2.5);
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
    translate([cx, cy, lid_bot]) linear_extrude(lid_t) rrect(out_w, out_d, corner_r);
    // corner screw holes + counterbore (M3 pan head)
    for (p = hole_pos) {
      translate([p[0], p[1], lid_bot-0.1]) cylinder(d=3.4, h=lid_t+0.2);
      translate([p[0], p[1], lid_top-1.6]) cylinder(d=7, h=1.7);
    }
    // LED windows: straight 3.2 mm holes (0805 top LEDs shine through; no extra parts)
    for (p = led_pos) translate([p[0], p[1], lid_bot-0.1]) cylinder(d=3.2, h=lid_t+0.2);
    // button plunger holes
    for (p = sw_pos) translate([p[0], p[1], lid_bot-0.1]) cylinder(d=7.0, h=lid_t+0.2);
    // ventilation slots over SLIC modules (main heat source when ringing)
    for (yy = [31.5, 36.5], xx = [37, 51, 65])
      translate([xx, yy, lid_bot-0.1]) linear_extrude(lid_t+0.2) slot2d(14, 3);
    for (yy = [45, 49.5], xx = [58, 72, 86])
      translate([xx, yy, lid_bot-0.1]) linear_extrude(lid_t+0.2) slot2d(14, 3);
    // ventilation slots over relay K1
    for (yy = [56, 60.5], xx = [36, 46])
      translate([xx, yy, lid_bot-0.1]) linear_extrude(lid_t+0.2) slot2d(12, 3);
    // ventilation slots over relay K2
    for (yy = [33, 38])
      translate([108, yy, lid_bot-0.1]) linear_extrude(lid_t+0.2) slot2d(14, 3);
  }
  // raised lettering (safety + identification), readable from the south side
  lid_text("SLIC2PORT-FXS", 6, 34, 67);
  lid_text("2-PORT FXS PSEUDO EXCHANGE", 3, 34, 73.5);
  lid_text("CAUTION: RING VOLTAGE", 3.2, 93, 58);
  lid_text("UP TO 135Vp-p - NO PSTN", 3.2, 93, 63.5);
  lid_text("PORT A", 3.4, 50, 20);
  lid_text("PORT B", 3.4, 76, 20);
  lid_text("EN", 3, sw_pos[0][0], 70.5);
  lid_text("IO0", 3, sw_pos[1][0], 70.5);
}

// ---------- button plungers (one twin-bar part, print 1; shafts land on SW1/SW2) ----------
// Modelled in installed orientation; origin at (button centre midpoint, lid_top plane).
module plungers() {
  shaft_len = lid_top - (pcb_top + button_h + plunger_gap);   // 14.2
  // bar (rests on lid top, bridges both buttons - centres are only 10.3 mm apart,
  // less than a single plunger's flange diameter, so one shared bar is used)
  linear_extrude(2.2) rrect(23, 10, 2);
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
  color("green") translate([27.4, 80.2, pcb_top]) cube([10.2, 9.8, 10]);                              // terminal block J2
  color("gray") {                                                                                     // SLIC modules (vertical plates)
    translate([24.5, 30.8, pcb_top+2.4]) cube([50.2, 6.3, 13.0]);
    translate([45.3, 43.8, pcb_top+2.4]) cube([50.2, 6.3, 13.0]);
  }
  color("black") {                                                                                    // relays G5V-2
    translate([30.4, 52.9, pcb_top]) cube([20.5, 10.1, 11.5]);
    translate([98.4, 30.4, pcb_top]) cube([20.5, 10.1, 11.5]);
  }
  color("blue") for (p = [[22.52,65.28],[54.12,56.98],[4.53,61.77]])                                  // electrolytics D8
    translate([p[0], p[1], pcb_top]) cylinder(d=8, h=12);
  color("darkgray") translate([41, 65, pcb_top+4.3]) cube([18, 24, 3]);                               // Stamp S3 on socket
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
