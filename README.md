<div align="center">

# CommitGuard

**Stops you from committing passwords, API keys, and Thai ID numbers by mistake.**

A small tool for Git. It checks the lines you are about to commit, and warns you before a secret leaves your computer.

[What it finds](#what-it-finds) &bull; [How it works](#how-it-works) &bull; [Install](#install) &bull; [Use](#use) &bull; [Known limits](#known-limits)

</div>

---

## What is this?

Sometimes a developer types an API key or a real ID number into code "just to test", then forgets it and commits. If the repository is public, the secret is public too.

CommitGuard is a **pre-commit hook**. A hook is a small program that Git runs automatically at a certain moment. A *pre-commit* hook runs just before a commit is created. CommitGuard uses this moment to scan your staged changes. (Staged means: files you added with `git add`.)

- It reads **only the lines you added**, not your whole project.
- It uses **only the Python standard library**. You do not need `pip install`.
- If it finds something, it shows a table and asks you: stop the commit, or continue.

**Tested on:** Windows, Python 3.14.
**UNVERIFIED:** Linux, macOS, and Python 3.8 to 3.13. I have not run CommitGuard there.

## What it finds

| What | Example | How it is found |
|------|---------|-----------------|
| Thai national ID | `1-1001-00123-45-4` | 13 digits, and the check digit must be correct (Modulo 11) |
| Thai mobile phone | `081-234-5678` | Starts with 06, 08 or 09 |
| Private key header | `-----BEGIN RSA PRIVATE KEY-----` | Pattern match |
| AWS access key | `AKIA...` | Pattern match |
| OpenAI-style key | `sk-...` | Pattern match |
| GitHub token | `ghp_...` | Pattern match |
| Random-looking strings | `wJalrXUtnFEMI/K7...` | Shannon entropy (see below) |

## How it works
---

```mermaid
flowchart TD
    A["You run git commit"] --> B["Git runs the hook<br/>.git/hooks/pre-commit"]
    B --> C["commitguard.py"]
    C --> D["scanner.py<br/>runs git diff --cached"]
    D --> E["Keep only the added lines (+)"]
    E --> F["validators.py<br/>Thai ID, phone, private key, API keys"]
    E --> G["entropy.py<br/>random-looking strings"]
    F --> H{"Found anything?"}
    G --> H
    H -- "No" --> I["Print CLEAN<br/>exit code 0, commit continues"]
    H -- "Yes" --> J["cli.py shows the alert table"]
    J --> K["Ask: Abort or Bypass?"]
    K -- "A" --> L["exit code 1<br/>commit is blocked"]
    K -- "B" --> M["exit code 0<br/>commit continues"]
```

Git decides what to do from the **exit code** of the hook. Code `0` means "OK, continue". Any other code means "stop the commit".

### Why the prompt reads from the terminal directly

A hook cannot always count on normal keyboard input (`sys.stdin`). So CommitGuard opens the terminal itself: `/dev/tty` on Linux and macOS, `CONIN$` on Windows. If it cannot open a terminal (for example, on a server with nobody there), it aborts the commit. This is a **fail-safe**: when in doubt, block.

**UNVERIFIED:** the `CONIN$` behavior on Windows and the "no terminal" case in a real CI system. The code is written for them, but I have not tested them.

<details>
<summary><b>The ideas behind it: Shannon entropy</b></summary>

<br>

**Entropy** measures how mixed and unpredictable the characters in a string are. The formula (Claude Shannon, 1948):

```
H = -sum( p(x) * log2(p(x)) )     p(x) = how often character x appears
```

The result is in *bits per character*. Three small examples:

| String | Entropy | Why |
|--------|---------|-----|
| `aaaaaaa` | 0.0 | Always the same character |
| `abababab` | 1.0 | Two characters, equal share |
| `abcdefghijklmnop` | 4.0 | 16 different characters, each once |

A real secret key is usually random, so its characters are very mixed and its entropy is high. Normal code repeats letters a lot, so its entropy is lower.

CommitGuard flags a string when **both** are true:
1. It is at least **16 characters** long.
2. Its entropy is at least **4.3**.

**Two facts about the limits** (these come from the math, not from guessing):
- A string with `n` characters can never have more than `log2(n)` bits. So a 16-character string tops out at 4.0 and can **never** reach 4.3. You need at least 20 characters.
- A hex string (`0-9a-f`) has only 16 different symbols, so its maximum is `log2(16) = 4.0`. A random hex secret can **never** be caught by entropy alone. Base64 has 64 symbols, so its maximum is 6.

Entropy cannot tell a secret from a file path. It only sees "mixed characters". See [Known limits](#known-limits) for a real example.

</details>

<details>
<summary><b>The ideas behind it: Thai national ID and Modulo 11</b></summary>

<br>

A Thai national ID has 13 digits. The last digit is a **check digit**. It is calculated from the first 12 digits, so it can catch typing mistakes. CommitGuard uses the same calculation to tell a real-looking ID from a random 13-digit number.

Steps (using `1234567890121` as the example):

1. Multiply the first 12 digits by the weights 13, 12, 11, ... 2.
   `1×13 + 2×12 + 3×11 + 4×10 + 5×9 + 6×8 + 7×7 + 8×6 + 9×5 + 0×4 + 1×3 + 2×2 = 352`
2. Take the remainder of the sum divided by 11: `352 mod 11 = 0`.
3. Check digit = `(11 − remainder) mod 10` = `(11 − 0) mod 10 = 1`.
4. The 13th digit is `1`. It matches, so the ID is valid.

The weights are different for each position, so swapping two digits changes the sum, and the mistake is caught. IDs where all 13 digits are the same (like `1111111111111`) are rejected.

This only checks the math. It cannot know if the person really exists. By chance, about 1 in 10 random 13-digit numbers also passes.

</details>

## Install
---

You install CommitGuard **into the repository you want to protect**. Run the installer while your terminal is inside that repository.

**Windows**

```powershell
cd path\to\your\project
path\to\CommitGuard\install.bat
```

**Linux / macOS** (UNVERIFIED: I wrote `install.sh` but I have not run it)

```bash
cd path/to/your/project
chmod +x path/to/CommitGuard/install.sh
path/to/CommitGuard/install.sh
```

**Or directly with Python**

```powershell
cd path\to\your\project
python path\to\CommitGuard\commitguard.py --install
```

What the installer does:
- It writes the file `.git/hooks/pre-commit` in your project.
- That file contains the **full path** to `commitguard.py`. So do not move or delete the CommitGuard folder after you install.
- It adds a marker comment `# CommitGuard-Hook` to the file. If you already have a pre-commit hook that CommitGuard did not write, `--install` and `--uninstall` refuse to touch it.

## Use
---

After you install, use Git as usual:

```powershell
git add .
git commit -m 'my message'
```

If everything is fine, you see `[CLEAN]` and the commit goes on. If CommitGuard finds something, you see a table like this (example, not real data):

```
 [SECURITY ALERT]  Detected 1 potential secret(s) / PII in staged changes!

------------------------------------------------------------------------------------
FILE                     LINE   CATEGORY   TYPE                       SCORE    SNIPPET
------------------------------------------------------------------------------------
config.py                12     SECRET     AWS Access Key             3.68     AK...LE
------------------------------------------------------------------------------------

[CommitGuard Action Required]
  [A] Abort commit (Fix your secrets)
  [B] Bypass and proceed anyway
Select action [A/B]:
```

- The **snippet is masked**. Like a bank app that shows `**** 1234`, it shows only about 20% of the characters, so the secret is not printed in full in your terminal.
- Type `A` and Enter to stop the commit. Remove the secret, then commit again.
- Type `B` and Enter if you checked and it is a false alarm.
- If you press Ctrl-D (end of input), CommitGuard treats it as `A`.

### Commands
---

| Command | What it does |
|---------|--------------|
| `python commitguard.py --install` | Installs the hook in the current repository |
| `python commitguard.py --scan` | Scans the staged changes now, without committing |
| `python commitguard.py --uninstall` | Removes the hook (only if CommitGuard wrote it) |
| `python commitguard.py --help` | Shows help |

## Project structure
---

```text
CommitGuard/
├── commitguard.py      # Entry point: reads the command and calls the right function
├── install.sh          # Installer for Linux and macOS (UNVERIFIED)
├── install.bat         # Installer for Windows
├── src/
│   ├── entropy.py      # Shannon entropy and the high-entropy check
│   ├── validators.py   # Thai ID (Modulo 11), phone, private key, API key patterns
│   ├── scanner.py      # Runs git diff --cached and finds the added lines
│   └── cli.py          # Output, the A/B prompt, install and uninstall
├── tests/
│   ├── test_core.py    # Tests for entropy and validators (16 tests)
│   └── test_scanner.py # Tests for the diff parser and the CLI (15 tests)
├── NOTES.md            # What I learned from each bug
└── ROADMAP.md          # Bug list and plan
```

## Tests
---

```powershell
cd path\to\CommitGuard
python -m unittest discover -s tests -v
```

There are **31 tests**. They cover entropy, the Thai ID check, the phone / key / token patterns, the diff parser, masking, the A and B choices, and the install / uninstall rules (including "do not touch a hook that is not ours").

## Known limits
---

CommitGuard is not finished. This list is honest. I am fixing these one by one (see [ROADMAP.md](ROADMAP.md)).

**It can miss real secrets** (false negatives)
- Random hex secrets are never caught by entropy (maximum is 4.0, the threshold is 4.3).
- Short random keys are often missed. In my tests with random base64 at threshold 4.3, 16 characters were never caught, 24 characters about 44% of the time, and 32 characters about 97%.
- Only 3 API key patterns exist today. An `sk-ant-` key is labelled "OpenAI".
- An added line that starts with `++` can be dropped by the diff parser, and the line numbers after it can shift.
- Thai or non-ASCII file names: Git puts quotes around the path, so the file name may be wrong.
- Thai ID and phone patterns can fail when the number touches a Thai letter or underscore, and `+66` or `081 234 5678` are not matched.
- `git commit --no-verify` skips every hook, including this one. CommitGuard cannot stop that.
- If you set `core.hooksPath`, `--install` still writes to `.git/hooks`.

**It can warn when nothing is wrong** (false positives)
- It flags its own code. Example: the path `SCRIPT_DIR/commitguard.py` has entropy 4.40, so it was reported as a secret.
- Package lock hashes, public certificate lines, and a CSS class like `sk-circle-fade-...` can be flagged.
- About 1 in 10 random 13-digit numbers (for example, a timestamp in milliseconds) passes the Thai ID check.
- One private key can produce many findings (one per line).
- Phone numbers are noisy. Plan: a phone number alone will only **warn** and will not block the commit. **Not done yet:** today a phone number shows the same A/B prompt.

**Not tested yet (UNVERIFIED)**
- Linux and macOS (including `install.sh`)
- Python versions other than 3.14
- Folder paths that contain spaces
- The Windows `python3` Store shortcut
- `CONIN$` on Windows, and a real CI system without a terminal

---

*Last updated: 15 Oct 2026.*
