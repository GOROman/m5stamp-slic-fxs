import csv
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'kicad/skidl/m5stamp_slic2port.py'
spec = importlib.util.spec_from_file_location('bom', SOURCE.with_name('export_bom.py'))
bom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bom)

class HardwareTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.components, cls.nets = bom.read_netlist(SOURCE.with_suffix('.net'))

    def net(self, ref, pin):
        return self.nets[(ref, str(pin))]

    def test_generated_connectivity_matches_source(self):
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run([sys.executable, str(SOURCE)], cwd=temp, check=True, capture_output=True)
            components, nets = bom.read_netlist(Path(temp)/SOURCE.with_suffix('.net').name)
        self.assertEqual(components, self.components)
        self.assertEqual(nets, self.nets)

    def test_usb_actual_pad_numbers(self):
        for pin in ('A1','A12','B1','B12','S1'):
            self.assertEqual(self.net('J1',pin), 'GND')
        for pin in ('A4','A9','B4','B9'):
            self.assertEqual(self.net('J1',pin), 'VIN_RAW')
        self.assertEqual(self.net('J1','A5'),self.net('R1',1))
        self.assertEqual(self.net('J1','B5'),self.net('R2',1))
        self.assertEqual(self.net('R1',2),'GND')
        self.assertEqual(self.net('R2',2),'GND')
        self.assertEqual({p for r,p in self.nets if r=='J1'},
                         {'A1','A12','B1','B12','S1','A4','A9','B4','B9','A5','B5'})

    def test_polarity_and_reverse_protection(self):
        self.assertEqual(self.net('Q1',2),'+5V') # source, protected side
        self.assertEqual(self.net('Q1',3),'VIN_F') # drain, input side
        self.assertEqual(self.net('D1',1),'+5V') # cathode
        self.assertEqual(self.net('D1',2),'GND')
        for ref in ('D2','D3'):
            self.assertEqual(self.net(ref,1),'GND')
        for ref, (value, _) in self.components.items():
            if value=='1N4004':
                # Every PD diode cathode goes toward the pull-down FET.
                if self.net(ref,2).startswith('PD_'):
                    self.assertEqual(self.net(ref,1),'PD_BUS')

    def test_reset_pulldowns(self):
        # 元は SEL_Z ロジックジャンパ J7 (pin2 = +5V) も検証していたが、J7 は
        # CD4053 -> リレー化 (1eb012c) で Z チャネルごと設計から削除された
        # 実在しない部品のため、その検証は削除した。プルダウン検証は不変。
        for signal in ('FR_A_33','RM_A_33','SEL_A_33','TONE_PWM_33',
                       'FR_B_33','RM_B_33','SEL_B_33'):
            self.assertTrue(any(value=='100K' and
                {self.net(ref,1), self.net(ref,2)}=={signal,'GND'}
                for ref,(value,_) in self.components.items() if ref.startswith('R')))

    def test_tone_is_ac_coupled(self):
        self.assertEqual({self.net('C9',1),self.net('C9',2)}, {'TONE_N2','TONE_AC'})
        self.assertEqual({self.net('R11',1),self.net('R11',2)}, {'TONE_AC','TONE_BUS'})
        for ref in ('C7','C8'):
            self.assertEqual(self.components[ref][0], '47nF')

    def test_bom_matches_netlist(self):
        with (ROOT/'bom.csv').open(newline='') as f:
            rows=list(csv.DictReader(f))
        actual={}
        for row in rows:
            refs=row['Refs'].split()
            self.assertEqual(len(refs),int(row['Qty']))
            for ref in refs:
                self.assertNotIn(ref,actual)
                actual[ref]=(row['Value'],row['Footprint'])
        self.assertEqual(actual,self.components)

    def test_rj11_pads_do_not_overlap(self):
        fp=(ROOT/'kicad/SLIC2PORT.pretty/RJ11_6P6C_TH.kicad_mod').read_text()
        pads=re.findall(r'\(pad "\d+" thru_hole \w+ \(at ([\d.-]+) [\d.-]+\) \(size ([\d.]+) [\d.]+\)',fp)
        self.assertEqual(len(pads),6)
        pads=sorted((float(x),float(w)) for x,w in pads)
        for (x,w),(nx,nw) in zip(pads,pads[1:]):
            # Design point is 0.12mm (Issue #6): JLCPCB 1oz min spacing is
            # 0.10mm, so keep a guard just above the design value's floor.
            self.assertGreater(nx-x-(w+nw)/2,0.11)

    def test_rj11_annular_ring_meets_jlcpcb_min(self):
        # Issue #6: short-side annular ring must satisfy JLCPCB 2-layer 1oz
        # PTH capability (absolute minimum 0.18mm; design point 0.20mm).
        fp=(ROOT/'kicad/SLIC2PORT.pretty/RJ11_6P6C_TH.kicad_mod').read_text()
        pads=re.findall(r'\(pad "\d+" thru_hole \w+ \(at [\d.-]+ [\d.-]+\) \(size ([\d.]+) ([\d.]+)\) \(drill ([\d.]+)\)',fp)
        self.assertEqual(len(pads),6)
        for w,l,d in pads:
            w,l,d=float(w),float(l),float(d)
            self.assertGreaterEqual((w-d)/2,0.18)   # short side (pitch dir)
            self.assertGreaterEqual((l-d)/2,0.18)   # long side
            self.assertEqual(d,0.75)  # JST MOD-J6 hole band 0.8+/-0.05, Issue #6 spec


    def test_placement_json_matches_netlist(self):
        # Issue #13: the placement JSON (kicad/netlist_v32.json) is generated
        # from the saved netlist by kicad/net2json.py. It drifted once (PD
        # diodes U79/U106 kept 1N4007 after the source moved to 1N5819), so
        # pin the JSON to the netlist on values, footprints and net membership.
        import json
        data = json.loads((ROOT / 'kicad/netlist_v32.json').read_text())
        comps = {ref: {'value': value, 'footprint': footprint}
                 for ref, (value, footprint) in self.components.items()}
        self.assertEqual(data['comps'], comps)
        nets = {}
        for (ref, pin), name in self.nets.items():
            nets.setdefault(name, []).append([ref, pin])
        for name in nets:
            nets[name] = sorted(nets[name])
        self.assertEqual({k: sorted(v) for k, v in data['nets'].items()}, nets)

    def test_all_pth_annular_ring_meets_jlcpcb_min(self):
        # Issues #6/#11: every PTH pad in the board and in the local socket
        # footprint must keep >= 0.18mm annular ring (JLCPCB 2-layer 1oz
        # absolute minimum). Design point across the board is 0.20mm.
        import sexpdata
        def pads_of(tree):
            for node in tree[1:]:
                if not (isinstance(node, list) and node and str(node[0]) == 'footprint'):
                    continue
                ref = None
                for ch in node[1:]:
                    if isinstance(ch, list) and str(ch[0]) == 'property' and str(ch[1]) == 'Reference':
                        ref = str(ch[2])
                for ch in node[1:]:
                    if isinstance(ch, list) and str(ch[0]) == 'pad':
                        yield ref, ch
        def ring(ch):
            toks = [str(t) for t in ch[1:4]]
            if 'thru_hole' not in toks or 'np_thru_hole' in toks:
                return None
            d = {str(i[0]): i[1:] for i in ch[1:] if isinstance(i, list)}
            if 'drill' not in d or 'size' not in d:
                return None
            dv = [str(x) for x in d['drill']]
            if dv[0] == 'oval':
                dw, dh = float(dv[1]), float(dv[2])
            else:
                dw = dh = float(dv[0])
            return min((float(d['size'][0]) - dw) / 2, (float(d['size'][1]) - dh) / 2)
        checked = 0
        for path in (ROOT / 'kicad/SLIC2PORT-FXS.kicad_pcb',
                     ROOT / 'kicad/SLIC2PORT.pretty/Stamp-S3-Socket.kicad_mod'):
            tree = sexpdata.loads(path.read_text())
            if str(tree[0]) == 'footprint':
                tree = [None, tree]
            for ref, ch in pads_of(tree):
                r = ring(ch)
                if r is not None:
                    checked += 1
                    self.assertGreaterEqual(r, 0.18, f'{path.name}:{ref} pad {ch[1]}')
        self.assertGreater(checked, 170)  # guard against silently scanning nothing

class ProtectionTopologyTests(unittest.TestCase):
    """Issue #9 item 3: manufacturer GND-referenced clamp (Ag1171 Fig.4 /
    KS0835F Typical Connection). Bridge minus-side anodes and the zener
    anode go to GND, not to a floating BRM rail."""

    def test_protection_minus_side_is_gnd(self):
        _, nets = bom.read_netlist(SOURCE.with_suffix(".net"))
        for ref in ("U58", "U59", "U60", "U85", "U86", "U87"):
            self.assertEqual(nets.get((ref, "2")), "GND",
                             ref + " pin 2 (anode) must be GND")
        self.assertFalse([n for n in set(nets.values()) if n.startswith("BRM")],
                         "no floating BRM rail may remain")
        self.assertEqual(nets.get(("U56", "1")), "BRP_A")
        self.assertEqual(nets.get(("U58", "1")), "TIP_A")
        self.assertEqual(nets.get(("U85", "1")), "TIP_B")


class Rj11ManufacturabilityTests(unittest.TestCase):
    """Issue #9/#6: RJ11 intra-footprint pad gap must clear the JLCPCB
    minimum spacing 0.127mm with the PTH annular ring >= 0.18mm."""

    def test_rj11_gap_and_annular(self):
        text = (ROOT / "kicad" / "SLIC2PORT.pretty" / "RJ11_6P6C_TH.kicad_mod").read_text()
        pads = re.findall(r'\(pad "\d+" .*?\(at ([-\d.]+) ([-\d.]+)\).*?\(size ([\d.]+) ([\d.]+)\).*?\(drill ([\d.]+)\)', text, re.S)
        self.assertEqual(len(pads), 6)
        xs = sorted(float(p[0]) for p in pads)
        w = float(pads[0][2]); drill = float(pads[0][4])
        pitch = round(xs[1] - xs[0], 3)
        self.assertEqual(pitch, 1.27)
        gap = pitch - w
        annular = (w - drill) / 2
        self.assertGreaterEqual(gap, 0.127, "pad gap below JLCPCB min spacing")
        self.assertGreaterEqual(annular, 0.18, "annular ring below JLCPCB min")

if __name__=='__main__': unittest.main()
