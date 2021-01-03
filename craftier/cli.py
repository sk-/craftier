import collections
import multiprocessing
import pathlib
import platform
import statistics
import sys
from typing import Any, DefaultDict, List, Mapping, Optional, Sequence

import click
import click_pathlib
from loguru import logger

from craftier import config, performance, refactor

# Generated using
# http://patorjk.com/software/taag/#p=display&f=Graceful&t=craftier
# The \b signals that paragraph won't be rewrapped.
_BANNER = (
    "\b"
    + r"""
  ___  ____   __   ____  ____  __  ____  ____ (pre-α)
 / __)(  _ \ / _\ (  __)(_  _)(  )(  __)(  _ \
( (__  )   //    \ ) _)   )(   )(  ) _)  )   /
 \___)(__\_)\_/\_/(__)   (__) (__)(____)(__\_)

      Your personal Python code reviewer
    """
)

_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.group(context_settings=_CONTEXT_SETTINGS, help=_BANNER)
@click.version_option(version="0.1.0", prog_name="craftier")
def app() -> None:
    """Entry point for craftier CLI."""


@click.command(
    context_settings=_CONTEXT_SETTINGS,
    name="refactor",
    help="Refactor your code",
)
@click.argument(
    "files",
    nargs=-1,
    type=click_pathlib.Path(
        exists=True,
        writable=True,
        readable=True,
        dir_okay=False,
        allow_dash=True,
    ),
)
@click.option(
    "--config",
    "config_path",
    type=click_pathlib.Path(exists=True, readable=True, dir_okay=False),
    help="Path to the config file. Searches for .craftier.ini by default.",
)
@click.option(
    "--debug/--no-debug",
    default=False,
    is_flag=True,
    help="Show extra debugging information.",
)
def _refactor(
    files: Sequence[pathlib.Path],
    config_path: Optional[pathlib.Path],
    debug: bool,
) -> None:
    """Subcommand to refactor code."""
    # In Python 3.8 for Mac OS the default was changed from fork to spawn,
    # however that brings lot of undesired effects. For example the Pickling
    # of many structures, which is fragile and the errors are undecipherable.
    # Aditionally it means, that logging and global state won't be preserved.
    # Spawning is also slower.
    # Note that it should be safe to use fork as we don't have any
    # multi-threaded code.
    if (
        platform.system() == "Darwin"
        and multiprocessing.get_start_method(allow_none=True) != "fork"
    ):
        multiprocessing.set_start_method("fork")
    level = "DEBUG" if debug else "WARNING"
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="{level}\t{elapsed}\t{message}",
        enqueue=True,
    )
    logger.enable("craftier")

    if debug:
        performance.enable()

    if not files:
        click.secho("No path provided. Nothing to do 💤", bold=True)
        return
    try:
        craftier_config = config.load(config_path)
        logger.debug("Config path: {}", craftier_config.path)
        result = refactor.run(craftier_config, files)
        _fix_summary(result)
    except (config.InvalidConfigError, refactor.Error) as e:
        print(e)
        raise click.exceptions.Exit(1)
    except KeyboardInterrupt:
        raise click.Abort("Aborted by user") from None

    if debug:
        performance.disable()


def _fix_summary(result: refactor.Result) -> None:
    _print_performance_stats()

    for file in result.refactored:
        click.secho(f"refactored {file.relative_to('.')}", bold=True)

    if result.success:
        click.secho("All done! 🎉 🏆 🎉", bold=True)
    else:
        click.secho("Oh no! 🧨 💣 🧨", bold=True)
    refactored = len(result.refactored)
    unchanged = len(result.unchanged)
    errors = result.error_count
    report = []
    if refactored > 0:
        report.append(
            click.style(
                f"{refactored} {_pluralize('file', refactored)} refactored",
                bold=True,
            )
        )
    if unchanged > 0:
        report.append(
            f"{unchanged} {_pluralize('file', unchanged)} left unchanged"
        )
    if errors > 0:
        report.append(
            click.style(
                f"{errors} {_pluralize('file', errors)} failed", fg="red"
            )
        )
    click.echo(f"{', '.join(report)}.")
    if not result.success:
        raise click.exceptions.Exit(1)


def _pluralize(word: str, count: int) -> str:
    ending = "s" if count != 1 else ""
    return f"{word}{ending}"


def _print_performance_stats() -> None:
    data = performance.read()
    grouped_data: DefaultDict[
        str, List[Mapping[str, Any]]
    ] = collections.defaultdict(list)
    for row in data:
        grouped_data[row["name"]].append(row)
    for name in sorted(grouped_data.keys()):
        _print_single_performance_stats(name, grouped_data[name])
    _print_single_performance_stats("Overall", data)


def _print_single_performance_stats(
    name: str, data: Sequence[Mapping[str, Any]]
) -> None:
    modified = [row["time"] for row in data if row["status"] == "modified"]
    unchanged = [row["time"] for row in data if row["status"] == "unchanged"]
    values = [row["time"] for row in data]
    logger.debug(
        "{}\tcount={}\ttotal={:.1f}ms\t{}\t{}\t{}",
        name,
        len(values),
        sum(values),
        _stats(values),
        _stats(modified),
        _stats(unchanged),
    )


def _stats(data: List[float]) -> str:
    if not data:
        return "-/-/-"
    mean = statistics.mean(data)
    maximum = max(data)
    try:
        stddev = statistics.stdev(data, xbar=mean)
    except statistics.StatisticsError:
        stddev = 0
    return f"μ={mean:.1f}ms/σ={stddev:.2f}ms/max={maximum:.1f}ms"


app.add_command(_refactor)
