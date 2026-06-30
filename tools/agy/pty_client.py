import os
import time
import select
import signal
from utils import REAL_AGY, strip_ansi

def get_quota_via_pty(email, sandbox_dir=None):
    import pty
    import fcntl
    import termios
    import struct

    master, slave = pty.openpty()
    s = struct.pack("HHHH", 24, 80, 0, 0)
    try:
        fcntl.ioctl(master, termios.TIOCSWINSZ, s)
    except:
        pass

    pid = os.fork()
    if pid == 0:
        os.setsid()
        os.dup2(slave, 0)
        os.dup2(slave, 1)
        os.dup2(slave, 2)
        os.close(master)
        os.close(slave)

        env = os.environ.copy()
        if sandbox_dir:
            env["HOME"] = sandbox_dir
            try:
                os.chdir(sandbox_dir)
            except OSError:
                pass

        try:
            os.execve(REAL_AGY, [REAL_AGY], env)
        except:
            os._exit(127)
    else:
        os.close(slave)

        output = b""

        # Wait dynamically for prompt (e.g. '>') or 'shortcuts' up to 12 seconds
        start_time = time.time()
        while time.time() - start_time < 12.0:
            r, _, _ = select.select([master], [], [], 0.1)
            if r:
                try:
                    chunk = os.read(master, 4096)
                    if not chunk:
                        break
                    output += chunk
                    # Auto-confirm workspace trust if prompted (e.g. running in untrusted Cwd)
                    if b"trust the contents" in chunk or b"trust this folder" in chunk or b"requires permission" in chunk:
                        try:
                            os.write(master, b"\x0d")
                        except:
                            pass
                    if b"\r\n>" in output or b"shortcuts" in output:
                        # Flush any remaining bytes
                        time.sleep(0.1)
                        r2, _, _ = select.select([master], [], [], 0.05)
                        if r2:
                            output += os.read(master, 4096)
                        break
                except OSError:
                    break
            else:
                time.sleep(0.05)

        # Send /usage
        try:
            os.write(master, b"/usage\x0d")
        except:
            pass

        # Read quota output (up to 4 seconds)
        quota_start = time.time()
        while time.time() - quota_start < 4:
            r, _, _ = select.select([master], [], [], 0.2)
            if r:
                try:
                    chunk = os.read(master, 4096)
                    if not chunk:
                        break
                    output += chunk
                    if b"Model Quota" in chunk or b"remaining" in chunk or b"Quota available" in chunk or b"matches" in chunk:
                        time.sleep(0.3)
                        r2, _, _ = select.select([master], [], [], 0.05)
                        if r2:
                            output += os.read(master, 4096)
                        break
                except OSError:
                    break

        # Send exit command
        try:
            os.write(master, b"/exit\x0d")
        except:
            pass

        # The CLI may ignore /exit while it is still rendering. Never return
        # while it can still rewrite the shared token file.
        try:
            deadline = time.time() + 2.0
            while time.time() < deadline:
                finished, _ = os.waitpid(pid, os.WNOHANG)
                if finished == pid:
                    break
                time.sleep(0.1)
            else:
                os.killpg(pid, signal.SIGTERM)
                deadline = time.time() + 1.0
                while time.time() < deadline:
                    finished, _ = os.waitpid(pid, os.WNOHANG)
                    if finished == pid:
                        break
                    time.sleep(0.1)
                else:
                    os.killpg(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
        except (ChildProcessError, ProcessLookupError):
            pass
        finally:
            os.close(master)

        return strip_ansi(output.decode(errors="ignore"))
