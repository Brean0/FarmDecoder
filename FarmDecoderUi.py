import json
import os
import pickle
from web3 import Web3
import sys
import readline
import streamlit as st
import pandas as pd
import requests
import math


# global variables
data = bytes(0)
BYTES_ARRAY_INDEX = 8 + 64 + 64

# Streamlit config
st.set_page_config(
    page_title = "Farm Decoder",
    page_icon = "🌱",
    layout="wide"
)
col1, col2 = st.columns([0.4,0.6], gap ="large")

dataTypes = {
    "uint8" : 1,
    "uint16" : 2,
    "uint24" : 3,
    "uint32" : 4,
    "uint64" : 8,
    "uint128" : 16,
    "uint256" : 32,
    "int96" : 12,
    "address" : 20,
    "advancedPipeCall" : 69,
    "advancedPipe" : 420,
    "bytes": 100
}

# from beanstalk.json, generate a dictonary of selectors and their input param data types
def jsonToSelectors():
    # TODO: add specific selectors to tuple[]
    # MultiPipe
    outDict = {}   
    with open('beanstalk.json') as json_file:
        _json = json.load(json_file)
        # loop through each function
        for function in _json:
            inputsStr = ""
            inputList = []
            for i , input in enumerate(function['inputs']):
                inputList.append(input['type'])
                if(i == len(function['inputs']) - 1):
                    inputsStr = inputsStr + input['type'] 
                else:
                    inputsStr = inputsStr + input['type'] + ","
            if(function['type'] != 'function'):
                continue
            stringThing = function['name'] + "(" + inputsStr + ")"
            functionSelector = Web3.solidity_keccak(["string"],[stringThing]).hex()[:10]
            outDict[functionSelector] = {function['name']: inputList}
        outDict['0xb452c7ae'] = {'advancedPipe': ['advancedPipeCall[]','uint256']} ## advancedPipe
        outDict['0x36bfafbd'] = {'advancedFarm': ['advancedFarmCall[]','uint256']} ## advancedFarm
    with open('Well.json') as json_file: 
        _json = json.load(json_file)['abi']
        # loop through each function
        for function in _json:
            inputsStr = ""
            inputList = []
            for i , input in enumerate(function['inputs']):
                if(input == []):
                    continue
                inputList.append(input['type'])
                if(i == len(function['inputs']) - 1):
                    inputsStr = inputsStr + input['type'] 
                else:
                    inputsStr = inputsStr + input['type'] + ","
            if(function['type'] != 'function'):
                continue
            stringThing = function['name'] + "(" + inputsStr + ")"
            functionSelector = Web3.solidity_keccak(["string"],[stringThing]).hex()[:10]
            outDict[functionSelector] = {function['name']: inputList}
     # dump the outDict to a pickle file 
    with open('selectors.pickle', 'wb') as handle:
        pickle.dump(outDict, handle, protocol=pickle.HIGHEST_PROTOCOL)

# given data, index, and json, get the selector data 
def getSelectorData(index: int, beanstalkJson: dict):
    selector = '0x' + data[index:index+8].decode('utf-8')
    st.write("Function Selector: ", selector)
    function = beanstalkJson[selector]
    st.subheader("Function Selector and Name: " + selector + " , " + list(function.keys())[0])
    st.write("Function Inputs: " + str(list(function.values())[0]))
    return function

def getSelectorData2(selector: bytes):
     with open('selectors.pickle', 'rb') as handle:
        beanstalkJson = pickle.load(handle)
        try:
            function = beanstalkJson['0x' + str(selector)[2:-1]]
        except: 
            function = {'NA' : 'NA'}
        return function
    
# loops through all the inputs of a function, and prints the input type and data
def decodeHelper(index: int, beanstalkJson: dict):
    st.divider()
    function = getSelectorData(index, beanstalkJson)
    index += 8
    # loop through all entries, and print the input type and data
    # if there are no entries, it doesn't require any inputs and therfore can be skipped
    st.write("Function inputs and data:")
    if(len(list(function.values())[0]) != 0):
        startIndex = index
        for i, value in enumerate(list(function.values())[0]):

            # check if value is an array. If its an array, we need to decode it differently
            if "[]" in value:
                # remove the last two characters in value
                value = value[:-2]
                index = decodeArray(data, startIndex, index, value)
                
            elif(value == "bytes"):
                decodeBytes(data, startIndex)

            else:
                inputData = int(data[index + 64 - 2*dataTypes[value]: index + 64],16)
                if(value == "address"):
                    st.write(value + ": " + "[" +  hex(inputData) + "](" + "https://etherscan.io/address/" + hex(inputData) + ")")
                else:
                    st.write(value + ": " + str(inputData))
            index += 64
    # add the remaining n bytes to the index (4 bytes from selector, so add 28 more bytes)
    index += 56
    return index

def decodeFarm():
    st.header('Results:')
    with open('selectors.pickle', 'rb') as handle:
        beanstalkJson = pickle.load(handle)
    if(data == "0x"):
        return
    index = 0
    # get selector
    function = getSelectorData(index, beanstalkJson)
    index +=8
    # next 32 bytes represent the position of where the length of bytes[] is stored: 
    lengthPos = int(data[index:index + 64], 16)
    index += lengthPos*2
    lengthOfBytesArray = int(data[index:index + 64],16)
    index += 64
    st.write("Farm contains", str(lengthOfBytesArray), "Functions!")
    st.write("lengthOfBytesPos", lengthOfBytesPos)


    # get the lengths of each bytes element
    for i in range(lengthOfBytesArray):
        lengthOfBytesPos = int(data[BYTES_ARRAY_INDEX + i*64:BYTES_ARRAY_INDEX + (i+1)*64], 16)
        startOfLengthOfbytes = BYTES_ARRAY_INDEX + lengthOfBytesPos*2
        # function data starts 32 bytes after the length
        startOfFunction = startOfLengthOfbytes + 64
        decodeHelper(startOfFunction, beanstalkJson)

def decodeAdvancedFarm():
    st.header('Results:')
    with open('selectors.pickle', 'rb') as handle:
        beanstalkJson = pickle.load(handle)
    if(data == "0x"):
        return
    index = 0
    # get selector
    function = getSelectorData(index, beanstalkJson)
    index +=8
    # next 32 bytes represent the position of where the length of advancedFarm[] is stored: 
    lengthPos = int(data[index:index + 64], 16)
    index += lengthPos*2
    lengthOfAdvancedFarmArray = int(data[index:index + 64],16)
    index += 64
    st.write("AdvancedFarm contains", str(lengthOfAdvancedFarmArray), "Functions!")
    clipboardData = []
    # get the location of the advancedFarmCall array
    for i in range(lengthOfAdvancedFarmArray):
        # advanced farm call has 2 bytes array 
        locOfBytesPos = int(data[BYTES_ARRAY_INDEX + i*64:BYTES_ARRAY_INDEX + (i+1)*64], 16)
        # st.write("locOfBytesPos", locOfBytesPos)
        FirstBytesPos = BYTES_ARRAY_INDEX + locOfBytesPos*2
        # st.write("FirstBytesPos", FirstBytesPos)
        for j in range(2):
            # get the location of the bytes length:
            LocationBytes = int(data[FirstBytesPos + j*64:FirstBytesPos + (j+1)*64],16)
            # st.write("LocationBytes", LocationBytes)
            byteLengthLocation = FirstBytesPos + LocationBytes*2
            # st.write("byteLengthLocation", byteLengthLocation)
            lengthOfBytes = int(data[byteLengthLocation:byteLengthLocation + 64],16)
            # st.write("lengthOfBytes", lengthOfBytes)
            # st.write("------------------")
            # calldata
            if(j == 0):
                decodeHelper(byteLengthLocation + 64, beanstalkJson)
            else:
                _bytesData = data[byteLengthLocation + 64:byteLengthLocation + 64 + lengthOfBytes*2]
                clipboardData.append(_bytesData)
                decodeClipboard(_bytesData, True, clipboardData)

def decodeClipboard(_bytesData, isAdvancedFarmClipboard, clipboardData):
    if(isAdvancedFarmClipboard):
        st.subheader('AdvancedFarmClipboard:')
    else:
        st.subheader('PipelineClipboard:')
    # clipboard is decoded as such:
    # first byte determines whether to use ether.
    # second byte determines the clipboardType:
    clipboardType = int(_bytesData[0:2])
    ethFlag = int(_bytesData[2:4])
    st.write("useEthFlag:", str(bool(ethFlag)))
    st.write("clipboardType:", str(clipboardType))
    if(clipboardType == 0): 
        # type 0 means that the clipboard is not used.
        if(ethFlag == 1):
            st.write("ethAmount:", str(int(_bytesData[62:],16)))
    elif(clipboardType == 1):
        # type 1 means that only 32 bytes of data is used
        st.write("clipboardData:", str(_bytesData[4:]))
        # bytes 2 - 11 specify the returnDataIndex of the function
        st.write("returnDataIndex:", str(int(_bytesData[4:24])))
        # bytes 12 - 21 specify the copyIndex of the function
        st.write("copyIndex:", str(((int(_bytesData[26:44],16) - 32) / 32)))
        # bytes 22 - 31 specify the pasteIndex of the function
        st.write("pasteIndex:", str((int(_bytesData[47:64],16) - 36) / 32))
        # bytes 32 - 63 is the the amount of eth used (if applicable)
        if(ethFlag == 1):
            st.write("ethAmount:", str(_bytesData[62:]))
    else:
        # type 2 means n bytes are being used.
        st.write("clipboardData:", str(_bytesData[4:]))
def getSelector(selector: str):
    with open('selectors.pickle', 'rb') as handle:
        beanstalkJson = pickle.load(handle) 
    function = beanstalkJson[selector]
    print("function Selector: " + selector)
    print("function Name: " + list(function.keys())[0])
    print("function Inputs: " + str(list(function.values())[0]))
  
def twos_comp(val, bits):
    """compute the 2's complement of int value val"""
    if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)        # compute negative value
    return val                         # return positive value as is

def decodeArray(data: bytes, startIndex: int, index: int, value: str):
    # first 32 bytes determine the location of the array)
    _lengthPos = data[index :index + 64]
    lengthPos = int(_lengthPos,16)
    lengthPosIndex = startIndex + lengthPos*2
    arrayLength = int(data[lengthPosIndex:lengthPosIndex + 64],16)

    arrayOutput = []
    lengthPosIndex += 64
    pipelineClipboard = []
    for i in range(arrayLength):
        if(dataTypes[value] == 69): ## advancedPipeCall is a tuple, and needs special care
            output = decodeAdvancedPipe(data, lengthPosIndex, "advancedPipe", i, pipelineClipboard)
            # arrayOutput.append(output)
        else:
            output = int(data[lengthPosIndex + (i * 64): lengthPosIndex + ((i + 1) * 64)],16)
            if("int" in value):
                output = twos_comp(output, 256)
            if(dataTypes[value] == 20):
                arrayOutput.append(hex(output))
            else:
                arrayOutput.append(output)
    if(dataTypes[value] != 69):
        st.write(value + "[]: " + str(arrayOutput))
    return index

def decodeAdvancedPipe(data: bytes, startIndex: int, value: str, m: int, pipelineClipboard):
    advancedData = []
     # first 32 bytes determine the location of the data of the array
    _lengthData = data[startIndex + (64 * m) :startIndex + (64 * (m+1))]
    lengthData = int(_lengthData,16)

    lengthDataIndex = startIndex + lengthData*2
    addressData = data[lengthDataIndex:lengthDataIndex + 64]
    addressData = hex(int(addressData,16))
    st.subheader("Target.Address: " + "[" + str(addressData) + "](https://etherscan.io/address/" + str(addressData) + ")")
    advancedData.append(("address:" + addressData))


    for i in range(2): ## get data of (bytes, bytes)
        # first 32 bytes determine the location of the length of the bytes
        _bytesLocation = data[lengthDataIndex + (64 * (i + 1)) :lengthDataIndex + (64 * (i + 2))]
        bytesLocation = int(_bytesLocation,16)
        bytesLengthIndex = lengthDataIndex + bytesLocation*2
        _bytesLength = data[bytesLengthIndex:bytesLengthIndex + 64]
        bytesLengthIndex += 64
        bytesLength = int(_bytesLength,16)
        _bytesData = data[bytesLengthIndex:bytesLengthIndex + bytesLength*2] 
        bytesData = int(_bytesData,16)
        stuff = []
        loop = 0
        if(i == 0):
            loop = (bytesLength - 4) // 32 + 1
            for j in range(loop):
                if(j == 0):
                    function = getSelectorData2(_bytesData[0:8])

                    st.subheader("callData.Function Selector and Name: " + '0x' + str(_bytesData[0:8])[2:-1] + " , " + list(function.keys())[0])
                    st.write("callData.Function Inputs: " + str(list(function.values())[0]))                   
                    stuff.append((" Selector: " + str(hex(bytesData))[0:10]))
                else:
                    st.write(str(j) + ": " + '0x' + str(hex(bytesData)[10 + (j-1)*64:10 + j*64])[2:-1])
                    stuff.append("  data " + str(j) + ": " + '0x' + str(hex(bytesData)[10 + (j-1)*64:10 + j*64])[2:-1])
        else:
            pipelineClipboard.append(_bytesData)
            st.write(" Clipboard: " + '0x' + str(_bytesData)[2:-1])
            decodeClipboard(_bytesData, False, pipelineClipboard)
            st.write()

def decodeBytes(data: bytes, startIndex: int):
    # first 32 bytes determine the location of the length of the bytes
    bytesLocation = int(data[startIndex :startIndex + 64],16)
    bytesLengthIndex = startIndex + bytesLocation*2
    bytesLength = int(data[bytesLengthIndex:bytesLengthIndex + 64],16)
    bytesLengthIndex += 64
    _bytesData = data[bytesLengthIndex:bytesLengthIndex + bytesLength*2]
    st.write('bytes: ' +'0x' + str(_bytesData)[2:-1])

def executeDecodeFarm():
    with col1:
        st.title("FarmDecoder")
        global data
        # check that selectors.pickles exist.
        # if not, generate with jsonToSelectors
        # if you want to regenerate the selectors, delete the pickle file. 
        if(os.path.isfile('./selectors.pickle') == False):
            jsonToSelectors()
        inp = st.text_input('Please input farm data (0x300dd6cf.. or 0x36bfafbd..)')
        if(inp == ''):
            return
        elif('0x300dd6cf' not in inp and '0x36bfafbd' not in inp):
            st.write("Incorrect Input")
        else:
            if('0x300dd6cf' in inp):
                st.write('Input Data:', inp)
                data = inp[2:].encode()
                with col2:
                    decodeFarm()
                    st.balloons()
            else:
                st.write('Input Data:', inp)
                data = inp[2:].encode()
                with col2:
                    decodeAdvancedFarm()
                    st.balloons()
    st.divider()
    st.subheader("[Github](https://github.com/Brean0/FarmDecoder)")
    st.subheader("[Beanstalk](https://app.bean.money/)")


if __name__ == "__main__":
    executeDecodeFarm()