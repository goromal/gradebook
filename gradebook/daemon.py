import click
import logging
import time
import os
import sqlite3
import grpc
from concurrent import futures

from aapis.gradebook.v1 import gradebook_pb2_grpc, gradebook_pb2

from gradebook.click_types import LogLevel

DEFAULT_INSECURE_PORT = 40080

def _get_req_status_string(status):
    if status == gradebook_pb2.RequirementStatus.REQUIREMENT_STATUS_UNSPECIFIED:
        return "UNSPECIFIED"
    elif status == gradebook_pb2.RequirementStatus.REQUIREMENT_STATUS_INVALID:
        return "INVALID"
    elif status == gradebook_pb2.RequirementStatus.REQUIREMENT_STATUS_ACTIVE:
        return "ACTIVE"
    elif status == gradebook_pb2.RequirementStatus.REQUIREMENT_STATUS_OBSOLETE:
        return "OBSOLETE"
    else:
        return "UNDEFINED"


class Gradebook(gradebook_pb2_grpc.GradebookServiceServicer):
    def __init__(self, database_file):
        self.db_path = database_file
        if not os.path.exists(self.db_path):
            self._create_database()
    
    def _create_database(self):
        conn = sqlite3.connect(self.db_path)
        conn.close()

    def CreateRequirement(self, request, context):
        table_name = "Requirements"

        # Open a connection to the SQLite database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create the table if it doesn't exist
        columns = "req_uuid TEXT, tag TEXT, parent_tag TEXT, status TEXT, text TEXT"
        create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns});"
        cursor.execute(create_table_query)

        # Insert the entry into the table
        columns = "req_uuid, tag, parent_tag, status, text"
        placeholders = "?, ?, ?, ?, ?"
        insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});"
        
        try:
            cursor.execute(insert_query, [
                request.req_uuid,
                request.tag,
                request.parent_tag,
                _get_req_status_string(request.status),
                request.text,
            ])
            conn.commit()
            response = gradebook_pb2.CreateRequirementResponse(
                message=f"Entry added to {table_name}.",
                success=True
            )
        except sqlite3.Error as e:
            response = gradebook_pb2.CreateRequirementResponse(
                message=str(e),
                success=False
            )
        finally:
            cursor.close()
            conn.close()

        return response
    
    def SubmitTestResult(self, request, context):
        table_name = "Results"

        # Open a connection to the SQLite database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create the table if it doesn't exist
        columns = "req_uuid TEXT, test_date INTEGER, test_unit TEXT, software_hash TEXT, passed BOOLEAN"
        create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns});"
        cursor.execute(create_table_query)

        # Insert the entry into the table
        columns = "req_uuid, test_date, test_unit, software_hash, passed"
        placeholders = "?, ?, ?, ?, ?"
        insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});"

        try:
            cursor.execute(insert_query, [
                request.req_uuid,
                request.test_data.ToSeconds(),
                request.test_unit,
                request.software_hash,
                request.passed,
            ])
            conn.commit()
            response = gradebook_pb2.SubmitTestResultResponse(
                message=f"Entry added to {table_name}.",
                success=True
            )
        except sqlite3.Error as e:
            response = gradebook_pb2.SubmitTestResultResponse(
                message=str(e),
                success=False
            )
        finally:
            cursor.close()
            conn.close()
        
        return response

def serve(port, database_file):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    gradebook_pb2_grpc.add_GradebookServiceServicer_to_server(Gradebook(database_file), server)
    server.add_insecure_port(f"[::]:{port}")
    print(f"Starting gradebook server on port {port}")
    server.start()
    server.wait_for_termination()

@click.command()
@click.option(
    "-p",
    "--port",
    type=int,
    default=DEFAULT_INSECURE_PORT,
)
@click.option(
    "--database-file",
    type=click.Path(),
    default="~/"
)
@click.option(
    "-l",
    "--log-level",
    type=LogLevel(),
    default=logging.INFO,
)
def cli(port, database_file, log_level):
    """Spawn the Gradebook daemon."""
    logging.basicConfig(level=log_level)
    logging.info(f"Log level set to {log_level}")
    serve(port, database_file)

if __name__ == '__main__':
    cli()
