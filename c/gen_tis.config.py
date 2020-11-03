#! /usr/bin/env python3

from binascii import hexlify
import json
from os import path
import subprocess
import shlex
import base64

# -------------

import re # Regular expressions.

# Outputting JSON.
def string_of_json(obj):
    # Output standard pretty-printed JSON (RFC 7159) with 4-space indentation.
    s = json.dumps(obj,indent=4)
    # Sometimes we need to have multiple "include" fields in the outputted JSON,
    # which is unfortunately impossible in the internal python representation
    # (OK, it is technically possible, but too cumbersome to bother implementing
    # it here), so we can name these fields 'include_', 'include__', etc, and
    # they are all converted to 'include' before outputting as JSON.
    s = re.sub(r'"include_+"', '"include"', s)
    return s

# -------------


HERE = path.dirname(__file__)
TEST_VECTORS_PATH = path.join(HERE, "..", "test_vectors", "test_vectors.json")
TEST_VECTORS = json.load(open(TEST_VECTORS_PATH))

tis_config = []

def tis_make_test(test_no, machdep, test_name, expected_name, args):
    print("===", str(test_no), ":", test_name, "===")

    tis_test = {
        "name": ("Test vector %02d: %s (%s)" % (test_no, test_name, machdep)),
        "include": "trustinsoft/common.config",
        "machdep": machdep,
        "filesystem": {
            "files": [
                {
                    "name": "tis-mkfs-stdin",
                    "from": ("trustinsoft/test_vectors/%02d_input" % test_no)
                },
                {
                    "name": "expected",
                    "from": ("trustinsoft/test_vectors/%02d_%s" % (test_no, expected_name))
                }
            ]
        }
    }

    if args:
        tis_test["val-args"] = ("%" + "%".join(args))

    if test_no >= 22:
        tis_test["no-results"] = True

    tis_config.append(tis_test)

    print(string_of_json(tis_test))



# This function copied from test.py
# ---------------------------------

# Fill the input with a repeating byte pattern. We use a cycle length of 251,
# because that's the largets prime number less than 256. This makes it unlikely
# to swapping any two adjacent input blocks or chunks will give the same
# answer.
def make_test_input(length):
    i = 0
    buf = bytearray()
    while len(buf) < length:
        buf.append(i)
        i = (i + 1) % 251
    return buf

# ---------------------------------

def write_test_vector_file(test_no, name, content):
    print("-<", name, ">-")
    file_path = "trustinsoft/test_vectors/%02d_%s" % (test_no, name)
    with open(file_path, "w") as file:
        file.write(content)

def write_test_vector_file_binary(test_no, name, content):
    print("-<", name, ">-")
    file_path = "trustinsoft/test_vectors/%02d_%s" % (test_no, name)
    with open(file_path, "wb") as file:
        file.write(content)

def main():
    test_no = 0
    machdeps = ["gcc_x86_32", "gcc_x86_64", "ppc_32", "ppc_64"]
    for case in TEST_VECTORS["cases"]:

        test_no += 1
        print("--- Test case", test_no, "---")

        # Following lines copied from test.py
        # -----------------------------------
        input_len = case["input_len"]
        input = make_test_input(input_len)
        key = TEST_VECTORS["key"]
        hex_key = hexlify(TEST_VECTORS["key"].encode())
        context_string = TEST_VECTORS["context_string"]
        expected_hash_xof = case["hash"]
        expected_hash = expected_hash_xof[:64]
        expected_keyed_hash_xof = case["keyed_hash"]
        expected_keyed_hash = expected_keyed_hash_xof[:64]
        expected_derive_key_xof = case["derive_key"]
        expected_derive_key = expected_derive_key_xof[:64]
        # -----------------------------------

        write_test_vector_file_binary(test_no, "input", input)

        # Test the default hash.
        write_test_vector_file(test_no, "expected_hash", expected_hash)
        for machdep in machdeps:
            tis_make_test(test_no,
                          machdep,
                          "test_hash",
                          "expected_hash",
                          [])

        # Test the extended hash.
        write_test_vector_file(test_no, "expected_hash_xof", expected_hash_xof)
        xof_len = len(expected_hash_xof) // 2
        for machdep in machdeps:
            tis_make_test(test_no,
                          machdep,
                          "test_hash_xof",
                          "expected_hash_xof",
                          ["--length", str(xof_len)])

        # Test the default keyed hash.
        write_test_vector_file(test_no, "expected_keyed_hash", expected_keyed_hash)
        for machdep in machdeps:
            tis_make_test(test_no,
                          machdep,
                          "test_keyed_hash",
                          "expected_keyed_hash",
                          ["--keyed", hex_key.decode()])

        # Test the extended keyed hash.
        write_test_vector_file(test_no, "expected_keyed_hash_xof", expected_keyed_hash_xof)
        xof_len = len(expected_keyed_hash_xof) // 2
        for machdep in machdeps:
            tis_make_test(test_no,
                          machdep,
                          "test_keyed_hash_xof",
                          "expected_keyed_hash_xof",
                          ["--keyed", hex_key.decode(), "--length", str(xof_len)])

        # Test the default derive key.
        write_test_vector_file(test_no, "expected_derive_key", expected_derive_key)
        for machdep in machdeps:
            tis_make_test(test_no,
                          machdep,
                          "test_derive_key",
                          "expected_derive_key",
                          ["--derive-key", context_string])

        # Test the extended derive key.
        write_test_vector_file(test_no, "expected_derive_key_xof", expected_derive_key_xof)
        xof_len = len(expected_derive_key_xof) // 2
        for machdep in machdeps:
            tis_make_test(test_no,
                          machdep,
                          "test_derive_key_xof",
                          "expected_derive_key_xof",
                          ["--derive-key", context_string, "--length", str(xof_len)])

    with open('tis.config', 'w') as f:
        f.write(string_of_json(tis_config))


if __name__ == "__main__":
    main()
