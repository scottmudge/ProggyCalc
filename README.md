# ProggyCalc

[![Build ProggyCalc](https://github.com/scottmudge/ProggyCalc/actions/workflows/python-app.yml/badge.svg)](https://github.com/scottmudge/ProggyCalc/actions/workflows/python-app.yml)

The programmer's simple, effective calculator.

## Description

Tired of using the Windows calculator to calculate hex offsets or convert values between hex and binary? Want to quickly compute the overflowed value of a sized integer? ProggyCalc is for you!

ProggyCalc is a programming and reverse-engineering focused calculator focused on ease of use. All the important features and functions have quick keybindings, making it easy to quickly compute an offset or convert hex to decimal (or binary) without needing to use the mouse.

## Screenshot

![ProggyCalc Screenshot](https://raw.githubusercontent.com/scottmudge/ProggyCalc/refs/heads/master/assets/screenshot.png)

## Key features:

* Key bindings for all important features, including copy and paste, converting between hex and binary, storing into memory register, recalling memory, and all basic arithmatic operations.
* Bit-wise operations for `AND`, `OR`, `XOR`, and left and right bit-shift.
* Simple arithmatic operations including add, subtract, multiply, and divide.
* Two main display modes: decimal and hex.
* Three "hex modes": signed (overflow at signed limits), unsigned (overflow at unsigned limits), and relative (same as decimal mode, numbers go infinitely positive or negative).
* Configurable integer size for signed and unsigned hex modes, from 8 to 128 bits.
* Configurable fonts - I like [Monaspace Krypton](https://github.com/githubnext/monaspace) for the display (same as screenshot).
* A smaller display beneath the main number display showing the alternate (hex if decimal, or visa-vera) and binary representations of the number.
* Memory register to store a value, with associated key bindings.
* Visual feedback for clear, clear everything, copy, paste, memory store, and memory restore.
* Quickly toggle and convert between hex and decimal display with the keybinding.
* A history view of previous operations.
* Cross-platform - it should work on Windows, Linux, and OSX.
* Simple, clean PyQt6 interface.

## Key-Bindings

* Numerical inputs and operators are what you'd expect.
* Bit shift left '<' and bit shift right '>'.
* Equals is 'enter'.
* Memory store is 'P'.
* Memory recall is 'R'.
* Clear entry is 'escape', clear is 'delete'.
* Clearing memory is either manually pressing the 'CE' button, or pressing escape or delete three times quickly.
* Toggling between hex and decimal is 'X'.
* Backspace works as you'd expect.

## Building

Note this requires Python 3, I'd recommend at least 3.11.

1. Clone this repository: `git clone https://github.com/scottmudge/ProggyCalc.git`
2. Navigate to the local clone: `cd ProggyCalc`
3. Create a python virtual environment environment: `python -m venv venv`
4. Activate the virtual environment: `source ./venv/bin/activate` for Linux or OSX, or `.\venv\Scripts\activate` for Windows
5. Install the requirements: `pip install -r requirements.txt`
6. For dark mode, install pyqtdarktheme (note it requires the extra option): `pip install pyqtdarktheme --ignore-requires-python`
7. Run `pyinstaller ProggyCalc.spec`
8. Wait for it to finish. The final `ProggyCalc` binary will be in `./dist/`
9. Copy it to wherever you want. It's portable.
