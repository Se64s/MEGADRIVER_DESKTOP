#! /usr/bin/env python
"""
Set a register preset to test different configurations on YM2612 chip
"""
from __future__ import print_function
import sys
import time
import rtmidi
import struct
import logging

# Defined constants
YM_MAX_NUM_USER_PRESETS = 5
YM_MAX_NUM_DEFAULT_PRESETS = 8

# Num voices
YM_MAX_VOICES = 6

# Num operators
YM_MAX_OPERATORS = 4

# Defined SYSEX CMD
YM_SYSEX_CMD_SET_REG = 0
YM_SYSEX_CMD_SAVE_PRESET = 1
YM_SYSEX_CMD_LOAD_PRESET = 2
YM_SYSEX_CMD_LOAD_DEFAULT_PRESET = 3

# Defined default PRESETS
YM_PRESET_DX_PIANO = 0
YM_PRESET_GUITAR = 1
YM_PRESET_SAWTOOTH = 2
YM_PRESET_SONIC = 3

# Minimun elay between commands
YM_MIDI_DELAY = 0.2

class YM2612Chip:
    """
    Class to handle and store information regading to FM synth chip
    """
    def __init__(self, midi_out=None, lfo_on=0, lfo_freq=0):
        # Init logger
        self.logger = logging.getLogger('fmDriver')
        self.logger.setLevel(logging.DEBUG)
        logFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logHandler = logging.StreamHandler()
        logHandler.setLevel(logging.DEBUG)
        logHandler.setFormatter(logFormatter)
        self.logger.addHandler(logHandler)
        # Create midi connection handler
        self.midiout = midi_out
        # Vendor id
        self.vendor_id = 0x001234
        # Chip general register
        self.lfo_on = lfo_on
        self.lfo_freq = lfo_freq
        # Channel definition
        self.channel = {
            0: self.__YMChannel(channel_id=0),
            1: self.__YMChannel(channel_id=1),
            2: self.__YMChannel(channel_id=2),
            3: self.__YMChannel(channel_id=3),
            4: self.__YMChannel(channel_id=4),
            5: self.__YMChannel(channel_id=5)
        }

    def __send_midi_cmd(self, midi_cmd, cmd_payload):
        retval = False
        # Check if midi interface def
        if self.midiout:
            self.logger.info("Send data start")
            # CMD set preset
            sysex_cmd = midi_cmd
            # Set data into array
            sysex_data = []
            # SysEx init
            sysex_data.append(0xF0) # SysEx init
            # Vendor id
            sysex_data.append((self.vendor_id >> 16) & 0xFF)
            sysex_data.append((self.vendor_id >> 8) & 0xFF)
            sysex_data.append((self.vendor_id >> 0) & 0xFF)
            # Cmd
            sysex_data.append(sysex_cmd)
            # Preset pos
            sysex_data.extend(cmd_payload)
            # SysEx end
            sysex_data.append(0xF7)
            # Data TX
            self.midiout.send_message(sysex_data)
            # Show used parameters
            self.logger.info("Data len %d" % len(sysex_data))
            self.logger.info("SysEx CMD x%02X" % sysex_cmd)
            self.logger.info("Send finish")
            retval = True
        else:
            self.logger.info("Not init")
        time.sleep(YM_MIDI_DELAY)
        return retval

    def __get_LFO(self):
        reg = ((self.lfo_on & 0x01) << 3) | (self.lfo_freq & 0x07)
        return reg

    def __get_reg_values_array(self):
        reg_array = []
        # Get general regs
        reg_array.append(self.lfo_on)
        reg_array.append(self.lfo_freq)
        # Get channel info
        for ch_id in range(6):
            reg_array.append(self.channel[ch_id].feedback)
            reg_array.append(self.channel[ch_id].op_algorithm)
            reg_array.append(self.channel[ch_id].audio_out)
            reg_array.append(self.channel[ch_id].amp_mod_sens)
            reg_array.append(self.channel[ch_id].phase_mod_sens)
            # Add operator data
            for op_id in range(4):
                reg_array.append(self.channel[ch_id].operator[op_id].detune)
                reg_array.append(self.channel[ch_id].operator[op_id].multiple)
                reg_array.append(self.channel[ch_id].operator[op_id].total_level)
                reg_array.append(self.channel[ch_id].operator[op_id].key_scale)
                reg_array.append(self.channel[ch_id].operator[op_id].attack_rate)
                reg_array.append(self.channel[ch_id].operator[op_id].amp_mod_on)
                reg_array.append(self.channel[ch_id].operator[op_id].decay_rate)
                reg_array.append(self.channel[ch_id].operator[op_id].sustain_rate)
                reg_array.append(self.channel[ch_id].operator[op_id].sustain_level)
                reg_array.append(self.channel[ch_id].operator[op_id].release_rate)
                reg_array.append(self.channel[ch_id].operator[op_id].ssg_envelope)
        # Return collected data
        return reg_array

    def __read_byte(self, file_handler):
        return struct.unpack('B', file_handler.read(1))[0]

    def show_reg_values(self):
        """
        Print current reg values in c format
        """
        self.logger.info("Show current reg values\r\n")
        self.logger.info(">> ===== C_REGISTER_MAP ===== <<")
        # Set board registers
        self.logger.info("static const xFmDevice_t xPreset = {")
        self.logger.info(".u8LfoOn = %dU," % self.lfo_on)
        self.logger.info(".u8LfoFreq = %dU," % self.lfo_freq)
        for voice in range(YM_MAX_VOICES):
            self.logger.info(" // VOICE %d" % voice)
            self.logger.info(".xChannel[%dU].u8Algorithm = %dU," % (voice, self.channel[voice].op_algorithm))
            self.logger.info(".xChannel[%dU].u8Feedback = %dU," % (voice, self.channel[voice].feedback))
            self.logger.info(".xChannel[%dU].u8AudioOut = %dU," % (voice, self.channel[voice].audio_out))
            self.logger.info(".xChannel[%dU].u8PhaseModSens = %dU," % (voice, self.channel[voice].phase_mod_sens))
            self.logger.info(".xChannel[%dU].u8AmpModSens = %dU," % (voice, self.channel[voice].amp_mod_sens))
            for operator in range(YM_MAX_OPERATORS):
                self.logger.info(" // OPERATOR %d" % operator)
                self.logger.info(".xChannel[%dU].xOperator[%dU].u8Detune = %dU," % (voice, operator, self.channel[voice].operator[operator].detune))
                self.logger.info(".xChannel[%dU].xOperator[%dU].u8Multiple = %dU," % (voice, operator, self.channel[voice].operator[operator].multiple))
                self.logger.info(".xChannel[%dU].xOperator[%dU].u8TotalLevel = %dU," % (voice, operator, self.channel[voice].operator[operator].total_level))
                self.logger.info(".xChannel[%dU].xOperator[%dU].u8KeyScale = %dU," % (voice, operator, self.channel[voice].operator[operator].key_scale))
                self.logger.info(".xChannel[%dU].xOperator[%dU].u8AttackRate = %dU," % (voice, operator, self.channel[voice].operator[operator].attack_rate))
                self.logger.info(".xChannel[%dU].xOperator[%dU].u8AmpMod = %dU," % (voice, operator, self.channel[voice].operator[operator].amp_mod_on))
                self.logger.info(".xChannel[%dU].xOperator[%dU].u8DecayRate = %dU," % (voice, operator, self.channel[voice].operator[operator].decay_rate))
                self.logger.info(".xChannel[%dU].xOperator[%dU].u8SustainRate = %dU," % (voice, operator, self.channel[voice].operator[operator].sustain_rate))
                self.logger.info(".xChannel[%dU].xOperator[%dU].u8SustainLevel = %dU," % (voice, operator, self.channel[voice].operator[operator].sustain_level))
                self.logger.info(".xChannel[%dU].xOperator[%dU].u8ReleaseRate = %dU," % (voice, operator, self.channel[voice].operator[operator].release_rate))
                self.logger.info(".xChannel[%dU].xOperator[%dU].u8SsgEg = %dU," % (voice, operator, self.channel[voice].operator[operator].ssg_envelope))
        self.logger.info("};")

    def load_vgi_file(self, vgi_filename):
        """
        Load vgi file into class registers
        """
        self.logger.info("VGI: LOAD FILE %s" % vgi_filename)
        with open(vgi_filename, 'rb') as byte_reader:
            byte_data = byte_reader.read()
            if len(byte_data) == 43:
                byte_reader.seek(0)
                self.op_algorithm = self.__read_byte(byte_reader)
                self.feedback = self.__read_byte(byte_reader)
                reg = self.__read_byte(byte_reader)
                self.audio_out = (reg >> 6) & 0x03
                self.amp_mod_sens = (reg >> 4) & 0x03
                self.phase_mod_sens = (reg >> 0) & 0x07
                # Operator CFG
                for operator_id in range(4):
                    self.channel[0].operator[operator_id].multiple = self.__read_byte(byte_reader)
                    self.channel[0].operator[operator_id].detune = self.__read_byte(byte_reader)
                    self.channel[0].operator[operator_id].total_level = self.__read_byte(byte_reader)
                    self.channel[0].operator[operator_id].key_scale = self.__read_byte(byte_reader)
                    self.channel[0].operator[operator_id].attack_rate = self.__read_byte(byte_reader)
                    reg = self.__read_byte(byte_reader)
                    self.channel[0].operator[operator_id].amp_mod_on = (reg >> 7) & 0x01
                    self.channel[0].operator[operator_id].decay_rate = (reg >> 0) & 0x1F
                    self.channel[0].operator[operator_id].sustain_rate = self.__read_byte(byte_reader)
                    self.channel[0].operator[operator_id].release_rate = self.__read_byte(byte_reader)
                    self.channel[0].operator[operator_id].sustain_level = self.__read_byte(byte_reader)
                    self.channel[0].operator[operator_id].ssg_envelope = self.__read_byte(byte_reader)
                # Copy channel 1 in other channels
                for channel_id in range(5):
                    self.channel[channel_id + 1] = self.channel[0]
                    self.channel[channel_id + 1].channel_id = channel_id + 1
            else:
                self.logger.info("VGI: Error on file size (%d/43)" % len(byte_data))

    def midi_set_reg_values(self):
        """
        Send register values over midi interface
        """
        # Generate CMD payload
        cmd_midi = YM_SYSEX_CMD_SET_REG
        cmd_payload = []
        cmd_payload.extend(self.__get_reg_values_array())
        # Send command
        retval = self.__send_midi_cmd(cmd_midi, cmd_payload)
        return retval

    def midi_save_preset(self, preset_pos=0, preset_name=""):
        """
        Save current register conf into specified preset position
        preset_pos: preset position [0:15]
        preset_name: string of 15 characters to identify the preset
        """
        retval = False
        if preset_pos < YM_MAX_NUM_USER_PRESETS:
            # Generate CMD payload
            cmd_midi = YM_SYSEX_CMD_SAVE_PRESET
            cmd_payload = []
            # Preset pos
            cmd_payload.append(preset_pos)
            # Preset name
            format_preset_name = "{:<15}".format(preset_name)
            preset_name_bytes = format_preset_name.encode()
            for str_ch in preset_name_bytes:
                cmd_payload.append((str_ch >> 0) & 0x0F)
                cmd_payload.append((str_ch >> 4) & 0x0F)
            # Register data
            cmd_payload.extend(self.__get_reg_values_array())
            # Send command
            retval = self.__send_midi_cmd(cmd_midi, cmd_payload)
        return retval

    def midi_load_default_preset(self, preset_pos=0):
        """
        Load default const preset
        preset_pos: preset position [0:8]
        """
        retval = False
        if preset_pos < YM_MAX_NUM_DEFAULT_PRESETS:
            # Generate CMD payload
            cmd_midi = YM_SYSEX_CMD_LOAD_DEFAULT_PRESET
            cmd_payload = []
            # Preset pos
            cmd_payload.append(preset_pos)
            # Send command
            retval = self.__send_midi_cmd(cmd_midi, cmd_payload)
        return retval

    def midi_load_preset(self, preset_pos=0):
        """
        Load saved preset
        preset_pos: preset position [0:8]
        """
        retval = False
        if preset_pos < YM_MAX_NUM_USER_PRESETS:
            # Generate CMD payload
            cmd_midi = YM_SYSEX_CMD_LOAD_PRESET
            cmd_payload = []
            # Preset pos
            cmd_payload.append(preset_pos)
            # Send command
            retval = self.__send_midi_cmd(cmd_midi, cmd_payload)
        return retval

    def set_custom_preset(self):
        """
        Set preset custom preset
        """
        retval = True
        # Set board registers
        self.lfo_on = 1
        self.lfo_freq = 0
        for voice in range(6):
            self.logger.info("PRESET: Setup voice", voice)
            # Setup voice 0
            self.channel[voice].op_algorithm = 4
            self.channel[voice].feedback = 3
            self.channel[voice].audio_out = 3
            self.channel[voice].phase_mod_sens = 0
            self.channel[voice].amp_mod_sens = 2
            # Setup operator 0
            self.channel[voice].operator[0].total_level = 0x28 # 30
            self.channel[voice].operator[0].multiple = 15
            self.channel[voice].operator[0].detune = 3
            self.channel[voice].operator[0].attack_rate = 31
            self.channel[voice].operator[0].decay_rate = 4
            self.channel[voice].operator[0].sustain_level = 0
            self.channel[voice].operator[0].sustain_rate = 10
            self.channel[voice].operator[0].release_rate = 3
            self.channel[voice].operator[0].key_scale = 1
            self.channel[voice].operator[0].amp_mod_on = 1
            self.channel[voice].operator[0].ssg_envelope = 0x00 # OFF
            # Setup operator 1
            self.channel[voice].operator[1].total_level = 0x07
            self.channel[voice].operator[1].multiple = 3
            self.channel[voice].operator[1].detune = 5 # -1
            self.channel[voice].operator[1].attack_rate = 30
            self.channel[voice].operator[1].decay_rate = 8
            self.channel[voice].operator[1].sustain_level = 3
            self.channel[voice].operator[1].sustain_rate = 6
            self.channel[voice].operator[1].release_rate = 3
            self.channel[voice].operator[1].key_scale = 1
            self.channel[voice].operator[1].amp_mod_on = 0
            self.channel[voice].operator[1].ssg_envelope = 0x00 # OFF
            # Setup operator 2
            self.channel[voice].operator[2].total_level = 0x19
            self.channel[voice].operator[2].multiple = 7
            self.channel[voice].operator[2].detune = 5 # -1
            self.channel[voice].operator[2].attack_rate = 31
            self.channel[voice].operator[2].decay_rate = 4
            self.channel[voice].operator[2].sustain_level = 3
            self.channel[voice].operator[2].sustain_rate = 17
            self.channel[voice].operator[2].release_rate = 1
            self.channel[voice].operator[2].key_scale = 1
            self.channel[voice].operator[2].amp_mod_on = 0
            self.channel[voice].operator[2].ssg_envelope = 0x00 # OFF
            # Setup operator 3
            self.channel[voice].operator[3].total_level = 0x03
            self.channel[voice].operator[3].multiple = 2
            self.channel[voice].operator[3].detune = 4
            self.channel[voice].operator[3].attack_rate = 31
            self.channel[voice].operator[3].decay_rate = 5
            self.channel[voice].operator[3].sustain_level = 2
            self.channel[voice].operator[3].sustain_rate = 12
            self.channel[voice].operator[3].release_rate = 3
            self.channel[voice].operator[3].key_scale = 1
            self.channel[voice].operator[3].amp_mod_on = 0
            self.channel[voice].operator[3].ssg_envelope = 0x00 # OFF
        if retval:
            if self.midiout:
                retval = self.midi_set_reg_values()
        self.logger.info("PRESET: End")
        return retval

    class __YMChannel:
        """
        Class to handle YM2612 voice
        """
        def __init__(self, 
                    channel_id=0, 
                    feedback=0, 
                    op_algorithm=0, 
                    audio_out=3, 
                    phase_mod_sens=0, 
                    amp_mod_sens=0):
            # Channel attributes
            self.channel_id = channel_id
            self.feedback = feedback
            self.op_algorithm = op_algorithm
            self.audio_out = audio_out
            self.phase_mod_sens = phase_mod_sens
            self.amp_mod_sens = amp_mod_sens
            # Channel operators
            self.operator = {
                0: self.__YMOperator(op_id=0),
                1: self.__YMOperator(op_id=1),
                2: self.__YMOperator(op_id=2),
                3: self.__YMOperator(op_id=3),
            }

        def get_reg_LRAMSPMS(self):
            reg = ((self.audio_out & 0x03) << 6) | ((self.amp_mod_sens & 0x03) << 4) | (self.phase_mod_sens & 0x07)
            return reg

        def get_reg_FBALG(self):
            reg = ((self.feedback & 0x03) << 3) | (self.op_algorithm & 0x07)
            return reg

        class __YMOperator:
            """
            Class with operator data
            """
            def __init__(self, 
                    op_id=0,
                    detune=0, 
                    multiple=0, 
                    total_level=0, 
                    key_scale=0, 
                    attack_rate=0, 
                    amp_mod_on=0,
                    decay_rate=0,
                    sustain_rate=0,
                    sustain_level=0,
                    release_rate=0,
                    ssg_envelope=0):
                # Operator attributes
                self.detune = detune
                self.multiple = multiple
                self.total_level = total_level
                self.key_scale = key_scale
                self.attack_rate = attack_rate
                self.amp_mod_on = amp_mod_on
                self.decay_rate = decay_rate
                self.sustain_rate = sustain_rate
                self.sustain_level = sustain_level
                self.release_rate = release_rate
                self.ssg_envelope = ssg_envelope

            def get_reg_DETMUL(self):
                reg = ((self.detune << 4) & 0x70) | (self.multiple & 0x0F)
                return reg

            def get_reg_TL(self):
                reg = self.total_level & 0x7F
                return reg

            def get_reg_KSAR(self):
                reg = ((self.key_scale & 0x03) << 6) | (self.attack_rate & 0x1F)
                return reg

            def get_reg_AMDR(self):
                reg = ((self.amp_mod_on & 0x01) << 7) | (self.decay_rate & 0x1F)
                return reg

            def get_reg_SR(self):
                reg = (self.sustain_rate & 0x1F)
                return reg

            def get_reg_SLRL(self):
                reg = ((self.sustain_level & 0x0F) << 4) | (self.release_rate & 0x0F)
                return reg

            def get_reg_SSGEG(self):
                reg = self.ssg_envelope & 0x0F
                return reg

def main():
    print("\r\nYM2612: Preset TEST\r\n")
    midiOut = rtmidi.MidiOut(0)
    synth = YM2612Chip(midi_out=midiOut)
    synth.midi_load_default_preset(YM_PRESET_SAWTOOTH)

if __name__ == "__main__":
    main()
    sys.exit(0)