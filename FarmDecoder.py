import json
import os
import pickle
from web3 import Web3
import sys
import readline
# global variables
data = bytes(0)

BYTES_ARRAY_INDEX = 8 + 64 + 64

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
    function = beanstalkJson[selector]
    print("function Selector: " + selector)
    print("function Name: " + list(function.keys())[0])
    print("function Inputs: " + str(list(function.values())[0]))
    index += 8
    return function, index

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
    print("----------------------------------")
    function, index = getSelectorData(index, beanstalkJson)

    # loop through all entries, and print the input type and data
    # if there are no entries, it doesn't require any inputs and therfore can be skipped
    print("function inputs and data:")
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
                    print(value + ":" , hex(inputData))
                else:
                    print(value + ":", inputData)
            index += 64
    # add the remaining n bytes to the index (4 bytes from selector, so add 28 more bytes)
    index += 56
    return index

def decodeFarm():
    with open('selectors.pickle', 'rb') as handle:
        beanstalkJson = pickle.load(handle)
    ## index starts at 8, as the first 4 bytes of a tx data is always the farm selector
    print("----------------------------------")

    index = 0
    function, index = getSelectorData(index, beanstalkJson)

    # next 32 bytes represent the position of where the length of bytes[] is stored: 
    lengthPos = int(data[index:index + 64], 16)
    index += lengthPos*2
    lengthOfBytesArray = int(data[index:index + 64],16)
    index += 64
    print("farm has", lengthOfBytesArray, "functions")

    # get the lengths of each bytes element
    for i in range(lengthOfBytesArray):
        lengthOfBytesPos = int(data[BYTES_ARRAY_INDEX + i*64:BYTES_ARRAY_INDEX + (i+1)*64], 16)
        startOfLengthOfbytes = BYTES_ARRAY_INDEX + lengthOfBytesPos*2
        # function data starts 32 bytes after the length
        startOfFunction = startOfLengthOfbytes + 64
        decodeHelper(startOfFunction, beanstalkJson)

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
    # print("lengthPos: " + str(lengthPos))


    lengthPosIndex = startIndex + lengthPos*2
    arrayLength = data[lengthPosIndex:lengthPosIndex + 64]
    arrayLength = int(arrayLength,16)

    arrayOutput = []
    lengthPosIndex += 64
    for i in range(arrayLength):
        if(dataTypes[value] == 69): ## advancedPipeCall is a tuple, and needs special care
            output = decodeAdvancedPipe(data, lengthPosIndex, "advancedPipe", i)
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
        print(value + "[]: " + str(arrayOutput))
    return index

def decodeAdvancedPipe(data: bytes, startIndex: int, value: str, i: int):
    advancedData = []
     # first 32 bytes determine the location of the data of the array
    _lengthData = data[startIndex + (64 * i) :startIndex + (64 * (i+1))]
    lengthData = int(_lengthData,16)

    lengthDataIndex = startIndex + lengthData*2
    addressData = data[lengthDataIndex:lengthDataIndex + 64]
    addressData = hex(int(addressData,16))
    print("\n Address: " + str(addressData))
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
                    print(" Selector: " + str(_bytesData[0:8]))
                    print(" Function name: " + list(function.keys())[0])
                    print(" Function inputs: " + str(list(function.values())[0]))                    
                    stuff.append((" Selector: " + str(hex(bytesData))[0:10]))
                else:
                    print(" " + str(j) + ": " + str(_bytesData[8 + (j-1)*64:8 + (j*64)]))
                    stuff.append("  data " + str(j) + ":" + str(hex(bytesData)[10 + (j-1)*64:10 + j*64]))
        else:
            print(" Clipboard: " + str(_bytesData) + '\n')

def decodeBytes(data: bytes, startIndex: int):
    # first 32 bytes determine the location of the length of the bytes
    bytesLocation = int(data[startIndex :startIndex + 64],16)
    bytesLengthIndex = startIndex + bytesLocation*2
    bytesLength = int(data[bytesLengthIndex:bytesLengthIndex + 64],16)
    bytesLengthIndex += 64
    _bytesData = data[bytesLengthIndex:bytesLengthIndex + bytesLength*2] 
    print(_bytesData)

def executeDecodeFarm():
    global data
    # check that selectors.pickles exist.
    # if not, generate with jsonToSelectors
    # if you want to regenerate the selectors, delete the pickle file. 
    if(os.path.isfile('./selectors.pickle') == False):
        jsonToSelectors()
    inp = input('Farm Decoder: Please input farm data. Example: "0x300dd6cf....\n')
    data = inp[2:].encode()
    decodeFarm()

if __name__ == "__main__":
    executeDecodeFarm()