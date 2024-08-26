import click
from colorama import Fore, Style
import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from aapis.gradebook.v1 import gradebook_pb2_grpc, gradebook_pb2


DEFAULT_INSECURE_PORT = 40080


@click.group()
@click.pass_context
@click.option(
    "--address",
    type=str,
    default="localhost",
    show_default=True,
    help="Address of the gradebookd server.",
)
@click.option(
    "--port",
    type=int,
    default=DEFAULT_INSECURE_PORT,
)
def cli(ctx: click.Context, address, port):
    """Manage your database of software requirements."""
    ctx.obj = {"address": address, "insecure_port": port}


@cli.group()
@click.pass_context
def add(ctx: click.Context):
    """Add to the database."""


@add.command()
@click.pass_context
@click.argument("id")
@click.argument("tag")
@click.argument("text")
@click.option(
    "-p",
    "--parent",
    type=str,
    default="",
    help="Optional specification of a parent tag for nested requirements.",
)
def requirement(ctx: click.Context, id, tag, text, parent):
    with grpc.insecure_channel(
        f"{ctx.obj['address']}:{ctx.obj['insecure_port']}"
    ) as channel:
        stub = gradebook_pb2_grpc.GradebookServiceStub(channel)
        print(Fore.YELLOW + "Adding requirement:" + Style.RESET_ALL)
        print(f"  Unique ID:      {id}")
        print(f"  Searchable Tag: {parent}/{tag}")
        print(f"  Text: {text}")
        response = stub.CreateRequirement(
            gradebook_pb2.CreateRequirementRequest(
                requirement=gradebook_pb2.Requirement(
                    req_uuid=id,
                    tag=tag,
                    parent_tag=tag,
                    status=gradebook_pb2.RequirementStatus.REQUIREMENT_STATUS_ACTIVE,
                    text=text,
                )
            )
        )
        if response.success:
            print(Fore.GREEN + "SUCCESS" + Style.RESET_ALL)
        else:
            print(Fore.RED + "FAILED:" + Style.RESET_ALL + response.message)


@add.command()
@click.pass_context
@click.argument("id")
@click.argument("unit")
@click.argument("hash")
@click.argument("passed")
def result(ctx: click.Context, id, unit, hash, passed):
    test_date = Timestamp()
    test_date.GetCurrentTime()
    if passed in [1, "1", True, "True", "true", "t", "T"]:
        passed = True
    else:
        passed = False
    with grpc.insecure_channel(
        f"{ctx.obj['address']}:{ctx.obj['insecure_port']}"
    ) as channel:
        stub = gradebook_pb2_grpc.GradebookServiceStub(channel)
        print(Fore.YELLOW + "Adding test result:" + Style.RESET_ALL)
        print(f"  Unique ID:       {id}")
        print(f"  Unit Under Test: {unit}")
        print(f"  Software Hash:   {hash}")
        print(f"  Test Date:       {test_date}")
        print(f"  Passed:          {passed}")
        response = stub.SubmitTestResult(
            gradebook_pb2.SubmitTestResultRequest(
                result=gradebook_pb2.TestResult(
                    req_uuid=id,
                    test_unit=unit,
                    software_hash=hash,
                    test_date=test_date,
                    passed=passed,
                )
            )
        )
        if response.success:
            print(Fore.GREEN + "SUCCESS" + Style.RESET_ALL)
        else:
            print(Fore.RED + "FAILED:" + Style.RESET_ALL + response.message)


def main():
    cli()


if __name__ == "__main__":
    main()
