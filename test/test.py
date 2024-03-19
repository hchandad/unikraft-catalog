import subprocess
import socket
import requests
import errno
from enum import Enum

PORT = 2105


class Platforms(Enum):
    QEMU = "qemu"
    FIRECRACKER = "fc"
    XEN = "xen"


class Architecture(Enum):
    X86_64 = "x86_64"


# TODO: cleanup the process on all exceptions
# TODO: support the yaml spec
# TODO: support extra kraft run options ...
# TODO: add output
# TODO: add parsable output (non human)
# TODO: we can write unit tests by passing specific json objects to run
#       and checking the error sample output, requires non human output to be done

"""
# spec
# TODO: apply regex on lines or on full file ? -> on lines
[
    # ...
    # array of test_case object
    {
        "arch": "x86_64",
        "args": {
            "disable-acceleration": true,
            "rootfs": "",
            "volume": ""
        },
        "http_check": [
            # ...
            # array of http_check object
            {
                "uri": "/",
                "method": "GET",
                "status_code": 200,
                "port": 2105,
                "response_check": {
                    "contains": ["Hello, World!"],
                    "match": ["... regex"],
                    "empty": "bool"
                }
            }
        ],
        "image": "unikraft.org/caddy:2.7",
        "memory": "512M",
        "plat": "QEMU",
        "ports": [
            # ...
            # array of tuples
            [
                2105,
                2015
            ]
        ],
        "return_code": {
            "equals": 0,
            "not_equal_to": 1,
            "greater_than": -1
        },
        "stderr_check": {
            "contains": [
                ""
            ],
            "match": [
                ""
            ],
            "empty": true
        },
        "stdout_check": {
            "contains": [
                "server running",
                "serving initial configuration"
            ],
            "match": "^Powered by Unikraft",
            "empty": true
        }
    }
]
"""

# type response_check = dict[str, list[str] |bool] # 3.12
from typing import TypedDict

t_response_check = TypedDict(
    "response_check", {"contains": list[str], "match": list[str], "empty": bool}
)
t_http_check = TypedDict(
    "http_check",
    {
        "uri": str,
        "method": str,
        "port": int,
        "status_code": int,
        "response_check": t_response_check,
    },
)
t_return_code = TypedDict(
    "return_code", {"equals": int, "not_equal_to": int, "greater_than": int}
)
t_stdout_check = TypedDict(
    "stdout_check", {"contains": list[str], "match": list[str], "empty": bool}
)
t_stderr_check = TypedDict(
    "stdout_check", {"contains": list[str], "match": list[str], "empty": bool}
)
t_args = TypedDict(
    "args", {"disable-acceleration": bool, "rootfs": str, "volume": str, "memory": str}
)
t_port_map = tuple[int, int]
t_test_case = TypedDict(
    "test_case",
    {
        "arch": Architecture,
        "args": t_args,
        "http_check": list[t_http_check],
        "image": str,
        "memory": str,
        "plat": Platforms,
        "ports": list[t_port_map],
        "return_code": t_return_code,
        "stderr_check": t_stderr_check,
        "stdout_check": t_stdout_check,
        "timeout": int,
    },
)


# TODO: unit test the command generation from the spec
# TODO: should we support multiple volumes bind mount ? as an array
# TODO: write a runtime spec checker based on the typing definitions
# TODO: should add the timeout to the test_case with a sane default
# TODO: switch to yaml
# TODO: supporting all http methods, requires providing other args to pass body params
#       for post/patch etc ..., current implementation works for get,head,options
# TODO: define the behavior when missing arguments
# TODO: print stdout when exit code is not what is expected
# TODO: show human readable errno descriptions
# TODO: in the case where kraft hangs, or fails with open subprocesses
#       we should track / register the names of vm's launched and remove them using the
#       kraft remove command, we need to do this if we do `process.kill()` where it seems
#       killing the main kraft process without sigterm can leave the launched vms open
#       due to not allowing it to do a graceful shutdown, the vms are removed since
#       we pass the `--rm` option when launching. e.i if we want to use SIGKILL we should
#       clean the launched vms by keeping track of their ids, and removing em manually.
def run_test_case(test_case: t_test_case) -> dict["str"]:
    ports_arg = ""
    ports = []
    if "ports" in test_case:
        ports = test_case["ports"]
        if test_case["ports"]:
            ports_arg = "-p" + " ".join(
                [f"{published}:{internal}" for published, internal in ports]
            )
    args = []
    if "args" in test_case:
        for arg_name, arg_value in test_case["args"].items():
            if arg_value:
                if type(arg_value) is bool:
                    args.append(f"--{arg_name}")
                else:
                    args.append(f"--{arg_name} {arg_value}")
    command = (
        f"kraft run --rm {ports_arg} --plat {test_case['plat'].value}"
        f" {' '.join(args)} --arch {test_case['arch'].value} {test_case['image']}"
    )
    print(
        f"Testing {test_case['image']} on {test_case['plat'].value}/{test_case['arch'].value}"
    )
    print(f"=> kraft command: \n`{command}`")
    # TODO: ...
    process: subprocess.Popen = subprocess.Popen(
        command.split(),
        close_fds=True,
        start_new_session=True,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    timeout = 2
    if "timeout" in test_case:
        timeout = test_case["timeout"]
    print(f"=> pid: {process.pid}")
    ports_tcp_check_results = dict()
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        if process.poll() == 1:
            print(f"❌ Failed to run {test_case['image']}")
            print(f"=> kraft stdout:")
            print(f"```\n{stdout.decode()}```")

    except subprocess.TimeoutExpired:
        # BUG: if the process fails, but takes during initialization longer than `timeout`
        # for example in the case of `pull`
        if ports:
            for port, _ in ports:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                err = s.connect_ex(("localhost", port))
                ports_tcp_check_results[port] = err
                s.close()
        if "http_check" in test_case:
            # breakpoint()
            for http_check in test_case["http_check"]:
                # TODO: assumes all ports are http # Fixed
                # r = requests.get(f"http://localhost:{port}{http_check['uri']}") # <- wrong port
                try:
                    r = requests.request(
                        method=http_check["method"],
                        url=f"http://localhost:{http_check['port']}{http_check['uri']}",
                    )
                    http_check["result"] = r
                except requests.ConnectionError as e:
                    http_check["error"] = e
        process.terminate()
        stdout, stderr = process.communicate()
        if process.poll() == 1:
            print(f"❌ Failed to run {test_case['image']}")
            print(f"=> kraft stdout:")
            print(f"```\n{stdout.decode()}```")
    except:
        process.kill()
        raise
    # breakpoint()
    if "stdout_check" in test_case:
        print("=> stdout_check:")
        if "contains" in test_case["stdout_check"]:
            for substr in test_case["stdout_check"]["contains"]:
                if substr.encode() in stdout:
                    print(f"✅ Check '{substr}' in stdout")
                else:
                    print(f"❌ Check '{substr}' in stdout")
        # TODO: match
        if "empty" in test_case["stdout_check"]:
            if stdout == b"":
                print(f"✅ Check stdout is empty")
            else:
                print(f"❌ Check stdout is empty")
    if "stderr_check" in test_case:
        print("=> stderr_check:")
        if "contains" in test_case["stderr_check"]:
            for substr in test_case["stderr_check"]["contains"]:
                if substr.encode() in stderr:
                    print(f"✅ Check '{substr}' in stderr")
                else:
                    print(f"❌ Check '{substr}' in stderr")
        # TODO: match
        if "empty" in test_case["stderr_check"]:
            if stderr == b"":
                print(f"✅ Check stderr is empty")
            else:
                print(f"❌ Check stderr is empty")
    if "return_code" in test_case:
        print("=> return_code:")
        if "equals" in test_case["return_code"]:
            if process.poll() == test_case["return_code"]["equals"]:
                print(f"✅ Check exit code equals {test_case['return_code']['equals']}")
            else:
                print(
                    f"❌ Check exit code equals {test_case['return_code']['equals']}, got: {process.poll()}"
                )

        if "not_equal_to" in test_case["return_code"]:
            if process.poll() == test_case["return_code"]["not_equal_to"]:
                print(
                    f"❌ Check exit code not equal to {test_case['return_code']['not_equal_to']}"
                )
            else:
                print(
                    f"✅ Check exit code not equal to {test_case['return_code']['not_equal_to']}"
                )
        if "greater_than" in test_case["return_code"]:
            if process.poll() > test_case["return_code"]["greater_than"]:
                print(
                    f"✅ Check exit code greater than {test_case['return_code']['greater_than']}"
                )
            else:
                print(
                    f"❌ Check exit code greater than {test_case['return_code']['greater_than']}, got: {process.poll()}"
                )
    # check tcp
    if ports_tcp_check_results:
        print("=> tcp_check:")
        for port, err in ports_tcp_check_results.items():
            if err == 0:
                print(f"✅ Check tcp port {port} is listening")
            else:
                print(
                    f"❌ Check tcp port {port} is listening, got: errno = {err} ({errno.errorcode[err]})"
                )
    # breakpoint()
    if "http_check" in test_case:
        print("=> http_check:")
        for http_check in test_case["http_check"]:
            if "error" in http_check:
                print(
                    f"❌ Check '{http_check['uri']}' failed with error {http_check['error']}"
                )
                continue
            response = http_check["result"]
            if response.status_code == http_check["status_code"]:
                print(f"✅ Check '{response.url}' returns {response.status_code}")
            else:
                print(
                    f"❌ Check '{response.url}' returns ok, got: {response.status_code}"
                )
            if "response_check" in http_check:
                if "contains" in http_check["response_check"]:
                    for substr in http_check["response_check"]["contains"]:
                        if substr in response.text:
                            print(f"✅ Check '{substr}' in '{response.url}' Body")
                        else:
                            print(f"❌ Check '{substr}' in '{response.url}' Body")
                # TODO: match
                if "empty" in http_check["response_check"]:
                    if response.text == "":
                        print(f"✅ Check '{response.url}' body is empty")
                    else:
                        print(f"❌ Check '{response.url}' body is empty")


if __name__ == "__main__":
    import argparse
    import json
    import yaml

    yaml.warnings({"YAMLLoadWarning": False})

    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=argparse.FileType())
    parser.add_argument("--filter", type=str, nargs="+")

    args = parser.parse_args()
    if args.file:
        test_cases: list[t_test_case] = []
        if args.file.name.endswith(".yaml"):
            test_cases = yaml.load(args.file, Loader=yaml.FullLoader)
        else:
            test_cases = json.load(args.file)
        filters = []
        if args.filter:
            filters = [s.split("=") for s in args.filter]

        # breakpoint()
        def f(t):
            # breakpoint()
            for key, value in filters:
                if (key not in t) or (t[key] != value):
                    return False
            return True

        for test_case in filter(f, test_cases):
            test_case["arch"] = Architecture(test_case["arch"].lower())
            test_case["plat"] = Platforms(test_case["plat"].lower())
            try:
                run_test_case(test_case)
            except:
                print(test_case)
                raise

    # TODO: add some general filtering of testcase's
    #       for example running just a specific architecture
    #       or a specific image
    # TODO: extract the targets from the kraftfile
