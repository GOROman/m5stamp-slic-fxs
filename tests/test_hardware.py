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

    def test_reset_pulldowns_and_logic_jumper(self):
        for signal in ('FR_A_33','RM_A_33','SEL_A_33','TONE_PWM_33',
                       'FR_B_33','RM_B_33','SEL_B_33'):
            self.assertTrue(any(value=='100K' and
                {self.net(ref,1), self.net(ref,2)}=={signal,'GND'}
                for ref,(value,_) in self.components.items() if ref.startswith('R')))
        self.assertEqual(self.net('J7',2),'+5V')

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

if __name__=='__main__': unittest.main()
