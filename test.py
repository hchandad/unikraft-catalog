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
    except subprocess.TimeoutExpired:
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
    assert stdout_check.encode() in stdout
    # check stderr is empty
    if stderr_check:
        assert stderr == b""
    # check return code
    if return_code:
        assert process.poll() == return_code
    # check tcp
    for port, errno in ports_tcp_check_results.items():
        assert errno == 0
    # check http
    for port, response in http_check_results.items():
        assert response.ok == True
        # TODO:
        # assert "Hello, World!" in r.text
        assert http_response_check in response.text
    # TODO: add the ability to run a bash command
    # redis-cli/curl/nc that should return 0
    # TODO: add the ability to do multiple stdout .includes tests
    pass


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


def run_tests_from_json():
    import json

    fd = open("tests.json")
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


if __name__ == "__main__":
    run_tests_from_json()
