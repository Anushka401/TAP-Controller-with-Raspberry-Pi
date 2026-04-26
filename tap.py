##########################################################
# PSU ECE510 Post-silicon Validation Project 1
# --------------------------------------------------------
# Filename: tap.py
# --------------------------------------------------------
# Purpose: TAP Controler Class
##########################################################

from tap.common.tap_gpio import *
from tap.log.logging_setup import *
import time

class Tap(Tap_GPIO):
    """ Class for JTAG TAP Controller"""

    def __init__(self,log_level=logging.INFO):
        """ initialize TAP """
        self.logger = get_logger(__file__,log_level)
        self.max_length = 1000

        #set up the RPi TAP pins
        Tap_GPIO.__init__(self)

    def toggle_tck(self, tms, tdi):
        """ toggle TCK for state transition 

        :param tms: data for TMS pin
        :type tms: int (0/1)
        :param tdi: data for TDI pin
        :type tdi: int (0/1)

        """
        
        # ---- ADDED ----
        # The TAP state machine advances only on the RISING edge of TCK.
        # So we pulse TCK: low -> high -> low to create one rising edge.
        # The DUT reads TMS on that rising edge and moves to the next state.

        # Step 1: Set TMS and TDI with TCK low (setup time)
        self.set_io_data(tms, tdi, 0)

        # Step 2: Bring TCK high -> this is the rising edge the DUT sees
        self.set_io_data(tms, tdi, 1)

        # Step 3: Bring TCK back low, ready for next toggle
        self.set_io_data(tms, tdi, 0)
        # ---- END ADDED ----
       
    def reset(self):
        """ set TAP state to Test_Logic_Reset """

        # ---- ADDED ----
        # IEEE 1149.1 standard guarantees that driving TMS=1 for 5
        # consecutive TCK rising edges lands in Test_Logic_Reset
        # from ANY state. This gives us a known starting point.
        log(self.logger, 'debug', 'reset()')
        for _ in range(5):
            self.toggle_tck(tms=1, tdi=0)
        # ---- END ADDED ----

    def reset2ShiftIR(self):
        """ shift TAP state from reset to shiftIR """
        
        # ---- ADDED ----
        # Path traced from tap_model.py state machine dictionary:
        #   Test_Logic_Reset --(TMS=0)--> Run_Test_Idle
        #   Run_Test_Idle    --(TMS=1)--> Select_DR_Scan
        #   Select_DR_Scan   --(TMS=1)--> Select_IR_Scan
        #   Select_IR_Scan   --(TMS=0)--> Capture_IR
        #   Capture_IR       --(TMS=0)--> Shift_IR
        # TMS sequence = 0, 1, 1, 0, 0
        log(self.logger, 'debug', 'reset2ShiftIR()')
        self.toggle_tck(tms=0, tdi=0)  # Test_Logic_Reset -> Run_Test_Idle
        self.toggle_tck(tms=1, tdi=0)  # Run_Test_Idle    -> Select_DR_Scan
        self.toggle_tck(tms=1, tdi=0)  # Select_DR_Scan   -> Select_IR_Scan
        self.toggle_tck(tms=0, tdi=0)  # Select_IR_Scan   -> Capture_IR
        self.toggle_tck(tms=0, tdi=0)  # Capture_IR       -> Shift_IR
        # ---- END ADDED ----

    def exit1IR2ShiftDR(self):
        """ shift TAP state from exit1IR to shiftDR """

        # ---- ADDED ----
        # Path traced from tap_model.py state machine dictionary:
        #   Exit1_IR       --(TMS=1)--> Update_IR
        #   Update_IR      --(TMS=1)--> Select_DR_Scan
        #   Select_DR_Scan --(TMS=0)--> Capture_DR
        #   Capture_DR     --(TMS=0)--> Shift_DR
        # TMS sequence = 1, 1, 0, 0
        log(self.logger, 'debug', 'exit1IR2ShiftDR()')
        self.toggle_tck(tms=1, tdi=0)  # Exit1_IR       -> Update_IR
        self.toggle_tck(tms=1, tdi=0)  # Update_IR      -> Select_DR_Scan
        self.toggle_tck(tms=0, tdi=0)  # Select_DR_Scan -> Capture_DR
        self.toggle_tck(tms=0, tdi=0)  # Capture_DR     -> Shift_DR
        # ---- END ADDED ----

    def exit1DR2ShiftIR(self):
        """ shift TAP state from exit1DR to shiftIR """
        
        # ---- ADDED ----
        # Path traced from tap_model.py state machine dictionary:
        #   Exit1_DR       --(TMS=1)--> Update_DR
        #   Update_DR      --(TMS=1)--> Select_DR_Scan
        #   Select_DR_Scan --(TMS=1)--> Select_IR_Scan
        #   Select_IR_Scan --(TMS=0)--> Capture_IR
        #   Capture_IR     --(TMS=0)--> Shift_IR
        # TMS sequence = 1, 1, 1, 0, 0
        log(self.logger, 'debug', 'exit1DR2ShiftIR()')
        self.toggle_tck(tms=1, tdi=0)  # Exit1_DR       -> Update_DR
        self.toggle_tck(tms=1, tdi=0)  # Update_DR      -> Select_DR_Scan
        self.toggle_tck(tms=1, tdi=0)  # Select_DR_Scan -> Select_IR_Scan
        self.toggle_tck(tms=0, tdi=0)  # Select_IR_Scan -> Capture_IR
        self.toggle_tck(tms=0, tdi=0)  # Capture_IR     -> Shift_IR
        # ---- END ADDED ----

    def shiftInData(self, tdi_str):    
        """ shift in IR/DR data

        :param tdi_str: TDI data to shift in
        :type tdo_str: str

        """

        # ---- ADDED ----
        # While in Shift_IR or Shift_DR, the state machine stays in
        # the shift state as long as TMS=0 (from tap_model.py):
        #   'Shift_IR' : {'0':'Shift_IR', '1':'Exit1_IR'}
        #   'Shift_DR' : {'0':'Shift_DR', '1':'Exit1_DR'}
        #
        # So we clock each bit with TMS=0 to stay in shift state.
        # On the LAST bit we set TMS=1 to automatically exit to Exit1.
        # This way shiftInData() always ends in Exit1_IR or Exit1_DR.
        log(self.logger, 'debug', 'shiftInData({})'.format(tdi_str))
        for i, bit in enumerate(tdi_str):
            # Last bit: TMS=1 to exit Shift state -> Exit1
            # All other bits: TMS=0 to stay in Shift state
            tms = 1 if i == len(tdi_str) - 1 else 0
            self.toggle_tck(tms=tms, tdi=int(bit))
        # ---- END ADDED ----

    def shiftOutData(self, length):
        """ get IR/DR data

        :param length: chain length        
        :type length: int
        :returns: int - TDO data

        """

        # ---- ADDED ----
        # While in Shift_DR, each TCK rising edge shifts one bit out on TDO.
        # We manually control TCK here (instead of using toggle_tck) because
        # we need to READ TDO while TCK is HIGH - that is when data is valid.
        #
        # Bits come out LSB first, so bit 0 arrives first.
        # We use: result |= (tdo_bit << i) to build the integer LSB first.
        #
        # Same as shiftInData: last bit uses TMS=1 to exit Shift_DR -> Exit1_DR.
        log(self.logger, 'debug', 'shiftOutData({})'.format(length))
        result = 0
        for i in range(length):
            # Last bit: TMS=1 to exit Shift_DR -> Exit1_DR
            tms = 1 if i == length - 1 else 0

            # TCK low (setup)
            self.set_io_data(tms, 0, 0)
            # TCK high (rising edge - DUT shifts out next bit onto TDO)
            self.set_io_data(tms, 0, 1)
            # READ TDO while TCK is high - this is when data is valid
            tdo_bit = self.read_tdo_data()
            # TCK low again
            self.set_io_data(tms, 0, 0)

            # Place this bit at position i in the result (LSB first)
            result |= (tdo_bit << i)

        return result
        # ---- END ADDED ----

    def getChainLength(self):
        """ get chain length

        :returns: int -- chain length	

        """

        # ---- ADDED ----
        # Uses the bypass register technique:
        # In bypass mode, each device in the chain has a 1-bit register
        # between TDI and TDO. So a '1' shifted in appears on TDO after
        # exactly N clock cycles where N = number of devices in chain.
        #
        # Steps:
        # 1. Flush entire chain with 0s (up to max_length)
        # 2. Shift in a single '1'
        # 3. Count clocks until that '1' appears on TDO
        # 4. That count = chain length
        log(self.logger, 'debug', 'getChainLength()')

        # Step 1: Flush the chain with 0s so we have a clean baseline
        for i in range(self.max_length):
            # Last bit: TMS=1 to exit Shift state
            tms = 1 if i == self.max_length - 1 else 0
            self.toggle_tck(tms=tms, tdi=0)

        # Now we are in Exit1_DR, go back to Shift_DR via:
        # Exit1_DR --(TMS=0)--> Pause_DR
        # Pause_DR --(TMS=1)--> Exit2_DR
        # Exit2_DR --(TMS=0)--> Shift_DR
        self.toggle_tck(tms=0, tdi=0)  # Exit1_DR -> Pause_DR
        self.toggle_tck(tms=1, tdi=0)  # Pause_DR -> Exit2_DR
        self.toggle_tck(tms=0, tdi=0)  # Exit2_DR -> Shift_DR

        # Step 2: Shift in a single '1' (TMS=0 to stay in Shift_DR)
        self.set_io_data(0, 1, 0)   # TCK low, TDI=1
        self.set_io_data(0, 1, 1)   # TCK high -> '1' enters chain
        self.set_io_data(0, 1, 0)   # TCK low

        # Step 3: Keep shifting 0s and count until the '1' comes out on TDO
        length = 0
        for i in range(self.max_length):
            tms = 1 if i == self.max_length - 1 else 0
            self.set_io_data(tms, 0, 0)    # TCK low
            self.set_io_data(tms, 0, 1)    # TCK high
            tdo_bit = self.read_tdo_data()  # read TDO while high
            self.set_io_data(tms, 0, 0)    # TCK low
            length += 1
            if tdo_bit == 1:               # '1' appeared -> done
                break

        return length
        # ---- END ADDED ----
