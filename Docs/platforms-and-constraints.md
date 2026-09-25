# Platforms and constraints

State: partially implemented

## Platform coverage

| Area | macOS | Windows | Linux |
| --- | --- | --- | --- |
| Python CLI, profiles, JSON state | Locally exercised | Hosted Python 3.11/3.14 tests passed | Hosted Python 3.11/3.14 tests passed |
| Installation discovery | Native paths, Homebrew, tool managers exercised | PATH/native locations/registry/tool environments; validation pending | PATH/native locations/dpkg/rpm/tool environments; validation pending |
| Agent launch with Ollama | Claude Code, OpenCode 2, Aider live checks | Native checks pending | Native checks pending |
| Full offline mode | Claude Code/Aider live checks | Unsupported; fail closed | Unsupported; fail closed |
| Installer/uninstaller routes | Fixture coverage; loc package install/uninstall exercised | Fixture/command coverage; native checks pending | Release wheel install/repeat/uninstall passed in hosted Linux; dependency installer checks pending |

Python 3.11+ is required for loc. Supported agent versions and their interpreter/runtime requirements are independent. Existing incompatible installations remain present; loc never obtains another copy as a shortcut.

## Shared conventions

User state is separate from package files: macOS Application Support, Windows LOCALAPPDATA, or Linux XDG state paths. `LOC_HOME` or `--home` overrides it for testing. File replacement is atomic and mutation locks use platform-native facilities. Imported profiles contain no machine paths or executable instructions.

Installation, update, browser availability, executable resolution, process inspection, and privileges vary by platform. Privilege errors remain actionable failures; loc does not silently escalate or declare success. Unsupported hardware/agent/runtime combinations must be explicit.

## Remaining limits

Native Windows versus WSL is not interchangeable. WSL, containers, and other users' hidden environments are outside exhaustive discovery coverage; register custom locations or resolve uncertainty before installation. Minimum supported OS versions, AMD/Intel accelerator behavior, additional CPU architectures, shell completion activation, and native package lifecycle behavior need platform testing.

No support claim follows merely from a Python branch or workflow definition. The current evidence is listed in [Implementation and verification](implementation-and-testing.md).

## Delivery evidence

Mac runtime, package, network-sandbox, and coding-agent checks passed. Portable state and platform-specific branches have automated fixture coverage. Hosted CLI tests passed on Windows/Linux; live agents and OS-specific dependency installers remain pending.
