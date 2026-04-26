##########################################################
# PSU ECE510 Post-silicon Validation Projects
# --------------------------------------------------------
# Filename: smoke.py
# --------------------------------------------------------
# Purpose: TAP Controller Smoke Tests
##########################################################

import os, sys
from tap.common.loopback import *
from tap.common.tap import *
import unittest

class smoke(unittest.TestCase):
    """ smoke/power on tests, hopefully won't produce actual smoke """
    
    def setUp(self):
        """ fires before each test
        Setting up for the test
    
        """
        log_level = LOG_LEVEL 
        self.logger = get_logger(self.id(), log_level)
        log(self.logger, 'info', '{}Running {}'.format(color_map['highlight'],self.id()))

        self.tap = Tap(log_level=log_level)
        self.loopback_monitor = LoopBack(log_level=log_level)
        self.loopback_monitor.set_monitor()
    
    def tearDown(self):
        """ fires after each test
        Cleaning up after the test
    
        """
        self.loopback_monitor.remove_monitor()
        self.tap.clean_up()
        log(self.logger, 'info', '{}Done with {}\n'.format(color_map['highlight'],self.id()))    
    
    def testReset(self):
        # This test was already here in the original skeleton - NOT CHANGED
        self.tap.reset()
        self.assertEqual("Test_Logic_Reset",self.loopback_monitor.cur_state)

    # ---- ADDED ----
    # Original had @unittest.skip and pass inside.
    # Removed @unittest.skip so the test actually runs.
    # Added the actual test body below.
    def testReset2ShiftIR(self):
        """ Test that reset -> ShiftIR navigation lands in Shift_IR.

        Steps:
          1. Call reset() to get to Test_Logic_Reset
          2. Call reset2ShiftIR() to navigate to Shift_IR
          3. Check loopback_monitor.cur_state == 'Shift_IR'

        The loopback_monitor physically listens to the TMS and TCK GPIO
        pins via interrupt callbacks. So cur_state reflects what the
        actual hardware saw, not just what we think happened.
        """
        # Step 1: Get to known state first
        self.tap.reset()
        self.assertEqual("Test_Logic_Reset", self.loopback_monitor.cur_state)

        # Step 2: Navigate to Shift_IR
        # TMS sequence driven: 0,1,1,0,0
        self.tap.reset2ShiftIR()

        # Step 3: Verify loopback monitor tracked the correct final state
        self.assertEqual("Shift_IR", self.loopback_monitor.cur_state)
    # ---- END ADDED ----

    # ---- ADDED ----
    # This test was NOT in the original skeleton at all.
    # Added it because the project doc specifically lists
    # testExit1IR2ShiftDR as a required routine to test.
    def testExit1IR2ShiftDR(self):
        """ Test that Exit1_IR -> ShiftDR navigation lands in Shift_DR.

        Steps:
          1. Reset and navigate to Shift_IR
          2. Clock one bit with TMS=1 to manually enter Exit1_IR
          3. Call exit1IR2ShiftDR() to navigate to Shift_DR
          4. Check loopback_monitor.cur_state == 'Shift_DR'
        """
        # Step 1: Get to Shift_IR
        self.tap.reset()
        self.tap.reset2ShiftIR()
        self.assertEqual("Shift_IR", self.loopback_monitor.cur_state)

        # Step 2: Clock one bit with TMS=1 to enter Exit1_IR
        # (Shift_IR --(TMS=1)--> Exit1_IR from tap_model.py)
        self.tap.toggle_tck(tms=1, tdi=0)
        self.assertEqual("Exit1_IR", self.loopback_monitor.cur_state)

        # Step 3: Navigate Exit1_IR -> Shift_DR
        # TMS sequence driven: 1,1,0,0
        self.tap.exit1IR2ShiftDR()

        # Step 4: Verify final state
        self.assertEqual("Shift_DR", self.loopback_monitor.cur_state)
    # ---- END ADDED ----

    # ---- ADDED ----
    # Original had @unittest.skip and pass inside.
    # Removed @unittest.skip so the test actually runs.
    # Added the full IDCODE read flow below.
    def testReadDeviceCode(self):
        """ Test reading the 32-bit IDCODE from the Xilinx Spartan-6 FPGA.

        Full flow (from Spartan-6 config user guide chapter 10):
          1. Reset TAP to Test_Logic_Reset
          2. Navigate to Shift_IR
          3. Shift in IDCODE instruction opcode "100100" (6 bits, LSB first)
             Last bit automatically exits to Exit1_IR
          4. Navigate Exit1_IR -> Shift_DR
          5. Shift out 32 bits from TDO -> this is the IDCODE value
          6. Verify IDCODE is valid:
             - Bit 0 must be 1 (required by IEEE 1149.1 for all IDCODEs)
             - Bits [11:1] must be 0x049 (Xilinx manufacturer ID)
        """
        # Step 1: Reset to known state
        self.tap.reset()
        self.assertEqual("Test_Logic_Reset", self.loopback_monitor.cur_state)

        # Step 2: Navigate to Shift_IR
        self.tap.reset2ShiftIR()
        self.assertEqual("Shift_IR", self.loopback_monitor.cur_state)

        # Step 3: Shift in IDCODE instruction opcode
        # "100100" is the 6-bit IDCODE opcode sent LSB first
        # Last bit sets TMS=1 automatically -> moves to Exit1_IR
        self.tap.shiftInData("100100")
        self.assertEqual("Exit1_IR", self.loopback_monitor.cur_state)

        # Step 4: Navigate Exit1_IR -> Shift_DR
        # TMS sequence: 1,1,0,0
        self.tap.exit1IR2ShiftDR()
        self.assertEqual("Shift_DR", self.loopback_monitor.cur_state)

        # Step 5: Shift out 32 bits of IDCODE from TDO
        idcode = self.tap.shiftOutData(32)
        log(self.logger, 'info', 'Device IDCODE: {:#010x}'.format(idcode))

        # Step 6a: Bit 0 must always be 1 per IEEE 1149.1 standard
        self.assertEqual(1, idcode & 0x1,
                         "IDCODE bit 0 should be 1, got {:#010x}".format(idcode))

        # Step 6b: IDCODE should not be all zeros or all ones (bad read)
        self.assertNotEqual(0x00000000, idcode, "IDCODE should not be zero")
        self.assertNotEqual(0xFFFFFFFF, idcode, "IDCODE should not be all ones")

        # Step 6c: Check Xilinx manufacturer ID in bits [11:1] = 0x049
        # IDCODE bit layout: [31:28]=version, [27:12]=part, [11:1]=mfr, [0]=1
        manufacturer_id = (idcode >> 1) & 0x7FF
        self.assertEqual(0x049, manufacturer_id,
                         "Xilinx manufacturer ID should be 0x049, "
                         "got {:#05x}".format(manufacturer_id))
    # ---- END ADDED ----
