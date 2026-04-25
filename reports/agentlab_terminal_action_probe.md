# Terminal Action Probe

- Task: `browsergym/miniwob.terminal`
- Seed: `27`
- Base URL: `file:///Users/lxl/lxl_code/hermes_lxl/external/miniwob-plusplus/miniwob/html/miniwob/`
- Working sequences: `4`

## Summary

| Sequence | Errors | Command Visible | Terminal Changed | Reward | Terminated |
|---|---:|---|---|---:|---|
| `fill_press` | 0 | false | true | 0.00 | false |
| `focus_keyboard_type_enter` | 0 | true | true | 0.00 | false |
| `click_input_keyboard_type_enter` | 0 | true | true | 0.00 | false |
| `click_terminal_keyboard_type_enter` | 0 | true | true | 0.00 | false |
| `mouse_click_keyboard_type_enter` | 0 | true | true | 0.00 | false |
| `keyboard_type_enter_no_focus` | 0 | false | true | 0.00 | false |

## Oracle Check

- Target extension: `.gpg`
- Target file: `vim.gpg`
- Reward: `1.00`
- Terminated: `true`
- Action errors: `none`
- Listed terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ ls | file.html sys32.py vim.gpg | user$`
- Final terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ ls | file.html sys32.py vim.gpg | user$ rm vim.gpg | user$`

Actions:

- `focus("25")`
- `keyboard_type("ls")`
- `keyboard_press("Enter")`
- `focus("25")`
- `keyboard_type("rm vim.gpg")`
- `keyboard_press("Enter")`


## Details

### fill_press

Actions:

- `fill("25", "ls *.gpg")`
- `press("25", "Enter")`

- Action errors: `none`
- Initial terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ █`
- Final terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ | user$ █`
- Final input value: ``
- Final active input: ``

### focus_keyboard_type_enter

Actions:

- `focus("25")`
- `keyboard_type("ls *.gpg")`
- `keyboard_press("Enter")`

- Action errors: `none`
- Initial terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ █`
- Final terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ ls *.gpg | error: ls arguments not understood. | user$ █`
- Final input value: ``
- Final active input: ``

### click_input_keyboard_type_enter

Actions:

- `click("25")`
- `keyboard_type("ls *.gpg")`
- `keyboard_press("Enter")`

- Action errors: `none`
- Initial terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ █`
- Final terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ ls *.gpg | error: ls arguments not understood. | user$`
- Final input value: ``
- Final active input: ``

### click_terminal_keyboard_type_enter

Actions:

- `click("14")`
- `keyboard_type("ls *.gpg")`
- `keyboard_press("Enter")`

- Action errors: `none`
- Initial terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ █`
- Final terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ ls *.gpg | error: ls arguments not understood. | user$`
- Final input value: ``
- Final active input: ``

### mouse_click_keyboard_type_enter

Actions:

- `mouse_click(75, 180)`
- `keyboard_type("ls *.gpg")`
- `keyboard_press("Enter")`

- Action errors: `none`
- Initial terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ █`
- Final terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ ls *.gpg | error: ls arguments not understood. | user$ █`
- Final input value: ``
- Final active input: ``

### keyboard_type_enter_no_focus

Actions:

- `keyboard_type("ls *.gpg")`
- `keyboard_press("Enter")`

- Action errors: `none`
- Initial terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ █`
- Final terminal lines: `Welcome! Type help for a list of available commands. | Last login: Sat Apr 25 2026 | user$ | user$`
- Final input value: ``
- Final active input: ``
