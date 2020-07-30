#!/usr/bin/env python3

"""
Megadriver control app

GUI interface to control synth parameters over MIDI of synth MEGADRIVER

Author: Sebastian Del Moral
Mail: sebmorgal@gmail.com
"""

import tkinter as tk
from tkinter import ttk 
from tkinter import filedialog
import logging
import struct
import rtmidi
import YM2612


# ComboBox reference values
voiceOutValues = {
    "R+L": 0x03,
    "R": 0x01,
    "L": 0x02,
    "OFF": 0x00
}

SSGEGValues = {
    "OFF": 0x00,
    "ADSR ADSR ADSR": 0x08,
    "ADSR OFF": 0x09,
    "ADSR RSDA ADSR": 0x0A,
    "ADSR ON": 0x0B,
    "RSDA RSDA RSDA": 0x0C,
    "RSDA ON": 0x0D,
    "RSDA ADSR RSDA": 0x0E,
    "RSDA OFF": 0x0F
}


class MegadriverApp(tk.Frame):

    def __init__(self, master):
        self.master = master
        tk.Frame.__init__(self, self.master)
        self.initLogger()
        self.initMaster()
        self.initUI()


    def initMaster(self):
        self.master.resizable(False, False)
        self.master.iconbitmap("megadriver.ico") 
        self.master.title("MEGADRIVER")


    def initLogger(self):

        self.log = logging.getLogger('megaGui')
        self.log.setLevel(logging.DEBUG)

        logFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        logHandler = logging.StreamHandler()
        logHandler.setLevel(logging.DEBUG)
        logHandler.setFormatter(logFormatter)

        self.log.addHandler(logHandler)


    def initUI(self):
        # Set main frame theme
        self.pack(fill=tk.BOTH, expand=True)

        # Fm chip handler
        self.FmChip = YM2612.YM2612Chip()

        # Midi interface handler
        self.midiHandler = rtmidi.MidiOut()
        
        # Midi options elements
        midiPortLbl = ttk.Label(self, text='MIDI')
        midiPortLbl.grid(row=0, column=0, padx=5, pady=5)

        # Midi options combobox
        self.varMidiCombo = tk.StringVar()
        midiPortCombo = ttk.Combobox(self, textvariable=self.varMidiCombo, width=20)
        midiPortCombo['values'] = self.midiHandler.get_ports()
        midiPortCombo.bind("<<ComboboxSelected>>", self.selectMidiPortCombo)
        midiPortCombo.current(0)
        midiPortCombo.config(state="readonly")
        midiPortCombo.grid(row=0, column=1, padx=5, pady=5)

        # Use first combo selection as actual midi port
        self.midiHandler.open_port(midiPortCombo.current())
        self.FmChip.midiout = self.midiHandler

        # Preset options
        presetSelLbl = ttk.Label(self, text='PRESET')
        presetSelLbl.grid(row=0, column=2, padx=5, pady=5)

        # Preset combobox
        self.varPresetCombo = tk.StringVar()
        presetSelCombo = ttk.Combobox(self, textvariable=self.varPresetCombo, width=10)
        slotList = list()
        slotList.append('Live')
        for slot in range(YM2612.YM_MAX_NUM_USER_PRESETS):
            slotList.append(slot)
        presetSelCombo['values'] = slotList
        presetSelCombo.current(0)
        presetSelCombo.config(state="readonly")
        presetSelCombo.grid(row=0, column=3, padx=5, pady=5)

        # Load button
        UpdateButton = tk.Button(self, text ="LOAD", command = self.loadPreset, width=10)
        UpdateButton.grid(row=0, column=4, padx=5, pady=5)

        # Save button
        UpdateButton = tk.Button(self, text ="SAVE", command = self.savePreset, width=10)
        UpdateButton.grid(row=0, column=5, padx=5, pady=5)

        # Exit button
        UpdateButton = tk.Button(self, text ="EXIT", command = self.onExit, width=10)
        UpdateButton.grid(row=0, column=6, padx=5, pady=5)

        # LFO elements
        lfoLbl = ttk.Label(self, text='LFO')
        lfoLbl.grid(row=1, column=0, padx=5, pady=5)

        # LFOon checkbox
        self.varLfoOn = tk.BooleanVar()
        lfoEnCheckButton = ttk.Checkbutton(self, variable=self.varLfoOn, command=self.updateLfoOn)
        lfoEnCheckButton.grid(row=1, column=1, padx=5, pady=5)

        #LFOrate scale
        self.varLfoRate = tk.IntVar()
        lfoRateScale = ttk.Scale(self, from_=0, to=7, variable=self.varLfoRate)
        lfoRateScale.bind("<ButtonRelease-1>", lambda x : self.updateParameterEvent(x))
        lfoRateScale.bind("<B1-Motion>", self.updateStatus)
        lfoRateScale.grid(row=1, column=2, padx=5, pady=5)

        # VoiceAll label
        lfoLbl = ttk.Label(self, text='VOICE ALL')
        lfoLbl.grid(row=1, column=3, padx=5, pady=5)

        # VoiceAll checkbox
        self.varVoiceAll = tk.BooleanVar()
        lfoEnCheckButton = ttk.Checkbutton(self, variable=self.varVoiceAll)
        lfoEnCheckButton.grid(row=1, column=4, padx=5, pady=5)

        # LiveUpdate label
        LiveUpdateLbl = ttk.Label(self, text='LIVE UPDATE')
        LiveUpdateLbl.grid(row=1, column=5, padx=5, pady=5)

        # LiveUpdate checkbox
        self.varLiveUpdate = tk.BooleanVar()
        LiveUpdateCheckBox = ttk.Checkbutton(self, variable=self.varLiveUpdate)
        LiveUpdateCheckBox.grid(row=1, column=6, padx=5, pady=5)

        # Voice tab list
        self.tabVoiceList = ttk.Notebook(self)
        tabVociceFrameList = []
        for voiceId in range(YM2612.YM_MAX_VOICES):
            voiceFrame = ttk.Frame(self.tabVoiceList)
            voiceFrame.grid(row=3, column=0, rowspan=2, columnspan=8, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
            tabVociceFrameList.append(voiceFrame)
            self.tabVoiceList.add(voiceFrame, text = 'Voice %d' % (voiceId))
        self.tabVoiceList.grid(row=2, column=0, rowspan=13, columnspan=8, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)

        # Var creation
        self.varVoiceFeedback = []
        self.varVoiceAlgorithm = []
        self.varVoiceOut = []
        self.varVoiceAMS = []
        self.varVoicePMS = []
        self.varOperatorDetune = []
        self.varOperatorMultiple = []
        self.varOperatorKeyScale = []
        self.varOperatorAmpMod = []
        self.varOperatorSSGEG = []
        self.varOperatorTotalLevel = []
        self.varOperatorAttackRate = []
        self.varOperatorSustainLevel = []
        self.varOperatorSustainRate = []
        self.varOperatorDecayRate = []
        self.varOperatorReleaseRate = []

        # Widget list
        self.comboVoiceOut = []
        self.comboOperatorSSGEG = []
        self.frameVoiceParameter = []
        self.frameOperatorParameter = []

        # Loop to initiate voice menu
        for voiceId in range(YM2612.YM_MAX_VOICES):
            # Get frame to use
            voiceFrame = tabVociceFrameList[voiceId]

            # Create Frame for voice parameters
            labelFrame = ttk.LabelFrame(voiceFrame, text="Voice")
            labelFrame.grid(row=0, column=0, rowspan=2, columnspan=8, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
            self.frameVoiceParameter.append(labelFrame)

            # Feedback control
            voiceFeedbackLbl = ttk.Label(labelFrame, text='FEEDBACK')
            voiceFeedbackLbl.grid(row=0, column=0, padx=5, pady=5)

            # Feedback control scale
            self.varVoiceFeedback.append(tk.IntVar())
            voiceFeedbackScale = ttk.Scale( labelFrame, from_=0, to=7, variable=self.varVoiceFeedback[voiceId])
            voiceFeedbackScale.bind("<ButtonRelease-1>", lambda x, y=self.varVoiceFeedback: self.updateParameterEventVoice(x, y))
            voiceFeedbackScale.bind("<B1-Motion>", self.updateStatus)
            voiceFeedbackScale.grid(row=0, column=1, padx=5, pady=5)

            # Algorithm control
            voiceAlgorithmLbl = ttk.Label(labelFrame, text='ALGORITHM')
            voiceAlgorithmLbl.grid(row=0, column=2, padx=5, pady=5)

            # Algorithm control scale
            self.varVoiceAlgorithm.append(tk.IntVar())
            voiceAlgorithmScale = ttk.Scale(labelFrame, from_=0, to=7, variable=self.varVoiceAlgorithm[voiceId])
            voiceAlgorithmScale.bind("<ButtonRelease-1>", lambda x, y=self.varVoiceAlgorithm: self.updateParameterEventVoice(x, y))
            voiceAlgorithmScale.bind("<B1-Motion>", self.updateStatus)
            voiceAlgorithmScale.grid(row=0, column=3, padx=5, pady=5)

            # Output
            voiceAlgorithmLbl = ttk.Label(labelFrame, text='OUT')
            voiceAlgorithmLbl.grid(row=0, column=4, padx=5, pady=5)

            # Output combobox
            self.varVoiceOut.append(tk.StringVar())
            voiceOutCombo = ttk.Combobox(labelFrame, textvariable=self.varVoiceOut[voiceId], width=10)
            voiceOutCombo['values'] = list(voiceOutValues.keys())
            voiceOutCombo.bind("<<ComboboxSelected>>", lambda x, y=self.varVoiceOut: self.updateParameterEventVoice(x, y))
            voiceOutCombo.current(0)
            voiceOutCombo.config(state="readonly")
            voiceOutCombo.grid(row=0, column=5, padx=5, pady=5)
            self.comboVoiceOut.append(voiceOutCombo)

            # Amplitude Modulation Sens
            voiceAMSLbl = ttk.Label(labelFrame, text='AMS')
            voiceAMSLbl.grid(row=1, column=0, padx=5, pady=5)

            # Amplitude Modulation scale
            self.varVoiceAMS.append(tk.IntVar())
            voiceAMSScale = ttk.Scale(labelFrame, from_=0, to=3, variable=self.varVoiceAMS[voiceId])
            voiceAMSScale.bind("<ButtonRelease-1>", lambda x, y=self.varVoiceAMS: self.updateParameterEventVoice(x, y))
            voiceAMSScale.bind("<B1-Motion>", self.updateStatus)
            voiceAMSScale.grid(row=1, column=1, padx=5, pady=5)

            # Phase Modulation Sens
            voicePMSLbl = ttk.Label(labelFrame, text='PMS')
            voicePMSLbl.grid(row=1, column=2, padx=5, pady=5)

            # Phase Modulation Sens scale
            self.varVoicePMS.append(tk.IntVar())
            voicePMSScale = ttk.Scale(labelFrame, from_=0, to=7, variable=self.varVoicePMS[voiceId])
            voicePMSScale.bind("<ButtonRelease-1>", lambda x, y=self.varVoicePMS: self.updateParameterEventVoice(x, y))
            voicePMSScale.bind("<B1-Motion>", self.updateStatus)
            voicePMSScale.grid(row=1, column=3, padx=5, pady=5)

            # Operator var init
            self.varOperatorDetune.append(list())
            self.varOperatorMultiple.append(list())
            self.varOperatorKeyScale.append(list())
            self.varOperatorAmpMod.append(list())
            self.varOperatorSSGEG.append(list())
            self.varOperatorTotalLevel.append(list())
            self.varOperatorAttackRate.append(list())
            self.varOperatorSustainRate.append(list())
            self.varOperatorSustainLevel.append(list())
            self.varOperatorDecayRate.append(list())
            self.varOperatorReleaseRate.append(list())

            # Widget init
            self.comboOperatorSSGEG.append(list())
            self.frameOperatorParameter.append(list())

            # Loop to init operators
            for operatorId in range(YM2612.YM_MAX_OPERATORS):
                # Container widget
                labelFrame = ttk.LabelFrame(voiceFrame, text="Operator %d" % operatorId)
                labelFrame.grid(row=2, column=operatorId * 2, rowspan=11, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
                self.frameOperatorParameter[voiceId].append(labelFrame)

                # Operator detune
                operatorDetuneLbl = ttk.Label(labelFrame, text='DETUNE')
                operatorDetuneLbl.grid(row=0, column=0, padx=5, pady=5)

                # Operator detune scale
                self.varOperatorDetune[voiceId].append(tk.IntVar())
                operatorDetuneScale = ttk.Scale(labelFrame, from_=0, to=7, variable=self.varOperatorDetune[voiceId][operatorId])
                operatorDetuneScale.bind("<ButtonRelease-1>", lambda x, y=self.varOperatorDetune, z=operatorId: self.updateParameterEventOperator(x, y, z))
                operatorDetuneScale.bind("<B1-Motion>", self.updateStatus)
                operatorDetuneScale.grid(row=0, column=1, padx=5, pady=5)

                # Operator multiple
                operatorMultipleLbl = ttk.Label(labelFrame, text='MULTIPLE')
                operatorMultipleLbl.grid(row=1, column=0, padx=5, pady=5)

                # Operator multiple scale
                self.varOperatorMultiple[voiceId].append(tk.IntVar())
                operatorMultipleScale = ttk.Scale(labelFrame, from_=0, to=15, variable=self.varOperatorMultiple[voiceId][operatorId])
                operatorMultipleScale.bind("<ButtonRelease-1>", lambda x, y=self.varOperatorMultiple, z=operatorId: self.updateParameterEventOperator(x, y, z))
                operatorMultipleScale.bind("<B1-Motion>", self.updateStatus)
                operatorMultipleScale.grid(row=1, column=1, padx=5, pady=5)

                # Operator Key
                operatorKeyScaleLbl = ttk.Label(labelFrame, text='KEY SCALE')
                operatorKeyScaleLbl.grid(row=2, column=0, padx=5, pady=5)

                # Operator Key Scale
                self.varOperatorKeyScale[voiceId].append(tk.IntVar())
                operatorKeyScale = ttk.Scale(labelFrame, from_=0, to=3, variable=self.varOperatorKeyScale[voiceId][operatorId])
                operatorKeyScale.bind("<ButtonRelease-1>", lambda x, y=self.varOperatorKeyScale, z=operatorId: self.updateParameterEventOperator(x, y, z))
                operatorKeyScale.bind("<B1-Motion>", self.updateStatus)
                operatorKeyScale.grid(row=2, column=1, padx=5, pady=5)

                # Operator Amplitude Modulation
                operatorKeyScaleLbl = ttk.Label(labelFrame, text='AMP MOD')
                operatorKeyScaleLbl.grid(row=3, column=0, padx=5, pady=5)

                # Operator Amplitude Modulation checkbox
                self.varOperatorAmpMod[voiceId].append(tk.BooleanVar())
                operatorAmpModCheckBox = ttk.Checkbutton(labelFrame, variable=self.varOperatorAmpMod[voiceId][operatorId], command=lambda x=voiceId, y=operatorId: self.updateAmpMod(x, y))
                operatorAmpModCheckBox.grid(row=3, column=1, padx=5, pady=5)

                # Operator SSG-EG
                operatorSSGEGLbl = ttk.Label(labelFrame, text='SSG-EG')
                operatorSSGEGLbl.grid(row=4, column=0, padx=5, pady=5)

                # Operator SSG-EG combo
                self.varOperatorSSGEG[voiceId].append(tk.StringVar())
                operatorSSEGCombo = ttk.Combobox(labelFrame, textvariable=self.varOperatorSSGEG[voiceId][operatorId], width=15)
                operatorSSEGCombo.bind("<<ComboboxSelected>>", lambda x, y=self.varOperatorSSGEG, z=operatorId: self.updateParameterEventOperator(x, y, z))
                operatorSSEGCombo['values'] = list(SSGEGValues.keys())
                operatorSSEGCombo.current(0)
                operatorSSEGCombo.config(state="readonly")
                operatorSSEGCombo.grid(row=4, column=1, padx=5, pady=5)
                self.comboOperatorSSGEG[voiceId].append(operatorSSEGCombo)

                # Operator Total level
                operatorTotalLevelLbl = ttk.Label(labelFrame, text='TOTAL LEVEL')
                operatorTotalLevelLbl.grid(row=5, column=0, padx=5, pady=5)

                # Operator Total level scale
                self.varOperatorTotalLevel[voiceId].append(tk.IntVar())
                operatorTotalLevelScale = ttk.Scale(labelFrame, from_=0, to=127, variable=self.varOperatorTotalLevel[voiceId][operatorId])
                operatorTotalLevelScale.bind("<ButtonRelease-1>", lambda x, y=self.varOperatorTotalLevel, z=operatorId: self.updateParameterEventOperator(x, y, z))
                operatorTotalLevelScale.bind("<B1-Motion>", self.updateStatus)
                operatorTotalLevelScale.grid(row=5, column=1, padx=5, pady=5)

                # Operator Attack Rate
                operatorAttackRateLbl = ttk.Label(labelFrame, text='ATTACK RATE')
                operatorAttackRateLbl.grid(row=6, column=0, padx=5, pady=5)

                # Operator Attack Rate scale
                self.varOperatorAttackRate[voiceId].append(tk.IntVar())
                operatorAttackRateScale = ttk.Scale(labelFrame, from_=0, to=31, variable=self.varOperatorAttackRate[voiceId][operatorId])
                operatorAttackRateScale.bind("<ButtonRelease-1>", lambda x, y=self.varOperatorAttackRate, z=operatorId: self.updateParameterEventOperator(x, y, z))
                operatorAttackRateScale.bind("<B1-Motion>", self.updateStatus)
                operatorAttackRateScale.grid(row=6, column=1, padx=5, pady=5)

                # Operator Sustain Level
                operatorSustainLevelLbl = ttk.Label(labelFrame, text='SUSTAIN LEVEL')
                operatorSustainLevelLbl.grid(row=7, column=0, padx=5, pady=5)

                # Operator Sustain Level scale
                self.varOperatorSustainLevel[voiceId].append(tk.IntVar())
                operatorSustainLevelScale = ttk.Scale(labelFrame, from_=0, to=15, variable=self.varOperatorSustainLevel[voiceId][operatorId])
                operatorSustainLevelScale.bind("<ButtonRelease-1>", lambda x, y=self.varOperatorSustainLevel, z=operatorId: self.updateParameterEventOperator(x, y, z))
                operatorSustainLevelScale.bind("<B1-Motion>", self.updateStatus)
                operatorSustainLevelScale.grid(row=7, column=1, padx=5, pady=5)

                # Operator Sustain Rate
                operatorSustainRateLbl = ttk.Label(labelFrame, text='SUSTAIN RATE')
                operatorSustainRateLbl.grid(row=8, column=0, padx=5, pady=5)

                # Operator Sustain Rate scale
                self.varOperatorSustainRate[voiceId].append(tk.IntVar())
                operatorSustainRateScale = ttk.Scale(labelFrame, from_=0, to=31, variable=self.varOperatorSustainRate[voiceId][operatorId])
                operatorSustainRateScale.bind("<ButtonRelease-1>", lambda x, y=self.varOperatorSustainRate, z=operatorId: self.updateParameterEventOperator(x, y, z))
                operatorSustainRateScale.bind("<B1-Motion>", self.updateStatus)
                operatorSustainRateScale.grid(row=8, column=1, padx=5, pady=5)

                # Operator Decay Rate
                operatorDecayRateLbl = ttk.Label(labelFrame, text='DECAY RATE')
                operatorDecayRateLbl.grid(row=9, column=0, padx=5, pady=5)

                # Operator Decay Rate scale
                self.varOperatorDecayRate[voiceId].append(tk.IntVar())
                operatorDecayRateScale = ttk.Scale(labelFrame, from_=0, to=31, variable=self.varOperatorDecayRate[voiceId][operatorId])
                operatorDecayRateScale.bind("<ButtonRelease-1>", lambda x, y=self.varOperatorDecayRate, z=operatorId: self.updateParameterEventOperator(x, y, z))
                operatorDecayRateScale.bind("<B1-Motion>", self.updateStatus)
                operatorDecayRateScale.grid(row=9, column=1, padx=5, pady=5)

                # Operator Release Rate
                operatorReleaseRateLbl = ttk.Label(labelFrame, text='RELEASE RATE')
                operatorReleaseRateLbl.grid(row=10, column=0, padx=5, pady=5)

                # Operator Release Rate
                self.varOperatorReleaseRate[voiceId].append(tk.IntVar())
                operatorReleaseRateScale = ttk.Scale(labelFrame, from_=0, to=15, variable=self.varOperatorReleaseRate[voiceId][operatorId])
                operatorReleaseRateScale.bind("<ButtonRelease-1>", lambda x, y=self.varOperatorReleaseRate, z=operatorId: self.updateParameterEventOperator(x, y, z))
                operatorReleaseRateScale.bind("<B1-Motion>", self.updateStatus)
                operatorReleaseRateScale.grid(row=10, column=1, padx=5, pady=5)


        # Status
        statusLbl = ttk.Label(self, text='VALUE')
        statusLbl.grid(row=15, column=0, padx=5, pady=5)

        # Status stringvar
        self.varStatus = tk.StringVar()
        statusVarLbl = ttk.Label(self, textvariable=self.varStatus)
        statusVarLbl.grid(row=15, column=1, padx=5, pady=5)
        self.varStatus.set("---")

        # Update button
        UpdateButton = tk.Button(self, text ="UPDATE", command = self.sendCommand, width=10)
        UpdateButton.grid(row=15, column=6, padx=5, pady=5)

        self.log.info('INIT')


    def updateLfoOn(self):
        varValue = self.varLfoOn.get()
        self.log.info('LfoOn: Value %d' % (varValue))
        if self.varLiveUpdate.get():
            self.sendCommand()


    def updateAmpMod(self, voiceId, operatorId):
        varValue = self.varOperatorAmpMod[voiceId][operatorId].get()
        self.log.info('AmpMod: Voice %d Operator %d Value %d' % (voiceId, operatorId, varValue))
        if self.varVoiceAll.get():
            for voiceId in range(YM2612.YM_MAX_VOICES):
                self.varOperatorAmpMod[voiceId][operatorId].set(varValue)
        if self.varLiveUpdate.get():
            self.sendCommand()


    def updateParameterEventVoice(self, event, varList):
        eventVar = event.widget.get()
        self.log.info('Parameter Update %s' % (str(eventVar)))
        self.updateStatus(event)
        if self.varVoiceAll.get():
            for voiceVar in varList:
                voiceVar.set(eventVar)
        if self.varLiveUpdate.get():
            self.sendCommand()


    def updateParameterEventOperator(self, event, varList, operatorId):
        eventVar = event.widget.get()
        self.log.info('Parameter Update %s' % (str(eventVar)))
        self.updateStatus(event)
        if self.varVoiceAll.get():
            for voiceVar in varList:
                voiceVar[operatorId].set(eventVar)
        if self.varLiveUpdate.get():
            self.sendCommand()


    def updateParameterEvent(self, event):
        eventVar = event.widget.get()
        self.updateStatus(event)
        self.log.info('Parameter Update %s' % (str(eventVar)))
        if self.varLiveUpdate.get():
                self.sendCommand()


    def updateStatus(self, eventData):
        varData = eventData.widget.get()
        if type(varData) is float:
            self.varStatus.set("%d" % (int(varData)))


    def sendCommand(self):
        self.log.info('Send Command')
        presetSlot = self.varPresetCombo.get()
        self.syncDriver()
        if presetSlot == 'Live':
            self.log.info('Live Update')
            self.FmChip.midi_set_reg_values()
        else:
            presetVar = int(presetSlot)
            self.log.info('Update slot %d' % (presetVar))
            self.FmChip.midi_save_preset(presetVar, "PRESET %d" % presetVar)
            self.FmChip.midi_load_preset(presetVar)


    def selectMidiPortCombo(self, event):
        midiPortId = event.widget.current()
        self.log.info('Open Midi port %s' % (midiPortId))
        self.midiHandler.close_port()
        self.midiHandler.open_port(midiPortId)
        self.FmChip.midiout = self.midiHandler


    def loadPreset(self):
        self.log.info('Load preset')
        filename = filedialog.askopenfilename(initialdir = "./vgi", 
                                            title = "Select file",
                                            filetypes = (("vgi files","*.vgi"), ("all files","*.*")))
        if filename != '':
            self.log.info(filename)
            for voice in range(YM2612.YM_MAX_VOICES):
                self.loadVgiFile(filename, voice)
        if self.varLiveUpdate.get():
            self.sendCommand()


    def readByte(self, fileHandler):
        return struct.unpack('B', fileHandler.read(1))[0]


    def writeByte(self, byte):
        return struct.pack('B', byte)


    def loadVgiFile(self, vgiFilename, voiceId):
        with open(vgiFilename, 'rb') as byte_reader:
            byte_data = byte_reader.read()
            if len(byte_data) == 43:
                byte_reader.seek(0)
                # Read voice parameters
                self.varVoiceAlgorithm[voiceId].set(self.readByte(byte_reader))
                self.varVoiceFeedback[voiceId].set(self.readByte(byte_reader))
                reg = self.readByte(byte_reader)
                self.comboVoiceOut[voiceId].current((reg >> 6) & 0x03)
                self.varVoiceAMS[voiceId].set((reg >> 4) & 0x03)
                self.varVoicePMS[voiceId].set((reg >> 0) & 0x07)
                # Read operator parameters
                for operator_id in range(YM2612.YM_MAX_OPERATORS):
                    self.varOperatorMultiple[voiceId][operator_id].set(self.readByte(byte_reader))
                    self.varOperatorDetune[voiceId][operator_id].set(self.readByte(byte_reader))
                    self.varOperatorTotalLevel[voiceId][operator_id].set(self.readByte(byte_reader))
                    self.varOperatorKeyScale[voiceId][operator_id].set(self.readByte(byte_reader))
                    self.varOperatorAttackRate[voiceId][operator_id].set(self.readByte(byte_reader))
                    reg = self.readByte(byte_reader)
                    self.varOperatorAmpMod[voiceId][operator_id].set((reg >> 7) & 0x01)
                    self.varOperatorDecayRate[voiceId][operator_id].set((reg >> 0) & 0x1F)
                    self.varOperatorSustainRate[voiceId][operator_id].set(self.readByte(byte_reader))
                    self.varOperatorReleaseRate[voiceId][operator_id].set(self.readByte(byte_reader))
                    self.varOperatorSustainLevel[voiceId][operator_id].set(self.readByte(byte_reader))
                    reg = self.readByte(byte_reader)
                    self.comboOperatorSSGEG[voiceId][operator_id].current(reg & 0x07)
            else:
                self.log.info("VGI: Error on file size (%d/43)" % len(byte_data))


    def saveVgiFile(self, vgiFilename, voiceId):
        with open(vgiFilename, 'wb') as byte_writer:
            byte_writer.seek(0)
            # Write voice parameters
            byte_writer.write(self.writeByte(self.varVoiceAlgorithm[voiceId].get()))
            byte_writer.write(self.writeByte(self.varVoiceFeedback[voiceId].get()))
            regVar = (voiceOutValues.get(self.comboVoiceOut[voiceId].get())) << 6
            regVar |= self.varVoiceAMS[voiceId].get() << 4
            regVar |= self.varVoicePMS[voiceId].get() << 0
            byte_writer.write(self.writeByte(regVar))
            # Write operator parameters
            for operator_id in range(YM2612.YM_MAX_OPERATORS):
                byte_writer.write(self.writeByte(self.varOperatorMultiple[voiceId][operator_id].get()))
                byte_writer.write(self.writeByte(self.varOperatorDetune[voiceId][operator_id].get()))
                byte_writer.write(self.writeByte(self.varOperatorTotalLevel[voiceId][operator_id].get()))
                byte_writer.write(self.writeByte(self.varOperatorKeyScale[voiceId][operator_id].get()))
                byte_writer.write(self.writeByte(self.varOperatorAttackRate[voiceId][operator_id].get()))
                regVar = self.varOperatorAmpMod[voiceId][operator_id].get() << 7
                regVar |= self.varOperatorDecayRate[voiceId][operator_id].get()
                byte_writer.write(self.writeByte(regVar))
                byte_writer.write(self.writeByte(self.varOperatorSustainRate[voiceId][operator_id].get()))
                byte_writer.write(self.writeByte(self.varOperatorReleaseRate[voiceId][operator_id].get()))
                byte_writer.write(self.writeByte(self.varOperatorSustainLevel[voiceId][operator_id].get()))
                regVar = SSGEGValues.get(self.comboOperatorSSGEG[voiceId][operator_id].get())
                byte_writer.write(self.writeByte(regVar))
            self.log.info("Saved %d bytes" % byte_writer.tell())


    def syncDriver(self):
        self.log.info('Sync driver')
        self.FmChip.lfo_on = int(self.varLfoRate.get())
        self.FmChip.lfo_freq = int(self.varLfoRate.get())
        for voiceId in range(YM2612.YM_MAX_VOICES):
            self.FmChip.channel[voiceId].op_algorithm = int(self.varVoiceAlgorithm[voiceId].get())
            self.FmChip.channel[voiceId].feedback = int(self.varVoiceFeedback[voiceId].get())
            self.FmChip.channel[voiceId].audio_out = voiceOutValues.get(self.comboVoiceOut[voiceId].get())
            self.FmChip.channel[voiceId].phase_mod_sens = int(self.varVoicePMS[voiceId].get())
            self.FmChip.channel[voiceId].amp_mod_sens = int(self.varVoiceAMS[voiceId].get())
            for operatorId in range(YM2612.YM_MAX_OPERATORS):
                self.FmChip.channel[voiceId].operator[operatorId].detune = int(self.varOperatorDetune[voiceId][operatorId].get())
                self.FmChip.channel[voiceId].operator[operatorId].multiple = int(self.varOperatorMultiple[voiceId][operatorId].get())
                self.FmChip.channel[voiceId].operator[operatorId].key_scale = int(self.varOperatorKeyScale[voiceId][operatorId].get())
                self.FmChip.channel[voiceId].operator[operatorId].amp_mod_on = int(self.varOperatorAmpMod[voiceId][operatorId].get())
                self.FmChip.channel[voiceId].operator[operatorId].ssg_envelope = SSGEGValues.get(self.comboOperatorSSGEG[voiceId][operatorId].get())
                self.FmChip.channel[voiceId].operator[operatorId].total_level = int(self.varOperatorTotalLevel[voiceId][operatorId].get())
                self.FmChip.channel[voiceId].operator[operatorId].attack_rate = int(self.varOperatorAttackRate[voiceId][operatorId].get())
                self.FmChip.channel[voiceId].operator[operatorId].sustain_level = int(self.varOperatorSustainLevel[voiceId][operatorId].get())
                self.FmChip.channel[voiceId].operator[operatorId].sustain_rate = int(self.varOperatorSustainRate[voiceId][operatorId].get())
                self.FmChip.channel[voiceId].operator[operatorId].decay_rate = int(self.varOperatorDecayRate[voiceId][operatorId].get())
                self.FmChip.channel[voiceId].operator[operatorId].release_rate = int(self.varOperatorReleaseRate[voiceId][operatorId].get())


    def savePreset(self):
        self.log.info('Save preset')
        filename = filedialog.asksaveasfilename(initialdir = "./vgi", 
                                    title = "Select file",
                                    defaultextension='.vgi',
                                    filetypes = (("vgi files","*.vgi"), ("all files","*.*")))
        if filename != '':
            voiceId = self.tabVoiceList.index(self.tabVoiceList.select())
            self.log.info("Save voice %d into %s" % (voiceId, filename))
            self.saveVgiFile(filename,voiceId)


    def onExit(self):
        self.log.info('EXIT')
        self.quit()


if __name__ == '__main__':
    root = tk.Tk()
    mainApp = MegadriverApp(root)
    root.mainloop()
