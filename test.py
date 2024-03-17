import subprocess
import socket
import requests


def test_helloworld():
    # launch the app
    process: subprocess.CompletedProcess = subprocess.run(
        "kraft run --rm unikraft.org/helloworld:latest".split(),
        capture_output=True,
        timeout=10,
    )
    # check stdout
    assert b"Hello from Unikraft!" in process.stdout
    # check return code
    assert process.returncode == 0
    # check stderr is empty
    assert process.stderr == b""


def __test_base():
    # launch the app
    process: subprocess.Popen = subprocess.Popen(
        "kraft run --rm unikraft.org/base:latest".split(),
    )
    try:
        stdout, stderr = process.communicate(timeout=10)
        # check stdout
        assert b"Happy krafting!" in stdout
        # check stderr is empty
        assert stderr == b""
    except subprocess.TimeoutExpired:
        # end if hanging
        process.terminate()
        stdout, stderr = process.communicate(timeout=10)
        # check stdout
        assert b"Happy krafting!" in stdout
        # check stderr is empty
        assert stderr == b""


def test_base():
    process: subprocess.CompletedProcess = subprocess.run(
        "kraft run --rm unikraft.org/helloworld:latest".split(),
        capture_output=True,
        timeout=10,
    )
    # check stdout
    assert b"Hello from Unikraft!" in process.stdout
    # check stderr is empty
    assert process.stderr == b""
    # check return code
    assert process.returncode == 0


PORT = 2105


def __test_caddy():
    breakpoint()
    try:
        process: subprocess.CompletedProcess = subprocess.run(
            f"kraft run --rm -M 512M -p {PORT}:2015 --plat qemu --arch x86_64 unikraft.org/caddy:2.7".split(),
            capture_output=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired as e:
        print(e)


def test_caddy():
    # breakpoint()
    process: subprocess.Popen = subprocess.Popen(
        f"kraft run --rm -M 512M -p {PORT}:2015 --plat qemu --arch x86_64 unikraft.org/caddy:2.7".split(),
        close_fds=True,
        start_new_session=True,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    try:
        stdout, stderr = process.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        # TODO: check tcp
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        err = s.connect_ex(("localhost", PORT))
        # TODO: check http
        r = requests.get(f"http://localhost:{PORT}")
        process.terminate()
        stdout, stderr = process.communicate()
    except:
        process.kill()
        raise
    breakpoint()
    # check stdout
    assert b"serving initial configuration" in stdout
    # check stderr is empty
    assert stderr == b""
    # check return code
    assert process.poll() == 0
    # check tcp
    assert err == 0
    # check http
    assert r.ok == True
    assert "Hello, World!" in r.text
    # breakpoint()


def run_tests():
    # test_caddy()
    # test_helloworld
    run_test(
        image="unikraft.org/helloworld:latest",
        memory="512M",
        ports=dict(),
        arch=Architecture.X86_64,
        plat=Platforms.QEMU,
        http_check_uri="",
        http_response_check="",
        stdout_check="Hello from Unikraft!",
        stderr_check=True,
        return_code=0,
    )
    # test_base
    run_test(
        image="unikraft.org/base:latest",
        memory="512M",
        ports=dict(),
        arch=Architecture.X86_64,
        plat=Platforms.QEMU,
        http_check_uri="",
        http_response_check="",
        stdout_check="Hello from Unikraft!",
        stderr_check=True,
        return_code=0,
    )
    # test_caddy
    run_test(
        image="unikraft.org/caddy:2.7",
        memory="512M",
        ports={PORT: 2015},
        arch=Architecture.X86_64,
        plat=Platforms.QEMU,
        http_check_uri="/",
        http_response_check="Hello, World!",
        stdout_check="serving initial configuration",
        stderr_check=True,
        return_code=0,
    )
    # test_lua:5.4.4
    run_test(
        image="unikraft.org/lua:5.4.4",
        memory="512M",
        ports={PORT: 8080},
        arch=Architecture.X86_64,
        plat=Platforms.QEMU,
        http_check_uri="/",
        http_response_check="Hello, World!",
        stdout_check="",
        stderr_check=True,
        return_code=0,
    )
    # test_nginx:1.25
    run_test(
        image="unikraft.org/nginx:1.25",
        memory="512M",
        ports={PORT: 80},
        arch=Architecture.X86_64,
        plat=Platforms.QEMU,
        http_check_uri="/",
        http_response_check="<h1>Welcome to nginx!</h1>",
        stdout_check="",
        stderr_check=True,
        return_code=0,
    )
    # test_memcached:1.6
    run_test(
        image="unikraft.org/memcached:1.6",
        memory="512M",
        ports={PORT: 112111},
        arch=Architecture.X86_64,
        plat=Platforms.QEMU,
        http_check_uri="",
        http_response_check="",
        stdout_check="",
        stderr_check=True,
        return_code=0,
    )
    # test_redis:7.2
    run_test(
        image="unikraft.org/redis:7.2",
        memory="512M",
        ports={PORT: 6379},
        arch=Architecture.X86_64,
        plat=Platforms.QEMU,
        http_check_uri="",
        http_response_check="",
        stdout_check="Ready to accept connections tcp",
        stderr_check=True,
        return_code=0,
    )


from enum import Enum


class Platforms(Enum):
    QEMU = "qemu"


class Architecture(Enum):
    X86_64 = "x86_64"


# TODO: cleanup the process on all exceptions
# TODO: support the yaml spec
# TODO: support extra kraft run options ...
# TODO: use pytest as a library for a better output / traceback
# TODO: add output
# TODO: add parsable output (non human)
# TODO: we can write unit tests by passing specific json objects to run
#       and checking the error sample output, requires non human output to be done
def run_test(
    image: str,
    memory: str,
    ports: dict[int, int],
    plat: Platforms,  # switch to enum
    arch: Architecture,  # switch to enum
    http_check_uri: str,
    http_response_check: str,
    stdout_check: str,
    stderr_check: bool,  # pass an array of functions that should return true
    # that are passed the stderr value
    return_code: int,
):
    # breakpoint()
    ports_arg = ""
    if ports:
        ports_arg = "-p" + " ".join([f"{key}:{value}" for key, value in ports.items()])
    command = f"kraft run --rm -M {memory} {ports_arg} --plat {plat.value} --arch {arch.value} {image}"
    process: subprocess.Popen = subprocess.Popen(
        command.split(),
        close_fds=True,
        start_new_session=True,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )
    ports_tcp_check_results = dict()
    http_check_results = dict()
    print(f"Testing {image} on {plat.value}/{arch.value}")
    try:
        stdout, stderr = process.communicate(timeout=2)
        if process.poll() == 1:
            print(f"❌ Failed to run {image}")
            print(f"=> kraft command: \n`{command}`")
            print(f"=> kraft stdout:")
            print(f"```\n{stdout.decode()}```")
            # print("kraft stderr", stderr)
    except subprocess.TimeoutExpired:
        # breakpoint()
        if ports:
            for port in ports:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                err = s.connect_ex(("localhost", port))
                ports_tcp_check_results[port] = err
                s.close()
                # TODO: assumes all ports are http
                if http_check_uri:
                    r = requests.get(f"http://localhost:{port}{http_check_uri}")
                    http_check_results[port] = r
        process.terminate()
        stdout, stderr = process.communicate()
    except:
        process.kill()
        raise
    # breakpoint()
    # check stdout
    if stdout_check:
        if stdout_check.encode() in stdout:
            print(f"✅ Check '{stdout_check}' in stdout")
        else:
            print(f"❌ Check '{stdout_check}' in stdout")
    # check stderr is empty
    if stderr_check:
        if stderr == b"":
            print(f"✅ Check stderr is empty")
        else:
            print(f"❌ Check stderr is empty")
    # check return code
    if return_code:  # TODO: fixme
        if process.poll() == return_code:
            print(f"✅ Check exit code equals {return_code}")
        else:
            print(f"❌ Check exit code equals {return_code}, got: {process.poll()}")
    # check tcp
    for port, errno in ports_tcp_check_results.items():
        if errno == 0:
            print(f"✅ Check tcp port {port} is listening")
        else:
            print(f"❌ Check tcp port {port} is listening, got: errno = {errno}")
    # check http
    for port, response in http_check_results.items():
        if response.ok == True:
            print(f"✅ Check '{response.url}' returns {response.status_code}")
        else:
            print(f"❌ Check '{response.url}' returns ok, got: {response.status_code}")
        # TODO:
        # assert "Hello, World!" in r.text
        if http_response_check in response.text:
            print(f"✅ Check '{http_response_check}' in {response.url}' Body")
        else:
            print(f"❌ Check '{http_response_check}' in {response.url}' Body")
    # TODO: add the ability to run a bash command
    # redis-cli/curl/nc that should return 0
    # TODO: add the ability to do multiple stdout .includes tests
    pass


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
    {"uri": str, "method": str, "status_code": int, "response_check": t_response_check},
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
t_args = TypedDict("args", {"disable-acceleration": bool, "rootfs": str, "volume": str})
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
def run_test_case(test_case: t_test_case) -> dict["str"]:
    ports = test_case["ports"]
    ports_arg = ""
    if test_case["ports"]:
        ports_arg = "-p" + " ".join(
            [f"{published}:{internal}" for published, internal in ports]
        )
    args = []
    for arg_name, arg_value in test_case["args"].items():
        if arg_value:
            if type(arg_value) is bool:
                args.append(f"--{arg_name}")
            else:
                args.append(f"--{arg_name} {arg_value}")
    command = (
        f"kraft run --rm -M {test_case['memory']} {ports_arg} --plat {test_case['plat'].value}"
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
    ports_tcp_check_results = dict()
    http_check_results = dict()
    try:
        stdout, stderr = process.communicate(timeout=2)
        if process.poll() == 1:
            print(f"❌ Failed to run {test_case['image']}")
            print(f"=> kraft stdout:")
            print(f"```\n{stdout.decode()}```")

    except subprocess.TimeoutExpired:
        if ports:
            for port, _ in ports:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                err = s.connect_ex(("localhost", port))
                ports_tcp_check_results[port] = err
                s.close()
        for http_check in test_case["http_check"]:
            # TODO: assumes all ports are http # Fixed
            # r = requests.get(f"http://localhost:{port}{http_check['uri']}") # <- wrong port
            r = requests.request(
                method=http_check["method"],
                url=f"http://localhost:{http_check['port']}{http_check['uri']}",
            )
            http_check["result"] = r
        process.terminate()
        stdout, stderr = process.communicate()
    except:
        process.kill()
        raise
    # breakpoint()
    if test_case["stdout_check"]:
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
    if test_case["stderr_check"]:
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
    if test_case["return_code"]:
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
        for port, errno in ports_tcp_check_results.items():
            if errno == 0:
                print(f"✅ Check tcp port {port} is listening")
            else:
                print(f"❌ Check tcp port {port} is listening, got: errno = {errno}")
    if test_case["http_check"]:
        print("=> http_check:")
        for http_check in test_case["http_check"]:
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


def run_tests_from_json(fd):
    import json

    test_cases = json.load(fd)
    for test_case in test_cases:
        run_test(
            image=test_case["image"],
            memory=test_case["memory"],
            ports={p: pi for p, pi in test_case["ports"]},
            arch=Architecture(test_case["arch"].lower()),
            plat=Platforms(test_case["plat"].lower()),
            http_check_uri=test_case["http_check_uri"],
            http_response_check=test_case["http_response_check"],
            stdout_check=test_case["stdout_check"],
            stderr_check=test_case["stderr_check"],
            return_code=test_case["return_code"],
        )


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=argparse.FileType())

    args = parser.parse_args()
    if args.file:
        # run_tests_from_json(args.file)
        test_cases: list[t_test_case] = json.load(args.file)
        for test_case in test_cases:
            test_case["arch"] = Architecture(test_case["arch"].lower())
            test_case["plat"] = Platforms(test_case["plat"].lower())
            run_test_case(test_case)
