from baeloop.terminal_probe import (
    TerminalOracleResult,
    TerminalProbeReport,
    TerminalProbeResult,
    TerminalState,
    render_terminal_probe_markdown,
)


def test_terminal_probe_report_identifies_working_sequences() -> None:
    report = TerminalProbeReport(
        task_name="browsergym/miniwob.terminal",
        seed=27,
        base_url="file:///tmp/miniwob/",
        results=[
            TerminalProbeResult(
                name="no_change",
                actions=["fill(\"25\", \"ls *.gpg\")"],
                action_errors=[""],
                initial_state=TerminalState(lines=["user$"]),
                final_state=TerminalState(lines=["user$"]),
                command_visible=False,
                terminal_changed=False,
                reward=0.0,
                terminated=False,
            ),
            TerminalProbeResult(
                name="working",
                actions=["keyboard_type(\"ls *.gpg\")"],
                action_errors=[""],
                initial_state=TerminalState(lines=["user$"]),
                final_state=TerminalState(lines=["user$ ls *.gpg"]),
                command_visible=True,
                terminal_changed=True,
                reward=0.0,
                terminated=False,
            ),
            TerminalProbeResult(
                name="errored",
                actions=["bad()"],
                action_errors=["NameError"],
                initial_state=TerminalState(lines=["user$"]),
                final_state=TerminalState(lines=["user$ ls *.gpg"]),
                command_visible=True,
                terminal_changed=True,
                reward=0.0,
                terminated=False,
            ),
        ],
    )

    assert [result.name for result in report.working_results] == ["working"]


def test_render_terminal_probe_markdown_summarizes_results() -> None:
    report = TerminalProbeReport(
        task_name="browsergym/miniwob.terminal",
        seed=27,
        base_url="file:///tmp/miniwob/",
        results=[
            TerminalProbeResult(
                name="working",
                actions=["keyboard_type(\"ls *.gpg\")"],
                action_errors=[""],
                initial_state=TerminalState(lines=["user$"]),
                final_state=TerminalState(
                    lines=["user$ ls *.gpg", "documents.gpg"],
                    input_value="",
                    active_input="",
                ),
                command_visible=True,
                terminal_changed=True,
                reward=0.0,
                terminated=False,
            )
        ],
        oracle_result=TerminalOracleResult(
            target_extension=".gpg",
            target_file="secret.gpg",
            actions=["keyboard_type(\"ls\")", "keyboard_type(\"rm secret.gpg\")"],
            action_errors=["", ""],
            listed_state=TerminalState(lines=["secret.gpg notes.txt"]),
            final_state=TerminalState(lines=["secret.gpg notes.txt", ""]),
            reward=1.0,
            terminated=True,
        ),
    )

    markdown = render_terminal_probe_markdown(report)

    assert "| `working` | 0 | true | true | 0.00 | false |" in markdown
    assert "## Oracle Check" in markdown
    assert "- Target file: `secret.gpg`" in markdown
    assert "- `keyboard_type(\"ls *.gpg\")`" in markdown
    assert "documents.gpg" in markdown
