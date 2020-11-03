#! /usr/bin/env python3

from binascii import hexlify
import json
from os import path
import subprocess
import shlex
import base64


# This function copied from test.py :
# -----------------------------------------------------------------------------
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
# -----------------------------------------------------------------------------


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

test_vectors_dir = "trustinsoft/test_vectors/"

def test_vector_file(vector_no, name):
    return test_vectors_dir + ("%02d_%s" % (vector_no, name))

# -------------

HERE = path.dirname(__file__)
TEST_VECTORS_PATH = path.join(HERE, "..", "test_vectors", "test_vectors.json")
TEST_VECTORS = json.load(open(TEST_VECTORS_PATH))

def make_test(vector_no, case_name, args, machdep):
    print("===", str(vector_no), ":", case_name, "===")

    tis_test = {
        "name": ("Test vector %02d: %s (%s)" % (vector_no, case_name, machdep)),
        "include": "trustinsoft/common.config",
        "machdep": machdep,
        "filesystem": {
            "files": [
                {
                    "name": "tis-mkfs-stdin",
                    "from": test_vector_file(vector_no, "input")
                },
                {
                    "name": "expected",
                    "from": test_vector_file(vector_no, "expected_" + case_name)
                }
            ]
        }
    }

    if args:
        tis_test["val-args"] = ("%" + "%".join(args))

    if vector_no >= 22:
        tis_test["no-results"] = True

    print(string_of_json(tis_test))

    return tis_test

machdeps = [
    "gcc_x86_32",
    "gcc_x86_64",
    "ppc_32",
    "ppc_64",
]

def test_cases_of_test_vector(test_vector):

    # Following lines copied from test.py
    # -------------------------------------------------
    hex_key = hexlify(TEST_VECTORS["key"].encode())
    context_string = TEST_VECTORS["context_string"]
    expected_hash_xof = test_vector["hash"]
    expected_keyed_hash_xof = test_vector["keyed_hash"]
    expected_hash = expected_hash_xof[:64]
    expected_keyed_hash = expected_keyed_hash_xof[:64]
    expected_derive_key_xof = test_vector["derive_key"]
    expected_derive_key = expected_derive_key_xof[:64]
    # -------------------------------------------------

    return (
        [
            # Test the default hash.
            {
                "name": "hash",
                "expected": expected_hash,
                "args": []
            },
            # Test the extended hash.
            {
                "name": "hash_xof",
                "expected": expected_hash_xof,
                "args": ["--length", str(len(expected_hash_xof) // 2)]
            },
            # Test the default keyed hash.
            {
                "name": "keyed_hash",
                "expected": expected_keyed_hash,
                "args": ["--keyed", hex_key.decode()]
            },
            # Test the extended keyed hash.
            {
                "name": "keyed_hash_xof",
                "expected": expected_keyed_hash_xof,
                "args": ["--keyed", hex_key.decode(), "--length",
                         str(len(expected_keyed_hash_xof) // 2)]
            },
            # Test the default derive key.
            {
                "name": "derive_key",
                "expected": expected_derive_key,
                "args": ["--derive-key", context_string]
            },
            # Test the extended derive key.
            {
                "name": "derive_key_xof",
                "expected": expected_derive_key_xof,
                "args": ["--derive-key", context_string, "--length",
                         str(len(expected_derive_key_xof) // 2)]
            },
        ]
    )

def make_tis_config():
    tis_config = []
    vector_no = 0
    for test_vector in TEST_VECTORS["cases"]:
        vector_no += 1
        print("--- Test vector ", vector_no, "---")

        # Following lines copied from test.py :
        # -------------------------------------
        input_len = test_vector["input_len"]
        input = make_test_input(input_len)
        # -------------------------------------

        # Write the input file for this test vector.
        input_file = test_vector_file(vector_no, "input")
        with open(input_file, "wb") as file:
            file.write(input)

        # Treat each test case in this test vector.
        for test_case in test_cases_of_test_vector(test_vector):
            # Write the expected output file for this test case.
            expected_file = test_vector_file(vector_no, "expected_" + test_case["name"])
            with open(expected_file, "w") as file:
                file.write(test_case["expected"])
            # Generate an entry in the tis.config file.
            # (One entry for each vector * case * machdep combination.)
            for machdep in machdeps:
                tis_test = make_test(vector_no, test_case["name"], test_case["args"], machdep)
                tis_config.append(tis_test)

    return tis_config

def main():
    tis_config = make_tis_config()
    with open("tis.config", "w") as file:
        file.write(string_of_json(tis_config))

if __name__ == "__main__":
    main()
