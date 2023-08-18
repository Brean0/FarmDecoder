# FarmDecoder
Decodes farm functions into readable functions. Supports advancedPipe()

Hosted on https://farmdecoder.streamlit.app/, or follow the steps outlined below for the CLI version: 

# Setup
## create an venv: 

```
python3 -m pip install venv (if not installed)
cd FarmDecoder
python3 -m venv env
```

## activate venv: 

windows
```
env\Scripts\activate.bat
```

linux/MacOs
```
source myvenv/bin/activate
```

## install libraries
```
pip install -r requirements.txt
```

for windows, the readline library is not supported. line 6 in `farmDecoder.py` needs to be deleted.
```
from web3 import Web3
import sys
import readline <- delete this line
...
```

run:
```
python3 FarmDecoder.py
```

you will get this prompt: 
Farm Decoder: Please input farm data. Example: "0x300dd6cf....
Simply input the farm hex data, and an decoded version will print on the terminal. 

input data can be obtained by going to the etherscan tx page, and copying the inputData, while viewing data as "original":

<img width="999" alt="image" src="https://github.com/Brean0/FarmDecoder/assets/90539204/7c204958-09e0-4e8c-aedc-d029e27889f7">

example output code:

 <img width="767" alt="image" src="https://github.com/Brean0/FarmDecoder/assets/90539204/94e6a11b-4ae0-4435-8125-3544f28d9805">
